"""Gmail sender using an existing locally authorized gmail.send OAuth token."""
import base64
import json
import os
from email.message import EmailMessage
from pathlib import Path
import requests

class DeliveryUncertain(RuntimeError):
    pass

def send(subject, body, config, token_path=None):
    if config.get('mode') != 'gmail':
        raise RuntimeError('Real digest delivery requires mail.mode=gmail; no silent preview fallback.')
    path=Path(token_path or os.environ.get('GMAIL_TOKEN_FILE','/mail-secrets/gmail-token.json'))
    token=json.loads(path.read_text(encoding='utf-8-sig'))
    # Refresh on each digest; no dependency on a potentially stale expiry field.
    refreshed=requests.post('https://oauth2.googleapis.com/token',data={
        'client_id':token['client_id'],'client_secret':token['client_secret'],
        'refresh_token':token['refresh_token'],'grant_type':'refresh_token'},timeout=(10,30))
    if not refreshed.ok:
        raise RuntimeError('Gmail authorization needs renewal; digest was not sent.')
    access=refreshed.json()['access_token']
    message=EmailMessage()
    message['From']=config['sender'];message['To']=config['recipient'];message['Subject']=subject
    message.set_content(body)
    raw=base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
    try:
        result=requests.post('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
             headers={'Authorization':'Bearer '+access},json={'raw':raw},timeout=(10,45))
    except requests.RequestException as exc:
        raise DeliveryUncertain('Gmail delivery outcome is uncertain; automatic resend suppressed.') from exc
    if result.status_code >= 500:
        raise DeliveryUncertain('Gmail returned a server error; outcome uncertain; resend suppressed.')
    if not result.ok:
        raise RuntimeError('Gmail rejected the digest (HTTP '+str(result.status_code)+'); no delivery confirmed.')
    result=result.json()
    if not result.get('id'): raise DeliveryUncertain('Gmail response omitted its message ID; resend suppressed.')
    return result['id']
