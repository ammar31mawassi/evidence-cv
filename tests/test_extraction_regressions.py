import json
import pytest
import engine
from extract import canonical_job_url, from_html, CVError

def test_selected_linkedin_search_job():
    assert canonical_job_url('https://www.linkedin.com/jobs/search-results/?currentJobId=1234567890&keywords=Python') == 'https://www.linkedin.com/jobs/view/1234567890/'
    assert canonical_job_url('https://www.linkedin.com/jobs/view/python-engineer-1234567890/') == 'https://www.linkedin.com/jobs/view/1234567890/'
    assert canonical_job_url('https://linkedin.com.evil.example/jobs/search/?currentJobId=1234567890').startswith('https://linkedin.com.evil.example/')
    with pytest.raises(CVError, match='no selected'): canonical_job_url('https://www.linkedin.com/jobs/search/?keywords=Python')

def test_linkedin_detail_fragment():
    raw='<h2 class="top-card-layout__title">Python Engineer</h2><a class="topcard__org-name-link">Example Co</a><div class="show-more-less-html__markup">'+'Requirements: Python development and API experience. '*12+'</div>'
    job=from_html(raw,'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/1234567890')
    assert job['title']=='Python Engineer' and job['company']=='Example Co' and job['single_posting']

def test_google_scoped_heading():
    job=from_html('<title>Careers</title><h1>Embedded Engineer, DSP</h1><main>'+('Requirements and responsibilities: C++ development. '*15)+'</main>', 'https://www.google.com/about/careers/applications/jobs/results/123456789')
    assert job['title']=='Embedded Engineer, DSP' and job['company']=='Google'
    assert job['single_posting']
    job=from_html('<title>Embedded Engineer, DSP — Google Careers</title><h1>job details</h1><main>'+('Requirements: C++ experience. '*20)+'</main>',job['url'])
    assert job['title']=='Embedded Engineer, DSP'

def test_expired_jsonld_rejected():
    job={'@type':'JobPosting','title':'Python Engineer','description':'Requirements and Python experience. '*20,'validThrough':'2020-01-01'}
    with pytest.raises(CVError,match='validThrough'):from_html('<script type="application/ld+json">'+json.dumps(job)+'</script>','https://example.com/job')

def test_source_identity_over_model_reformatting(monkeypatch):
    result={'title':'Engineer - Embedded','company':'Wrong Co','role_family':'systems','requirements':['C++ development','Linux experience'],'is_single_job':False}
    monkeypatch.setattr(engine,'ollama_json',lambda *args:dict(result))
    job={'text':'Example Co Engineer, Embedded. Requirements: C++ development and Linux experience.', 'title':'Engineer, Embedded','company':'Example Co','single_posting':True}
    actual=engine.analyze(job)
    assert actual['title']==job['title'] and actual['company']=='Example Co'
    assert job['analysis_diagnostics']['raw_model_result']==result
    job['text']+=' No longer accepting applications.'
    with pytest.raises(CVError,match='closed'):engine.analyze(job)
    job['text']=job['text'].replace(' No longer accepting applications.','').replace('Linux experience','Windows development')
    with pytest.raises(CVError,match='unsupported requirement'):engine.analyze(job)

def test_requirement_typography_does_not_reject_evidence(monkeypatch):
    result={'title':'Engineer','company':'Example','role_family':'systems','requirements':["Bachelor's degree",'C++ experience'],'is_single_job':True}
    monkeypatch.setattr(engine,'ollama_json',lambda *args:dict(result))
    job={'text':'Example Engineer: Bachelor\u2019s degree and C++ experience.'}
    assert engine.analyze(job)['requirements']==result['requirements']
    result['requirements'][1]='Python experience'
    with pytest.raises(CVError,match='unsupported requirement'):engine.analyze(job)
