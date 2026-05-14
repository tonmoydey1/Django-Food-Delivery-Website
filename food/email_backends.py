import base64
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """Send Django EmailMessage objects through the Resend HTTPS API."""

    api_url = 'https://api.resend.com/emails'

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not settings.RESEND_API_KEY:
            logger.error('RESEND_API_KEY is not configured.')
            return 0

        sent_count = 0
        for message in email_messages:
            try:
                self._send_message(message)
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception('Resend email failed for %s', ', '.join(message.to))
            else:
                sent_count += 1
        return sent_count

    def _send_message(self, message):
        payload = self._payload_from_message(message)
        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {settings.RESEND_API_KEY}',
                'Content-Type': 'application/json',
                'User-Agent': 'tonmoy-eats-django/1.0',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
                if response.status >= 300:
                    raise RuntimeError(f'Resend returned HTTP {response.status}.')
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'Resend returned HTTP {exc.code}: {body}') from exc

    def _payload_from_message(self, message):
        html_body = ''
        for content, mimetype in getattr(message, 'alternatives', []):
            if mimetype == 'text/html':
                html_body = content
                break

        payload = {
            'from': settings.RESEND_FROM_EMAIL or message.from_email,
            'to': message.to,
            'subject': message.subject,
            'text': message.body or '',
        }
        if html_body:
            payload['html'] = html_body
        if message.cc:
            payload['cc'] = message.cc
        if message.bcc:
            payload['bcc'] = message.bcc

        attachments = self._attachments_from_message(message)
        if attachments:
            payload['attachments'] = attachments
        return payload

    def _attachments_from_message(self, message):
        attachments = []
        for attachment in message.attachments:
            if isinstance(attachment, tuple):
                filename, content, _mimetype = attachment
            else:
                filename = attachment.get_filename()
                content = attachment.get_payload(decode=True)

            if isinstance(content, str):
                content = content.encode('utf-8')
            attachments.append({
                'filename': filename,
                'content': base64.b64encode(content).decode('ascii'),
            })
        return attachments
