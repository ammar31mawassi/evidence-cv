import copy
import json
import shutil
import os
from pathlib import Path
import pytest
import engine
from extract import CVError, from_html, public_url
from onboarding import seal, validate_private
from template import make_template

@pytest.fixture
def records(tmp_path,monkeypatch):
    examples=Path(__file__).parents[1]/'examples'
    for name in ['profile','projects']:
        shutil.copyfile(examples/(name+'.example.json'),tmp_path/(name+'.json'))
    cat=json.loads((tmp_path/'projects.json').read_text())
    for p in cat['projects']: p['approved']=True
    (tmp_path/'projects.json').write_text(json.dumps(cat))
    seal(tmp_path); monkeypatch.setattr(engine,'SOURCES',tmp_path)
    return tmp_path

def choice(cat):
    return {'projects':[{'id':p['id'],'bullet_ids':[b['id'] for b in p['bullets'][:2]]} for p in cat['projects']],
            'skills':engine.master_skills()}

def test_new_identity_without_code_changes(records):
    p,c=validate_private(records,True)
    p['name']='Taylor Fictional'; (records/'profile.json').write_text(json.dumps(p)); seal(records)
    source,bids=engine.render(choice(c),c)
    assert 'Taylor Fictional' in source and 'Alex Example' not in source
    assert len(bids)==6

def test_changed_fact_requires_review(records):
    p=json.loads((records/'profile.json').read_text()); p['name']='Unreviewed Edit'
    (records/'profile.json').write_text(json.dumps(p))
    with pytest.raises(CVError,match='changed'): engine.load_catalog()

def test_unapproved_project_is_blocked(records):
    c=json.loads((records/'projects.json').read_text()); c['projects'][0]['approved']=False
    (records/'projects.json').write_text(json.dumps(c))
    with pytest.raises(CVError,match='approved'): seal(records)

def test_source_references_required(records):
    c=json.loads((records/'projects.json').read_text()); c['projects'][0]['bullets'][0]['sources']=[]
    (records/'projects.json').write_text(json.dumps(c))
    with pytest.raises(CVError,match='source references'): validate_private(records)

def test_private_link_is_not_public_evidence(records):
    c=json.loads((records/'projects.json').read_text()); c['projects'][0]['url']='https://example.com/private'
    (records/'projects.json').write_text(json.dumps(c))
    with pytest.raises(CVError,match='public HTTPS'): validate_private(records)

def test_ratings_drive_role_selection_without_presentation_penalty(records):
    c=engine.load_catalog(); ranked=engine.shortlist(c,{'title':'Java developer','requirements':['Java'],'role_family':'java'})
    assert ranked[0]['id']=='sample-java'

def test_all_skills_survive_reduction_in_labeled_groups(records):
    c=engine.load_catalog(); selected=choice(c)
    for level in range(4):
        source,_=engine.render(selected,c,level)
        section=source.split(r'\cvsection{Technical Skills}')[1].split(r'\cvsection{Projects}')[0]
        assert r'\textbf{Languages:}' in section
        for skill in engine.master_skills(): assert engine.tex_escape(skill) in section

def test_unknown_skill_rejected(records):
    with pytest.raises(CVError):engine.complete_skill_order(['InventedFramework'],{'title':'Java','requirements':['Java']})

@pytest.mark.parametrize('url',['http://localhost','http://127.0.0.1','http://169.254.169.254','file:///etc/passwd'])
def test_local_fetch_blocked(url):
    with pytest.raises(CVError):public_url(url)

def test_multiple_job_page_rejected():
    jobs=[{'@type':'JobPosting','title':t,'description':'Responsibilities and requirements '*20} for t in ['One','Two']]
    with pytest.raises(CVError):from_html('<script type="application/ld+json">'+json.dumps(jobs)+'</script>','https://example.com')

def test_escape_prevents_tex_commands():
    assert r'\input{secret}' not in engine.tex_escape(r'\input{secret}')

@pytest.mark.skipif(not (shutil.which('pdflatex') or shutil.which('tectonic') or os.getenv('TECTONIC_PATH')),reason='Local TeX required; worker image provides it')
def test_real_pdf_with_fictional_profile(records,tmp_path):
    c=engine.load_catalog(); work=tmp_path/'compile'; work.mkdir()
    pdf,checks,*_=engine.compile_cv(choice(c),c,work)
    assert pdf.exists() and checks['pages']==1

@pytest.mark.skipif(not (shutil.which('pdflatex') or shutil.which('tectonic') or os.getenv('TECTONIC_PATH')),reason='Local TeX required')
def test_worker_writes_validated_pdf_and_host_path(records,tmp_path,monkeypatch):
    import app
    state=tmp_path/'jobs'; state.mkdir(); output=tmp_path/'delivered'
    monkeypatch.setattr(app,'STATE',state); monkeypatch.setattr(app,'OUTPUT',output)
    monkeypatch.setattr(app,'WINDOWS_OUTPUT',str(output))
    monkeypatch.setattr(app,'SOURCES',records)
    cat=engine.load_catalog()
    monkeypatch.setattr(app,'analyze',lambda job:{'title':'Java Engineer','company':'Example Co','requirements':['Java','JUnit'],'role_family':'java'})
    monkeypatch.setattr(app,'select',lambda catalog,analysis:choice(catalog))
    jid='a'*32; work=state/jid; work.mkdir()
    request={'url':'https://example.com/job','description':'Example Co Java Engineer. Requirements: Java and JUnit. Responsibilities: build and test event services. '*6}
    (work/'request.json').write_text(json.dumps(request)); app.write(jid,status='queued')
    app.run(jid); result=app.read(jid)
    assert result['status']=='completed',result
    assert Path(result['path']).is_file()
    audit=json.loads((output/'Example-Co_Java-Engineer.audit.json').read_text())
    assert audit['checks']['pages']==1 and audit['checks']['links_checked']
