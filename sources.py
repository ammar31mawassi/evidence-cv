"""Read-only public ATS/catalog adapters with bounded requests and normalized output."""
import hashlib
import json
import logging
import re
from urllib.parse import urlparse, urljoin, urlencode, parse_qsl, urlunparse
import requests
from bs4 import BeautifulSoup
from extract import public_url, plain, canonical_job_url, CVError

def public_json(url):
    for _ in range(5):
        public_url(url)
        with requests.get(url, timeout=(8, 30), allow_redirects=False, stream=True,
                          headers={'User-Agent': 'EvidenceCV/1.0 (personal read-only job search)'}) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers['Location']); continue
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 12_000_000: raise CVError('Source response exceeds size limit')
                chunks.append(chunk)
            return json.loads(b''.join(chunks))
    raise CVError('Source redirect limit exceeded')

def clean_url(url):
    p = urlparse(canonical_job_url(url))
    query = urlencode([(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k not in {'trackingId','refId'}])
    return urlunparse((p.scheme,p.netloc,p.path, p.params,query,''))

def normalized(source, external_id, title, company, url, description, location='', countries=None, published='', remote=False):
    if not title or not url: raise CVError('Source omitted title or posting URL')
    url = clean_url(url); public_url(url)
    company=company or '';location=location or ''
    raw=str(description or '')
    raw=BeautifulSoup(raw,'html.parser').get_text('\n',strip=True) if '<' in raw else raw
    body='\n'.join(plain(line) for line in raw.splitlines() if line.strip())
    identity = re.sub(r'\W+', ' ', (company+' '+title+' '+location).casefold()).strip()
    return {'source':source,'external_id':str(external_id),'title':plain(title),'company':plain(company),'url':url,
            'text':plain(title+' '+company+' '+body),'description':body,'location':location,
            'countries':countries or [],'published':published,'remote':remote,
            'canonical_key': hashlib.sha256(identity.encode()).hexdigest(),
            'content_hash':hashlib.sha256((title+' '+company+' '+body).encode()).hexdigest()}

def fetch_source(config):
    kind, board = config['kind'], config.get('board','')
    if kind == 'greenhouse':
        if not re.fullmatch(r'[a-zA-Z0-9_-]+',board): raise CVError('Invalid board')
        data=public_json(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true')
        return [normalized(kind+':'+board,j['id'],j['title'],config['company'],j['absolute_url'],j.get('content',''),j.get('location',{}).get('name',''),published=j.get('updated_at','')) for j in data['jobs']]
    if kind == 'ashby':
        if not re.fullmatch(r'[a-zA-Z0-9_-]+',board): raise CVError('Invalid board')
        data=public_json(f'https://api.ashbyhq.com/posting-api/job-board/{board}')
        return [normalized(kind+':'+board,j.get('id',j['jobUrl']),j['title'],config['company'],j['jobUrl'],j.get('descriptionPlain') or j.get('descriptionHtml',''),j.get('location',''),published=j.get('publishedAt',''),remote=j.get('isRemote',False)) for j in data['jobs'] if j.get('isListed',True)]
    if kind == 'lever':
        if not re.fullmatch(r'[a-zA-Z0-9_-]+',board): raise CVError('Invalid board')
        data=public_json(f'https://api.lever.co/v0/postings/{board}?mode=json')
        return [normalized(kind+':'+board,j['id'],j['text'],config['company'],j['hostedUrl'],j.get('description','')+' '.join(x.get('content','') for x in j.get('lists',[])),j.get('categories',{}).get('location','')) for j in data]
    if kind == 'freehire':
        output=[]
        for query in config.get('queries',['software engineer']):
            params={'q':query,'countries':'il','limit':min(config.get('limit',50),100),'offset':0}
            data=public_json('https://freehire.me/api/v1/jobs/search?'+urlencode(params))
            for j in data.get('data',[]):
                if j.get('closed_at'):continue
                try:
                    output.append(normalized(kind,j.get('public_slug',j['url']),j['title'],j.get('company',''),j['url'],j.get('description',''),j.get('location',''),j.get('countries',[]),j.get('posted_at',''),str(j.get('work_mode','')).casefold()=='remote'))
                except (CVError,KeyError,TypeError) as exc:
                    # One dead destination must not discard every other result.
                    # URL guards still run here and again before fetching finalists.
                    logging.getLogger(__name__).warning('Skipped an invalid catalog posting (%s)',type(exc).__name__)
        return output
    raise CVError('Unsupported source: '+kind)
