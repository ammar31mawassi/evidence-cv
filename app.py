import hashlib
import json
import logging
import os
import re
import shutil
import threading
import uuid
import ntpath
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from engine import MODEL, SOURCES, analyze, compile_cv, load_catalog, safe_name, select
from extract import CVError, fetch_job, looks_like_job, normalize

STATE = Path(os.getenv('STATE_DIR', str(Path(__file__).parent / 'state')))
OUTPUT = Path(os.getenv('OUTPUT_DIR', str(Path(__file__).parent / 'output')))
_host_output = os.getenv('WINDOWS_OUTPUT_DIR', str(OUTPUT.resolve()))
WINDOWS_OUTPUT = ntpath.normpath(_host_output) if re.match(r'^[A-Za-z]:', _host_output) else str(Path(_host_output).resolve())
POOL = ThreadPoolExecutor(max_workers=1)
LOCK = threading.RLock()
LOG = logging.getLogger('job-cv')

class Request(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    description: str | None = Field(default=None, min_length=350, max_length=60000)

def job_path(jid):
    if not re.fullmatch(r'[a-f0-9]{32}', jid):
        raise HTTPException(404, 'Unknown job ID.')
    return STATE / jid

def read(jid):
    path = job_path(jid) / 'status.json'
    if not path.exists():
        raise HTTPException(404, 'Unknown job ID.')
    with LOCK:
        return json.loads(path.read_text(encoding='utf-8'))

def write(jid, **changes):
    with LOCK:
        path = job_path(jid) / 'status.json'
        value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'id': jid}
        value.update(changes)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(path)
    return value

def run(jid):
    work = job_path(jid)
    try:
        write(jid, status='running', stage='reading posting')
        request = json.loads((work / 'request.json').read_text(encoding='utf-8'))
        catalog = load_catalog()
        if request.get('description'):
            text = normalize(request['description'])
            if not looks_like_job(text):
                raise CVError('The supplied text does not contain a complete job description.')
            job = {'text': text, 'title': '', 'company': '', 'url': request['url'], 'method': 'supplied description'}
        else:
            job = fetch_job(request['url'])
        (work / 'posting.json').write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding='utf-8')
        write(jid, stage='analyzing requirements with local Ollama')
        analysis = analyze(job)
        (work / 'analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
        write(jid, stage='selecting verified projects and skills')
        choice = select(catalog, analysis)
        (work / 'selection.json').write_text(json.dumps(choice, ensure_ascii=False, indent=2), encoding='utf-8')
        write(jid, stage='compiling and validating one-page PDF')
        pdf, checks, reduction, bids = compile_cv(choice, catalog, work)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stem = safe_name(analysis['company'], analysis['title'])
        # Exclusive creation preserves earlier runs; no dates in any filename.
        counter = 1
        while True:
            target = OUTPUT / (stem + (f'_{counter}' if counter > 1 else '') + '.pdf')
            try:
                with target.open('xb') as dest, pdf.open('rb') as source:
                    shutil.copyfileobj(source, dest)
                break
            except FileExistsError:
                counter += 1
        public_path = WINDOWS_OUTPUT + ('\\' if '\\' in WINDOWS_OUTPUT else '/') + target.name
        audit = {'job_url': request['url'], 'extraction_method': job['method'], 'analysis': analysis,
                 'selection': choice, 'rendered_bullet_ids': bids, 'reduction_level': reduction,
                 'model': MODEL, 'checks': checks, 'career_source_sha256': hashlib.sha256((SOURCES / 'profile.json').read_bytes()).hexdigest(),
                 'inventory_sha256': hashlib.sha256((SOURCES / 'projects.json').read_bytes()).hexdigest(), 'pdf_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                 'note': 'CV uses fixed reviewed claims. Internal notes are model-generated and are not hiring predictions.'}
        (work / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
        # PDF is delivered only after checks; editable generated source remains beside it.
        shutil.copyfile(work / 'resume.tex', target.with_suffix('.tex'))
        shutil.copyfile(work / 'audit.json', target.with_suffix('.audit.json'))
        write(jid, status='completed', stage='finished', path=public_path, filename=target.name, checks=checks,
              model=MODEL, audit_path=public_path.removesuffix('.pdf') + '.audit.json')
    except Exception as exc:
        LOG.exception('Job %s failed', jid)
        message = str(exc) if isinstance(exc, CVError) else f'Generation failed ({type(exc).__name__}); inspect local worker logs.'
        write(jid, status='failed', stage='failed', error=message)

@asynccontextmanager
async def lifespan(app):
    STATE.mkdir(parents=True, exist_ok=True)
    for path in STATE.glob('*/status.json'):
        value = json.loads(path.read_text(encoding='utf-8'))
        if value['status'] == 'running':
            write(value['id'], status='failed', error='Generation was interrupted by a service restart. Resubmit the job URL.')
        elif value['status'] == 'queued':
            POOL.submit(run, value['id'])
    yield

app = FastAPI(title='Local Job CV', lifespan=lifespan)

@app.get('/health')
def health():
    return {'status': 'ok', 'model': MODEL, 'cloud_models': False}

@app.post('/jobs', status_code=202)
def create(request: Request):
    parsed = urlparse(request.url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422, 'Provide an http/https job URL without credentials.')
    jid = uuid.uuid4().hex
    directory = job_path(jid)
    directory.mkdir(parents=True)
    (directory / 'request.json').write_text(json.dumps(request.model_dump(), ensure_ascii=False), encoding='utf-8')
    value = write(jid, status='queued', stage='waiting for local worker')
    POOL.submit(run, jid)
    return value

@app.get('/jobs/{jid}')
def status(jid: str):
    return read(jid)
