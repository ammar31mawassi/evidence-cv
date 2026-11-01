"""Interactive local Gmail send-only OAuth setup; never commit its output token."""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--client',type=Path,default=Path('private/client_secret.json'))
    parser.add_argument('--token',type=Path,default=Path('private/gmail-token.json'))
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise SystemExit('Install the setup helper: python -m pip install google-auth-oauthlib')
    if not args.client.is_file():raise SystemExit('Supply your Gmail Desktop OAuth client JSON with --client.')
    flow=InstalledAppFlow.from_client_secrets_file(str(args.client),['https://www.googleapis.com/auth/gmail.send'])
    creds=flow.run_local_server(host='localhost',bind_addr='127.0.0.1',port=args.port,open_browser=True,
        access_type='offline',prompt='consent',timeout_seconds=900,
        authorization_prompt_message='Complete the Gmail permission request in your browser.',
        success_message='Gmail authorized. You can close this tab and return to your CV workflow.')
    if not creds.refresh_token:raise SystemExit('No offline authorization returned; Gmail setup is incomplete.')
    args.token.parent.mkdir(parents=True,exist_ok=True)
    args.token.write_text(creds.to_json(),encoding='utf-8')
    print('Gmail send authorization saved locally. Retry discovery to send the digest.')


if __name__=='__main__':main()
