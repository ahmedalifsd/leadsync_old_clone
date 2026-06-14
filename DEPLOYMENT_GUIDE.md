# LeadSync Deployment Notes

## Auto-Renew + Manual Payment Workflow

LeadSync now supports an auto-renew workflow where payment is still manual.

- Auto-renew enabled owners get an automatic renewal request before expiry.
- Reminder notifications/emails are sent on configured days.
- After expiry, a grace period is applied.
- If payment is still not approved after grace period, subscription is auto-deactivated.

## Required Environment Variables

Add these to your `.env`:

```env
RENEWAL_NOTICE_DAYS=7
RENEWAL_GRACE_DAYS=3
RENEWAL_REMINDER_DAYS=7,3,1,0
SITE_BASE_URL=https://your-domain.com

# Payment proof storage backend
PAYMENT_PROOF_STORAGE_BACKEND=gdrive

# Personal Google Drive (recommended): OAuth user credentials
GOOGLE_DRIVE_OAUTH_CLIENT_ID=your_google_oauth_client_id
GOOGLE_DRIVE_OAUTH_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN=your_google_oauth_refresh_token

# Google Drive API settings
# Option A (recommended for server): put JSON key as base64 in env
GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_BASE64=your_base64_encoded_service_account_json

# Option B: raw JSON in env (works, but harder to manage safely)
GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# Option C: server file path (old way)
GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE=/path/to/google-service-account.json
GOOGLE_DRIVE_PROOF_FOLDER_ID=your_google_drive_folder_id
GOOGLE_DRIVE_PUBLIC_LINK=True

# Optional: only used if backend=filesystem
PAYMENT_PROOF_ROOT=D:\\DriveFolder\\LeadSyncProofs
PAYMENT_PROOF_BASE_URL=/payment-proofs/
```

## Daily Command (Required)

Run this command daily via scheduler:

```bash
python manage.py process_renewals
```

## Windows Task Scheduler Example

Program/script:

```text
python
```

Arguments:

```text
manage.py process_renewals
```

Start in:

```text
D:\My Projects\Combine Work\LeadSync
```

Suggested schedule: every day at 9:00 AM (server local time).

## Verify

Run:

```bash
python manage.py migrate
python manage.py check
python manage.py process_renewals --help
```

## Payment Proof Storage Notes

- Access URL is stored in database field `Payment.payment_proof_access_url`.
- Site renders proof links using this DB URL.
- If backend is `gdrive`, files are saved in Google Drive folder directly.
- If backend is `filesystem`, files are saved in `PAYMENT_PROOF_ROOT` and served via `PAYMENT_PROOF_BASE_URL`.
- For personal Gmail Drive, prefer OAuth user credentials. Service-account uploads can hit quota errors on personal Drive.

## Personal Google Drive Setup (Best for Gmail 15GB)

Use this if your folder is in your personal Google account (not Workspace shared drive).

1. In Google Cloud Console:
- Go to APIs & Services > OAuth consent screen
- Configure app (External), add your Gmail as Test User
- Enable Google Drive API

2. Create OAuth Client Credentials:
- APIs & Services > Credentials > Create Credentials > OAuth client ID
- App type: Desktop app (easy for refresh token)
- Save Client ID + Client Secret

3. Get refresh token (one-time):
- Open OAuth 2.0 Playground
- Settings icon: enable Use your own OAuth credentials
- Add your Client ID and Client Secret
- Scope: `https://www.googleapis.com/auth/drive`
- Authorize, then Exchange authorization code
- Copy refresh_token

4. Set `.env`:

```env
PAYMENT_PROOF_STORAGE_BACKEND=gdrive
GOOGLE_DRIVE_OAUTH_CLIENT_ID=your_google_oauth_client_id
GOOGLE_DRIVE_OAUTH_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN=your_google_oauth_refresh_token
GOOGLE_DRIVE_PROOF_FOLDER_ID=your_google_drive_folder_id
GOOGLE_DRIVE_PUBLIC_LINK=True
```

5. Restart app and test upload.

Notes:
- OAuth method uploads as your own Google account, so your 15GB quota is used.
- Service account method is still supported, but best for Shared Drives / Workspace scenarios.

## Google Drive Browser Folder Setup (Recommended for Live)

Use this when you want direct Google Drive (browser folder), without local drive mount.

1. In Google Cloud Console:
- Create/select a project
- Enable **Google Drive API**

2. Create Service Account:
- Create service account
- Create key (JSON)
- Download JSON file to server (safe private path)

3. Share your Google Drive browser folder with service account email:
- Open folder in browser Google Drive
- Click Share
- Add service-account email (from JSON `client_email`)
- Give **Editor** access

4. Get folder ID:
- Folder URL example:
	`https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp`
- Folder ID is part after `/folders/`: `1AbCdEfGhIjKlMnOp`

5. Set `.env`:

```env
PAYMENT_PROOF_STORAGE_BACKEND=gdrive
GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_BASE64=your_base64_encoded_service_account_json
GOOGLE_DRIVE_PROOF_FOLDER_ID=1AbCdEfGhIjKlMnOp
GOOGLE_DRIVE_PUBLIC_LINK=True
```

6. Convert JSON key to base64 (recommended for server):

Windows PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("D:\path\leadsync-gdrive.json"))
```

Linux:

```bash
base64 -w 0 /var/www/secrets/leadsync-gdrive.json
```

Copy output into `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON_BASE64`.

7. Install dependencies and restart app:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py check
```

8. Test flow:
- Upload transaction proof from superadmin approval form
- File appears in Google Drive browser folder
- DB `payment_proof_access_url` stores usable link
- Site "View" button opens same file

## Windows Drive Setup (Optional, only if backend=filesystem)

1. Create a folder on the drive you want to use, for example:

```text
E:\LeadSync\transaction_proofs
```

2. Open your project `.env` and set:

```env
PAYMENT_PROOF_ROOT=E:\\LeadSync\\transaction_proofs
PAYMENT_PROOF_BASE_URL=/payment-proofs/
```

3. Run migrations/check:

```bash
python manage.py migrate
python manage.py check
```

4. Restart the Django server.

5. Test by approving any pending payment with proof image upload from super admin panel.

6. Verify results:
- File is physically saved inside `E:\LeadSync\transaction_proofs`
- DB field `payment_proof_access_url` is populated
- "View" link opens the same uploaded image in site

## If You Use Google Drive Desktop

If your Google Drive is mounted as a local path (example `G:\My Drive\LeadSyncProofs`), use that full path in `PAYMENT_PROOF_ROOT`.
