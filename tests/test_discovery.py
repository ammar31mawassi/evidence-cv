import json,shutil
from pathlib import Path
import pytest
import discovery
import engine
from evaluate import fixtures,fixture_config
from onboarding import seal
from retrieval import requirement_bank,bm25
from digest_mail import DeliveryUncertain

def test_labeled_eligibility_cases():
    assert all(case['passed'] for case in fixtures())

def test_id_excerpts_are_source_substrings():
    text="Requirements: Python API development. SQL knowledge and debugging experience. Company picnic."
    records=requirement_bank(text)
    assert len(records)>=2 and all(r['text'] in text for r in records)
    assert len({r['id'] for r in records})==len(records)

def test_bm25_distinguishes_java_and_python():
    scores=bm25('Python API SQL',['Java message bus and queues','Python API and SQL services'])
    assert scores[1]>scores[0]

def test_unknown_employer_not_quarantined():
    status,_=discovery.employer_policy({'company':'Unlisted Fictional Co','title':'Engineer','description':'Veterans welcome'},fixture_config())
    assert status=='allowed'

@pytest.fixture
def configured(tmp_path,monkeypatch):
    examples=Path(__file__).parents[1]/'examples'
    for name in ['profile','projects']:shutil.copyfile(examples/(name+'.example.json'),tmp_path/(name+'.json'))
    c=json.loads((tmp_path/'projects.json').read_text())
    for p in c['projects']:p['approved']=True
    (tmp_path/'projects.json').write_text(json.dumps(c));seal(tmp_path)
    monkeypatch.setattr(engine,'SOURCES',tmp_path)
    monkeypatch.setattr(discovery,'STATE',tmp_path/'state')
    cfg=dict(fixture_config(),enabled=True,sources=[{'kind':'freehire'}],hour=13,top_n=10,max_model_jobs=5,min_score=40,
             mail={'mode':'gmail','sender':'sender@example.com','recipient':'recipient@example.com'})
    monkeypatch.setattr(discovery,'config',lambda:cfg)
    job={'source':'fixture','external_id':'1','canonical_key':'one','content_hash':'hash-one','title':'Junior Python Developer',
         'company':'Fictional Co','url':'https://example.com/job','description':'Requirements: Python APIs and SQL knowledge.',
         'text':'Junior Python Developer. Requirements: Python APIs and SQL knowledge.','location':'Tel Aviv, Israel','countries':['il']}
    monkeypatch.setattr(discovery,'fetch_source',lambda source:[dict(job)])
    monkeypatch.setattr(discovery,'fetch_job',lambda url:{'title':job['title'],'text':job['text']})
    monkeypatch.setattr(discovery,'rank',lambda *args:dict(score=80,matches=[{'requirement':'Python APIs','evidence':'Built Python APIs.',
       'evidence_id':'sample-python.1'}],gaps=[],employer_note='Local blacklist applied'))
    return cfg,job

def test_digest_delivery_deduplicates_jobs(configured,monkeypatch):
    sent=[]
    monkeypatch.setattr(discovery,'send',lambda subject,body,cfg:sent.append(body) or 'gmail-message-1')
    first=discovery.scan(force=True)
    second=discovery.scan(force=True)
    assert first['email']['status']=='sent' and len(sent)==1
    assert second['email']['status']=='no_new_matches'
    assert 'job-cv "https://example.com/job"' in sent[0]

def test_uncertain_delivery_never_auto_resends(configured,monkeypatch):
    attempts=[]
    def uncertain(*args):attempts.append(1);raise DeliveryUncertain('network outcome unknown')
    monkeypatch.setattr(discovery,'send',uncertain)
    with pytest.raises(DeliveryUncertain):discovery.scan(force=True)
    discovery.scan(force=True)
    assert len(attempts)==1
    with discovery.connect() as db:assert db.execute("SELECT status FROM digests").fetchone()['status']=='uncertain'


def test_preview_does_not_consume_daily_email(configured,monkeypatch):
    cfg,_=configured;cfg['hour']=0
    sent=[]
    monkeypatch.setattr(discovery,'send',lambda *args:sent.append(1) or 'message-1')
    preview=discovery.scan(force=True,send_email=False)
    actual=discovery.scan(force=False,send_email=True)
    assert preview['email']['status']=='disabled'
    assert actual['email']['status']=='sent' and len(sent)==1
    assert discovery.scan(force=False)['status']=='not_due'


def test_gmail_refresh_and_confirmed_send(tmp_path,monkeypatch):
    import digest_mail
    import base64
    token=tmp_path/'token.json'
    token.write_text(json.dumps({'client_id':'fictional','client_secret':'fictional','refresh_token':'fictional'}))
    calls=[]
    class Response:
        ok=True;status_code=200
        def __init__(self,data):self.data=data
        def json(self):return self.data
    def post(url,**kwargs):
        calls.append((url,kwargs))
        return Response({'access_token':'fixture-access'} if len(calls)==1 else {'id':'gmail-1'})
    monkeypatch.setattr(digest_mail.requests,'post',post)
    assert digest_mail.send('Matches','Actual strengths and gaps',
        {'mode':'gmail','sender':'sender@example.com','recipient':'recipient@example.com'},token)=='gmail-1'
    assert calls[0][1]['data']['grant_type']=='refresh_token'
    raw=base64.urlsafe_b64decode(calls[1][1]['json']['raw']).decode()
    assert 'To: recipient@example.com' in raw and 'Actual strengths and gaps' in raw

def test_fresh_closed_or_changed_job_not_emailed(configured,monkeypatch):
    sent=[];monkeypatch.setattr(discovery,'send',lambda *args:sent.append(1))
    monkeypatch.setattr(discovery,'fetch_job',lambda url:{'title':'Senior Engineer','text':'Changed listing'})
    report=discovery.scan(force=True)
    assert not report['jobs'] and not sent


@pytest.mark.parametrize('disconnect',[False,True])
def test_smtp_delivery_confirmation_and_uncertain_disconnect(tmp_path,monkeypatch,disconnect):
    import digest_mail
    import smtplib
    path=tmp_path/'smtp.json';path.write_text(json.dumps({'username':'sender@example.com','password':'fixture only'}))
    monkeypatch.setenv('GMAIL_SMTP_FILE',str(path))
    calls=[]
    class Server:
        def __init__(self,host,port,**kwargs):
            assert host=='smtp.gmail.com' and port==465 and kwargs['context'].check_hostname
        def login(self,user,password):calls.append(user)
        def send_message(self,message):
            assert message['To']=='recipient@example.com'
            if disconnect:raise smtplib.SMTPServerDisconnected('fixture disconnect')
            return {}
        def close(self):pass
    monkeypatch.setattr(digest_mail.smtplib,'SMTP_SSL',Server)
    args=('Job matches','Evidence and gaps',{'mode':'smtp','sender':'sender@example.com','recipient':'recipient@example.com'})
    if disconnect:
        with pytest.raises(DeliveryUncertain):digest_mail.send(*args)
    else:assert digest_mail.send(*args).endswith('@evidence-cv.local>')
    assert calls==['sender@example.com']

def test_fresh_employer_is_also_blacklisted(configured,monkeypatch):
    sent=[];monkeypatch.setattr(discovery,'send',lambda *args:sent.append(1))
    monkeypatch.setattr(discovery,'fetch_job',lambda url:{'title':'Junior Python Developer','company':'ExcludedExample','text':'Python APIs and SQL knowledge.'})
    report=discovery.scan(force=True)
    assert not report['jobs'] and not sent

def test_private_digest_endpoint_requires_secret(monkeypatch):
    import app
    from fastapi import HTTPException
    monkeypatch.setenv('DISCOVERY_TOKEN','fixture-secret')
    with pytest.raises(HTTPException):app.discovery_auth(None)
    with pytest.raises(HTTPException):app.discovery_auth('wrong')
    app.discovery_auth('fixture-secret')


def test_preferred_years_do_not_become_mandatory():
    job={'title':'Junior Software Engineer','description':'Python required. 5 years of experience preferred.',
         'company':'Fictional Co','location':'Israel','countries':['il']}
    assert discovery.eligibility(job,fixture_config())['eligible']
    job['description']='Python required. 5 years of previous experience required.'
    assert not discovery.eligibility(job,fixture_config())['eligible']

def test_requirement_ids_restore_exact_source(monkeypatch):
    job={'text':'Example Python Engineer. Requirements: Python API experience. SQL database knowledge is required.',
         'title':'Python Engineer','company':'Example','single_posting':True}
    def choose(system,payload,schema):
        ids=[r['id'] for r in payload['source_requirements']]
        return {'title':'Python Engineer','company':'Example','role_family':'python','requirement_ids':ids[:2],'is_single_job':True}
    monkeypatch.setattr(engine,'ollama_json',choose)
    result=engine.analyze(job)
    assert all(r in job['text'] for r in result['requirements'])
