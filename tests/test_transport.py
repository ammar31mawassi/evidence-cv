import json
from unittest.mock import Mock
import pytest
import engine
from extract import CVError

def test_local_ollama_request_is_schema_constrained(monkeypatch):
    response=Mock(); response.json.return_value={'message':{'content':json.dumps({'value':'approved'})}}
    post=Mock(return_value=response); monkeypatch.setattr(engine.requests,'post',post)
    assert engine.ollama_json('data only',{},engine.object_schema({'value':{'type':'string'}}))=={'value':'approved'}
    request=post.call_args.kwargs['json']
    assert request['stream'] is False and request['think'] is False
    assert request['format']['additionalProperties'] is False
    assert 'Authorization' not in post.call_args.kwargs.get('headers',{})

def test_invalid_json_never_becomes_a_cv(monkeypatch):
    response=Mock(); response.json.return_value={'message':{'content':'unstructured fabricated content'}}
    monkeypatch.setattr(engine.requests,'post',Mock(return_value=response))
    with pytest.raises(CVError,match='generation failed'): engine.ollama_json('data only',{},engine.object_schema({'value':{'type':'string'}}))

def test_long_verbatim_qualification_is_preserved(monkeypatch):
    requirement='Experience with '+', '.join(['algorithms','data structures','coursework','research','coding projects','practical implementation']*3)+'.'
    assert 160 < len(requirement) <= 350
    value={'title':'Software Engineering Intern','company':'Example Co','role_family':'general',
           'requirements':[requirement,'Python programming'],'is_single_job':True}
    response=Mock(); response.json.return_value={'message':{'content':json.dumps(value)}}
    monkeypatch.setattr(engine.requests,'post',Mock(return_value=response))
    result=engine.analyze({'text':'Example Co Software Engineering Intern. '+requirement+' Python programming'})
    assert result['requirements'][0]==requirement
