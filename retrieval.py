"""Small, deterministic BM25 retrieval over approved evidence; no vector service."""
import math
import re
from collections import Counter

STOP = set('a an and are as at be by for from in is it of on or the to with you your we our experience'.split())
STOP.update('student team project projects software developer engineer development developed implemented implementation system systems platform work working company join looking build built application applications'.split())

def words(text):
    aliases={'apis':'api','tests':'test','testing':'test','automated':'automation','databases':'database'}
    return [aliases.get(w,w) for w in re.findall(r'[a-z0-9][a-z0-9+#.-]*', text.lower()) if w not in STOP]

def bm25(query, documents):
    docs = [Counter(words(d)) for d in documents]
    avg = sum(sum(d.values()) for d in docs) / max(1, len(docs)) or 1
    result = [0.0] * len(docs)
    for term in set(words(query)):
        df = sum(term in d for d in docs)
        idf = math.log(1 + (len(docs) - df + .5) / (df + .5))
        for i, d in enumerate(docs):
            freq = d[term]
            result[i] += idf * freq * 2.2 / (freq + 1.2 * (.25 + .75 * sum(d.values()) / avg))
    return result

def evidence_bank(profile, catalog):
    records = []
    for project in catalog['projects']:
        if project.get('approved'):
            for bullet in project['bullets']:
                records.append({'id': bullet['id'], 'project_id': project['id'], 'text': bullet['text'],
                                'sources': bullet['sources'], 'limits': project['limits'],
                                'contribution': project['contribution'], 'url': project.get('url')})
    return records

def requirement_bank(text):
    """Bounded source excerpts, selected by ID rather than reconstructed by the model."""
    parts = re.split(r'\n+|(?<=[.!?;])\s+|\s+[•]\s+|\s+-\s+|\s+(?=(?:Strong [Ee]xperience|Experience (?:working|with|in)|Experienced with|Deep knowledge|Ability to|Coding skills|Knowledge of|Understanding of|Excellent |Independent,|Bachelor[’\x27]s degree))', text)
    # Normalized HTML often has no line breaks: recover requirement sentences.
    markers = re.compile(r'experience|proficien|knowledge|degree|student|python|java|c\+\+|sql|react|required|qualif|ability|דרישות|ניסיון|סטודנט', re.I)
    candidates = []
    for part in parts:
        part = re.sub(r'\s+', ' ', part).strip(' -•')
        if not markers.search(part) or len(part) < 15:
            continue
        # Exact contiguous segments only, including long sentences.
        while len(part) > 300:
            boundary = part.rfind(' ', 120, 300)
            candidates.append(part[:boundary]); part = part[boundary:].lstrip()
        if len(part) >= 15:
            candidates.append(part)
    candidates = list(dict.fromkeys(candidates))
    candidates.sort(key=lambda value:bool(re.search(r'required|experience|proficien|knowledge|degree|familiar|must|ability|qualifications|ניסיון|דרישות',value,re.I)),reverse=True)
    candidates=candidates[:45]
    return [{'id': f'R{i+1}', 'text': value} for i, value in enumerate(candidates)]
