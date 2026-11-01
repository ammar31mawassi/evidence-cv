"""Reproducible fit fixtures and opt-in local model comparison; reports stay ignored."""
import argparse,json,time,os
from pathlib import Path
from discovery import eligibility

def fixture_config():
    return {'role_pattern':r'software|developer|backend|frontend|automation|devops','max_required_years':2,
            'allow_worldwide_remote':True,'blacklist':{'companies':[{'aliases':['ExcludedExample']}]}}

def fixtures():
    cases=json.loads((Path(__file__).parent/'evals/cases.json').read_text())
    results=[]
    for c in cases:
        job=dict(c,company=c.get('company','Fictional Example'),text=c['title']+' '+c['description'])
        actual=eligibility(job,fixture_config())
        passed=actual['eligible']==c['eligible'] and (not c.get('gap') or bool(actual['gaps']))
        results.append({'id':c['id'],'passed':passed,'actual':actual})
    return results

def compare(models):
    import engine
    schema=engine.object_schema({'requirement_ids':{'type':'array','uniqueItems':True,'items':{'type':'string','enum':['R1','R2','R3']}}})
    cases=[{'title':'Junior Python Developer','requirements':[{'id':'R1','text':'Python API development is required.'},{'id':'R2','text':'SQL knowledge is required.'},{'id':'R3','text':'Equal opportunity employer.'}],'expected':{'R1','R2'}},
           {'title':'Software Engineering Student','requirements':[{'id':'R1','text':'Currently enrolled in computer science.'},{'id':'R2','text':'C++ knowledge is required.'},{'id':'R3','text':'Company picnic every summer.'}],'expected':{'R1','R2'}}]
    output=[]
    for model in models:
        for case in cases:
            started=time.monotonic()
            try:
                result=engine.ollama_json('Select IDs of actual job qualifications, excluding company perks and boilerplate. Return only IDs.',
                   {k:v for k,v in case.items() if k!='expected'},schema,model=model)
                output.append({'model':model,'case':case['title'],'passed':set(result['requirement_ids'])==case['expected'],
                    'seconds':round(time.monotonic()-started,2),'output':result})
            except Exception as exc:output.append({'model':model,'case':case['title'],'passed':False,'error':str(exc),'seconds':round(time.monotonic()-started,2)})
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--models',nargs='*',default=[]);args=p.parse_args()
    data={'fixtures':fixtures(),'models':compare(args.models)}
    out=Path(os.getenv('STATE_DIR',str(Path(__file__).parent/'state')))/'evaluations.json';out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(data,indent=2))
    if not all(r['passed'] for r in data['fixtures']):raise SystemExit(1)
