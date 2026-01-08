# backend/controllers/doorlist_controller.py (FINAL WORKING CODE)

from fastapi import APIRouter, Depends, HTTPException, status
import requests
from app.backend.services.signature_service import SignatureService
from app.backend.services.auth_service import get_current_user, User # <-- JWT Imports
from typing import Annotated 

router = APIRouter(prefix="/door", tags=["Linked Doors"])

# Define the SHORT PATH endpoints (only the segment after /artemis)

ENDPOINTS = [
    "/api/resource/v1/acsDoor/advance/acsDoorList",
    "/api/resource/v1/acsDoor/acsDoorList"
]

@router.post("/linked")
# JWT PROTECTION RESTORED
def linked_door_list(current_user: Annotated[User, Depends(get_current_user)]):
    payload = {
        "pageNo": 1,
        "pageSize": 200
    }

    ok_res = None
    last_error = None

    # Try both APIs until one returns proper data
    for ep_short in ENDPOINTS:
        # CRITICAL FIX: Build the full path required for the VMS signature protocol
        ep_full_signature = "/artemis" + ep_short 

        signature = SignatureService.generate_signature(
            "POST",
            ep_full_signature, # <-- Use the FULL path for signature calculation
            payload
        )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "Content-MD5": signature["Content-MD5"],
            "X-Ca-Key": signature["X-Ca-Key"],
            "X-Ca-Signature": signature["X-Ca-Signature"],
            "X-Ca-Signature-Headers": signature["X-Ca-Signature-Headers"]
        }

        try:
            # Use the SHORT path (ep_short) for execution URL construction (Host + Short Path)
            response = requests.post(
                signature["Host"] + ep_short, 
                headers=headers,
                json=payload,
                verify=False
            )

            # Check if the API succeeded (Status 200 and VMS code 0)
            if str(response.status_code) == "200":
                data = response.json()
                if str(data.get("code")) == "0":
                    ok_res = data
                    break # Success, exit the loop
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:100]}"
        except Exception as e:
            last_error = str(e)

    if not ok_res:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"VMS API Request Failed. VMS Error: {last_error or 'Unknown VMS Error'}"
        )

    return {
        "status": 200,
        "doors": ok_res.get("data", {}).get("list", [])
    }