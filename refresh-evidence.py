"""Export reviewed claim IDs, ownership limits and source links for local inspection."""
import json
from pathlib import Path
from onboarding import validate_private,digest
from retrieval import evidence_bank

def refresh(root):
    root=Path(root)
    profile,catalog=validate_private(root,True)
    bank={'source_hashes':{f:digest(root/f) for f in ['profile.json','projects.json']},
          'skills':profile['skills'],'education':profile['education'],
          'approved_claims':evidence_bank(profile,catalog),
          'limitations':'Source-linked reviewed claims; no inferred employment years, metrics or ownership.'}
    (root/'evidence-bank.json').write_text(json.dumps(bank,indent=2),encoding='utf-8')
    lines=['# Approved evidence bank','',f"{len(bank['approved_claims'])} claims across {len(catalog['projects'])} projects.",'']
    for b in bank['approved_claims']:
        lines += ['## '+b['id'],b['text'],'Contribution: '+b['contribution'],'Limits: '+b['limits'],
                  'Sources: '+str(b['sources']),'']
    (root/'EVIDENCE.md').write_text('\n'.join(lines),encoding='utf-8')
    return bank

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--private',type=Path,default=Path(__file__).parent/'private')
    args=parser.parse_args();bank=refresh(args.private)
    print('Exported',len(bank['approved_claims']),'approved evidence IDs.')
