# backend/services/signature_service.py (FINAL VERSION WITH DYNAMIC LOAD)

import hmac
import hashlib
import base64
import json
import os 
from pathlib import Path 
# from backend.config import settings

from app.backend.config import ARTEMIS_HOST # Statically imported host
from app.backend.config import APP_KEY, APP_SECRET # Import the empty placeholders

# Define the file path for dynamic VMS credentials
VMS_KEYS_FILE = "vms_keys.json" 

def load_vms_credentials():
    """Loads APP_KEY and APP_SECRET from the local JSON file (set by the UI)."""
    # The VMS_KEYS_FILE is expected to be next to the executable (in the dist folder)
    if os.path.exists(VMS_KEYS_FILE):
        try:
            with open(VMS_KEYS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('APP_KEY', ''), data.get('APP_SECRET', '')
        except Exception:
            pass
    # Return empty strings if file or keys are missing
    return '', ''

# Load credentials once when the service starts
VMS_APP_KEY, VMS_APP_SECRET = load_vms_credentials()


class SignatureService:

    @staticmethod
    def generate_signature(method, api_path, body):
        
        # 1. Use the dynamically loaded credentials
        APP_KEY = VMS_APP_KEY
        APP_SECRET = VMS_APP_SECRET
        # HOST = settings.ARTEMIS_HOST
        if not APP_KEY or not APP_SECRET:
             # This will trigger if the user hasn't saved the credentials yet
             raise Exception("VMS Credentials not configured. Please set them in the UI.")

        # 2. Signature calculation logic (uses APP_KEY, APP_SECRET)
        body_str = json.dumps(body)
        content_md5 = base64.b64encode(hashlib.md5(body_str.encode('utf-8')).digest()).decode('utf-8')

        accept = "application/json"
        content_type = "application/json;charset=UTF-8"
        signature_headers = "x-ca-key"
        
        headers_to_sign = f"x-ca-key:{APP_KEY}\n"

        string_to_sign = (
            f"{method}\n"
            f"{accept}\n"
            f"{content_md5}\n"
            f"{content_type}\n"
            f"{headers_to_sign}"
            f"{api_path}"
        )

        hmac_sha256 = hmac.new(APP_SECRET.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256)
        signature = base64.b64encode(hmac_sha256.digest()).decode('utf-8')

        return {
            "Content-MD5": content_md5,
            "X-Ca-Key": APP_KEY,
            "X-Ca-Signature": signature,
            "X-Ca-Signature-Headers": signature_headers,
            # "Host": ARTEMIS_HOST # Static host is still used
            "Host": ARTEMIS_HOST
        }