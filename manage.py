"""Run with Python or the worker container. Personal inputs stay under private/."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from onboarding import validate_private, seal

ROOT=Path(__file__).parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--private', type=Path, default=ROOT/'private')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    sub.add_parser('validate')
    approve=sub.add_parser('seal'); approve.add_argument('--approve',action='store_true',required=True)
    collect=sub.add_parser('collect'); collect.add_argument('--cv',type=Path); collect.add_argument('--github')
    sub.add_parser('rankings')
    health=sub.add_parser('github-health'); health.add_argument('owner'); health.add_argument('--analyzer',type=Path, required=True)
    args=parser.parse_args(); root=args.private; root.mkdir(parents=True,exist_ok=True)
    if args.command=='init':
        for name in ['profile','projects']:
            dest=root/(name+'.json')
            if not dest.exists():
                shutil.copyfile(ROOT/'examples'/(name+'.example.json'),dest)
        print('Fictional examples copied to private/. Replace every fictional fact; no approval seal was created.')
    elif args.command=='collect':
        inbox=root/'inbox'; inbox.mkdir(exist_ok=True)
        if args.cv:
            if args.cv.suffix.lower()=='.pdf':
                import fitz
                with fitz.open(args.cv) as doc:
                    text='\n'.join(p.get_text() for p in doc)
            else:
                text=args.cv.read_text(encoding='utf-8-sig')
            (inbox/'previous-cv.txt').write_text(text,encoding='utf-8')
        if args.github:
            # Uses the user's existing gh authentication; never reads or stores its token.
            data=subprocess.check_output(['gh','repo','list',args.github,'--limit','1000','--json',
                'nameWithOwner,url,description,isPrivate,languages,defaultBranchRef'],text=True)
            (inbox/'github-repositories.json').write_text(data,encoding='utf-8')
        print('Collected untrusted candidate evidence in private/inbox/. Inspect implementation and confirm contributions before approving bullets.')
    elif args.command=='validate':
        p,c=validate_private(root); print(f"Valid record structure: {len(p['skills'])} skills, {len(c['projects'])} projects. Facts still require human review.")
    elif args.command=='seal':
        seal(root); print('Local approval seal saved. Any later fact edit invalidates it.')
    elif args.command=='rankings':
        p,c=validate_private(root)
        lines=['# Project inventory and role rankings','', 'Scores are evidence-based judgments, not hiring predictions. Presentation is separate from technical depth.','']
        for project in c['projects']:
            lines += ['## '+project['name'],str(project.get('url') or project['access']),
                'Description: '+project['description'], 'Skills: '+', '.join(project['technologies']), 'Contribution: '+project['contribution'],
                'Engineering: '+project['engineering'], 'Limits: '+project['limits'],
                'Evidence: '+str(project['evidence']), 'Ratings: '+str(project['role_ratings']),
                'Reasons: '+str(project['rating_reasons']),'']
        roles=sorted({role for p in c['projects'] for role in p['role_ratings']})
        for role in roles:
            lines += ['## '+role+' ranking']+[f"{i+1}. {p['name']} ({p['role_ratings'].get(role,0)}/5)" for i,p in enumerate(sorted(c['projects'],key=lambda p:p['role_ratings'].get(role,0),reverse=True))]+['']
        (root/'PROJECTS.md').write_text('\n'.join(lines),encoding='utf-8'); print('Wrote private/PROJECTS.md')
    elif args.command=='github-health':
        subprocess.run(['node',str(ROOT/'integrations'/'github-health.mjs'),str(args.analyzer.resolve()),args.owner,str(root/'github-health.json')],check=True)

if __name__=='__main__':
    main()
