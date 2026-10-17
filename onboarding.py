"""Local evidence records and approval seals. Never imports career data into source code."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from extract import CVError

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_private(root, require_seal=False):
    root = Path(root)
    try:
        profile = json.loads((root/'profile.json').read_text(encoding='utf-8-sig'))
        catalog = json.loads((root/'projects.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise CVError('Finish onboarding: private/profile.json and private/projects.json are required.') from exc
    for key in ['name', 'headline', 'availability', 'education', 'contacts', 'skills']:
        if not profile.get(key):
            raise CVError('Missing profile field: ' + key)
    if not isinstance(profile['skills'],list) or len(set(profile['skills'])) != len(profile['skills']):
        raise CVError('Skills must be a unique list of verified names.')
    if not all(isinstance(s,str) and s.strip() for s in profile['skills']):
        raise CVError('Skill names must be nonempty strings.')
    if any(not e.get('title') or not e.get('detail') or not e.get('dates') for e in profile['education']):
        raise CVError('Education requires title, detail (including degree status) and dates.')
    for contact in profile['contacts']:
        if not contact.get('label') or urlparse(contact.get('url','')).scheme not in {'http','https','mailto','tel'}:
            raise CVError('Invalid contact label or URL scheme.')
    projects = catalog.get('projects', [])
    if len(projects) < 3:
        raise CVError('Provide at least three distinct evidence-backed projects before tailoring.')
    ids, bullets = set(), set()
    for p in projects:
        pid = p.get('id','')
        if not re.fullmatch('[a-z0-9-]+',pid) or pid in ids:
            raise CVError('Project IDs must be unique lowercase slugs.')
        ids.add(pid)
        for field in ['name','description','technologies','engineering','best_fit','limits','evidence','contribution','role_ratings','rating_reasons']:
            if not p.get(field):
                raise CVError(f'{pid}: missing {field}')
        if p.get('access') not in {'public','private','local'}:
            raise CVError(pid+': invalid access status')
        if p.get('url') and (p['access'] != 'public' or urlparse(p['url']).scheme != 'https'):
            raise CVError(pid+': only public HTTPS evidence links may appear in a CV')
        for field in ['technical_depth','evidence_strength', 'presentation_readiness']:
            if type(p.get(field)) is not int or not 0 <= p[field] <= 5:
                raise CVError(pid+': ratings must be integers from 0 to 5')
        if any(type(n) is not int or not 0 <= n <= 5 for n in p['role_ratings'].values()):
            raise CVError(pid+': invalid role relevance rating')
        if len(p.get('bullets',[])) < 2:
            raise CVError(pid+': two approved bullet variants are required')
        for b in p['bullets']:
            if not b.get('id','').startswith(pid+'.') or b['id'] in bullets or not b.get('text') or not b.get('sources'):
                raise CVError(pid+': each unique bullet needs supporting source references')
            bullets.add(b['id'])
        if require_seal and not p.get('approved'):
            raise CVError(pid+': contribution and bullets need user approval before sealing')
    if require_seal:
        try:
            seal = json.loads((root/'approval.json').read_text())
        except (OSError,ValueError) as exc:
            raise CVError('Review facts with the user and run manage.py seal --approve.') from exc
        if seal != {f:digest(root/f) for f in ['profile.json','projects.json']}:
            raise CVError('Private facts changed. Review and reseal before generating a CV.')
    return profile, catalog

def seal(root):
    root=Path(root)
    profile,catalog=validate_private(root)
    if not all(p.get('approved') for p in catalog['projects']):
        raise CVError('Each project must have approved=true after user review.')
    (root/'approval.json').write_text(json.dumps({f:digest(root/f) for f in ['profile.json','projects.json']},indent=2))
    return profile,catalog
