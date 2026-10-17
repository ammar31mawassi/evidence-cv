"""Fixed one-column design, populated exclusively from private verified records."""
from pathlib import Path

def make_template(profile):
    from engine import tex_escape as esc
    source=(Path(__file__).parent/'templates'/'resume.tex').read_text(encoding='utf-8')
    def entries(items):
        lines=[]
        for item in items:
            lines += [r'\cventry{'+esc(item['title'])+'}{'+esc(item.get('dates',''))+'}',esc(item.get('detail',''))+r'\par']
            if item.get('bullets'):
                lines += [r'\begin{itemize}'] + [r'\item '+esc(b) for b in item['bullets']] + [r'\end{itemize}']
        return '\n'.join(lines)
    contacts=r' \enspace | \enspace '.join(r'\href{'+c['url']+'}{'+esc(c['label'])+'}' for c in profile['contacts'])
    replacements={
      '@@NAME@@':esc(profile['name']), '@@HEADLINE@@':esc(profile['headline']),
      '@@AVAILABILITY@@':esc(profile['availability']), '@@CONTACTS@@':contacts,
      '@@EDUCATION@@':entries(profile['education']),
      '@@EXPERIENCE@@':entries(profile.get('experience',[])),
      '@@AWARDS@@':entries(profile.get('awards',[])),
      '@@LANGUAGES@@':esc(profile.get('languages','')),
    }
    for marker,value in replacements.items():
        source=source.replace(marker,value)
    return source
