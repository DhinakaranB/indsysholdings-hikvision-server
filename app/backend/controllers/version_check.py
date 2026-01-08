import hmac
import hashlib
import base64
import json
import requests
# iclmport time
import urllib3
from email.utils import formatdate
 
 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app_key = "11566257"
app_secret = "DBntId5f4LZPfW1Ik5Yh"
method = "POST"
host = "127.0.0.1"
api_path = "/artemis/api/common/v1/version"
url = f"https://{host}{api_path}"
 
accept = "application/json"
content_type = "application/json;charset=UTF-8"
body_json = {}
body = json.dumps(body_json)
 
content_md5 = base64.b64encode(hashlib.md5(body.encode('utf-8')).digest()).decode('utf-8')
signature_headers = "x-ca-key"
headers_to_sign = f"x-ca-key:{app_key}\n"
 
string_to_sign = (
    f"{method}\n"
    f"{accept}\n"
    f"{content_md5}\n"
    f"{content_type}\n"  
    f"{headers_to_sign}"
    f"{api_path}"
)
 
hmac_sha256 = hmac.new(
    app_secret.encode('utf-8'),
    string_to_sign.encode('utf-8'),
    hashlib.sha256
)
signature = base64.b64encode(hmac_sha256.digest()).decode('utf-8')
 
headers = {
    "Accept": accept,
    "Content-MD5": content_md5,
    "Content-Type": content_type,
    "X-Ca-Key": app_key,
    "X-Ca-Signature-Headers": signature_headers,
    "X-Ca-Signature": signature
}
 
print("==== StringToSign ====")
print(string_to_sign)
print("\nGenerated Signature:", signature)
print("\nHeaders:", json.dumps(headers, indent=4))
print("\nURL:", url)
 
response = requests.post(url, headers=headers, data=body, verify=False)
 
print("\n==== Response ====")
print("Status Code:", response.status_code)
print("Body:", response.text)