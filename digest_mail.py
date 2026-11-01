"""Gmail delivery using dedicated local App Password or send-only OAuth credentials."""
import base64
import json
import os
import smtplib
import ssl
from contextlib import suppress
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
import requests

class DeliveryUncertain(RuntimeError):
    pass

def smtp_send(message, config):
    path=Path(os.environ.get('GMAIL_SMTP_FILE','/mail-secrets/smtp.json'))
    token=json.loads(path.read_text(encoding='utf-8-sig'))
    if token['username'].casefold()!=config['sender'].casefold():
        raise RuntimeError('Gmail sender must match the locally configured SMTP account.')
    message['Message-ID']=make_msgid(domain='evidence-cv.local')
    try:
        server=smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=45,context=ssl.create_default_context())
        try:server.login(token['username'],token['password'].replace(' ',''))
        except Exception:
            with suppress(OSError,smtplib.SMTPException):server.close()
            raise
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError('Gmail rejected the App Password. Run configure-gmail.ps1 to replace it.') from None
    except (OSError,smtplib.SMTPException):
        raise RuntimeError('Could not connect/sign in to Gmail SMTP; digest was not sent.') from None
    try:
        refused=server.send_message(message)
        if refused:raise RuntimeError('Gmail refused the digest recipient; no delivery confirmed.')
    except (smtplib.SMTPRecipientsRefused,smtplib.SMTPSenderRefused,smtplib.SMTPDataError):
        raise RuntimeError('Gmail SMTP rejected the digest; no delivery confirmed.') from None
    except (OSError,smtplib.SMTPException):
        raise DeliveryUncertain('SMTP delivery outcome is uncertain; automatic resend suppressed.') from None
    finally:
        with suppress(OSError,smtplib.SMTPException):server.close()
    return message['Message-ID']


def send(subject, body, config, token_path=None):
    message=EmailMessage()
    message['From']=config['sender'];message['To']=config['recipient'];message['Subject']=subject
    message.set_content(body)
    if config.get('mode')=='smtp':return smtp_send(message,config)
    if config.get('mode') != 'gmail':
        raise RuntimeError('Configure Gmail App Password (smtp) or dedicated OAuth (gmail); no silent preview fallback.')
    path=Path(token_path or os.environ.get('GMAIL_TOKEN_FILE','/mail-secrets/gmail-token.json'))
    token=json.loads(path.read_text(encoding='utf-8-sig'))
    # Refresh on each digest; no dependency on a potentially stale expiry field.
    refreshed=requests.post('https://oauth2.googleapis.com/token',data={
        'client_id':token['client_id'],'client_secret':token['client_secret'],
        'refresh_token':token['refresh_token'],'grant_type':'refresh_token'},timeout=(10,30))
    if not refreshed.ok:
        raise RuntimeError('Gmail authorization needs renewal; digest was not sent.')
    access=refreshed.json()['access_token']
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
