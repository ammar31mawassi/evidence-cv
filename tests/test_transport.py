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
