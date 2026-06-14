import io
import mimetypes
import os
import uuid
import json
import base64
import binascii

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage


class LocalPaymentProofStorage(FileSystemStorage):
    """Store transaction proof files in a configurable filesystem folder."""

    def __init__(self, *args, **kwargs):
        location = str(getattr(settings, 'PAYMENT_PROOF_ROOT', settings.MEDIA_ROOT))
        base_url = getattr(settings, 'PAYMENT_PROOF_BASE_URL', f"{settings.MEDIA_URL.rstrip('/')}/payments/proofs/")
        super().__init__(location=location, base_url=base_url)


class GoogleDrivePaymentProofStorage(Storage):
    """Store transaction proof files directly in Google Drive folder via API."""

    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        oauth_client_id = (getattr(settings, 'GOOGLE_DRIVE_OAUTH_CLIENT_ID', '') or '').strip()
        oauth_client_secret = (getattr(settings, 'GOOGLE_DRIVE_OAUTH_CLIENT_SECRET', '') or '').strip()
        oauth_refresh_token = (getattr(settings, 'GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN', '') or '').strip()
        oauth_token_uri = (getattr(settings, 'GOOGLE_DRIVE_OAUTH_TOKEN_URI', 'https://oauth2.googleapis.com/token') or '').strip()

        # Prefer OAuth user credentials for personal Google Drive uploads.
        if oauth_client_id and oauth_client_secret and oauth_refresh_token:
            from google.oauth2.credentials import Credentials as UserCredentials
            from googleapiclient.discovery import build

            credentials = UserCredentials(
                token=None,
                refresh_token=oauth_refresh_token,
                token_uri=oauth_token_uri,
                client_id=oauth_client_id,
                client_secret=oauth_client_secret,
                scopes=self.SCOPES,
            )
            self._service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
            return self._service

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = None

        creds_json_base64 = (getattr(settings, 'GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_BASE64', '') or '').strip()
        creds_json = (getattr(settings, 'GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON', '') or '').strip()
        creds_file = (getattr(settings, 'GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE', '') or '').strip()

        if creds_json_base64:
            try:
                decoded = base64.b64decode(creds_json_base64).decode('utf-8')
                info = json.loads(decoded)
                credentials = service_account.Credentials.from_service_account_info(info, scopes=self.SCOPES)
            except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError('GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_BASE64 is invalid.') from exc
        elif creds_json:
            try:
                info = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(info, scopes=self.SCOPES)
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError('GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON is invalid JSON.') from exc
        elif creds_file:
            credentials = service_account.Credentials.from_service_account_file(
                creds_file,
                scopes=self.SCOPES,
            )
        else:
            raise ValueError(
                'Google Drive credentials are missing. Set one of: '
                'GOOGLE_DRIVE_OAUTH_CLIENT_ID + GOOGLE_DRIVE_OAUTH_CLIENT_SECRET + GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN, '
                'GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_BASE64, GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON, '
                'or GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE.'
            )

        self._service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
        return self._service

    @staticmethod
    def _extract_file_id(name):
        if not name:
            return ''
        name_str = str(name)
        # Format: file_id__userid-date-transactionid-imagename
        if '__' in name_str:
            return name_str.split('__', 1)[0]
        # Fallback for old format without file_id prefix (shouldn't happen with new code)
        return name_str

    def _save(self, name, content):
        folder_id = (getattr(settings, 'GOOGLE_DRIVE_PROOF_FOLDER_ID', '') or '').strip()
        if not folder_id:
            raise ValueError('GOOGLE_DRIVE_PROOF_FOLDER_ID is required for gdrive proof storage.')

        service = self._get_service()

        # Name format: {user_id}-{date}-{original_filename}
        original = os.path.basename(name or 'proof.jpg')
        safe_name = original  # Already formatted from views.py as {userid}-{date}-{original}

        mime_type = getattr(content, 'content_type', None) or mimetypes.guess_type(original)[0] or 'application/octet-stream'
        payload = content.read()
        media_stream = io.BytesIO(payload)

        from googleapiclient.http import MediaIoBaseUpload
        from googleapiclient.errors import HttpError

        media = MediaIoBaseUpload(media_stream, mimetype=mime_type, resumable=False)
        try:
            created = service.files().create(
                body={
                    'name': safe_name,
                    'parents': [folder_id],
                },
                media_body=media,
                fields='id',
            ).execute()
        except HttpError as exc:
            text = str(exc)
            if 'storageQuotaExceeded' in text or 'Service Accounts do not have storage quota' in text:
                raise ValueError(
                    'Google Drive upload failed: service-account uploads cannot use personal Drive quota. '
                    'Set OAuth user credentials (GOOGLE_DRIVE_OAUTH_CLIENT_ID, GOOGLE_DRIVE_OAUTH_CLIENT_SECRET, '
                    'GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN) to upload into your personal Google Drive.'
                ) from exc
            raise

        file_id = created.get('id')
        if not file_id:
            raise ValueError('Google Drive upload failed: missing file id.')

        if getattr(settings, 'GOOGLE_DRIVE_PUBLIC_LINK', True):
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'},
            ).execute()

        return f'{file_id}__{safe_name}'

    def exists(self, name):
        # File names are unique due to UUID; avoid redundant API call.
        return False

    def url(self, name):
        file_id = self._extract_file_id(name)
        if not file_id:
            return ''
        # Validate that file_id looks like a Google Drive file ID (not a filename)
        # Google Drive IDs are typically alphanumeric strings
        # Our filenames have format: userid-date-transid-name.ext
        if file_id and '-' in file_id[:5]:  # Filename patterns have hyphens early
            # This looks like a filename, not a proper file_id - return empty for safety
            return ''
        return f'https://drive.google.com/uc?export=view&id={file_id}'

    def delete(self, name):
        file_id = self._extract_file_id(name)
        if not file_id:
            return
        try:
            self._get_service().files().delete(fileId=file_id).execute()
        except Exception:
            # Avoid breaking app flow on delete failures.
            return


def get_payment_proof_storage():
    backend = (getattr(settings, 'PAYMENT_PROOF_STORAGE_BACKEND', 'filesystem') or 'filesystem').strip().lower()
    if backend == 'gdrive':
        return GoogleDrivePaymentProofStorage()
    return LocalPaymentProofStorage()
