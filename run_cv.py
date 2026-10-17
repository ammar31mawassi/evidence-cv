"""Direct CLI path: same worker as n8n, no workflow server required."""
import argparse
import time
from app import create, read, Request, STATE

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('url'); parser.add_argument('--description-file')
    args=parser.parse_args()
    from pathlib import Path
    description=Path(args.description_file).read_text(encoding='utf-8-sig') if args.description_file else None
    STATE.mkdir(parents=True,exist_ok=True)
    result=create(Request(url=args.url,description=description))
    while True:
        result=read(result['id'])
        if result['status']=='completed':
            print(result['path']); return
        if result['status']=='failed':
            raise SystemExit(result['error'])
        time.sleep(1)

if __name__=='__main__': main()
