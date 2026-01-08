# backend/controllers/visitorlist_controller.py (FINAL WORKING CODE)

from fastapi import APIRouter, Depends, HTTPException, status 
import requests # <-- REQUIRED for the API call
from app.backend.services.signature_service import SignatureService
from app.backend.services.auth_service import get_current_user, User 
from typing import Annotated 

router = APIRouter(prefix="/visitor", tags=["Visitor List"])

# Define the FULL PATH for signature calculation (as required by VMS protocol)
FULL_API_PATH = "/artemis/api/visitor/v1/visitor/visitorInfo" 
# Define the SHORT PATH for execution (to prevent double slash 404)
SHORT_API_PATH = "/api/visitor/v1/visitor/visitorInfo" 


@router.post("/list")
# JWT Protection is now enabled
def get_visitor_list(request_body: dict, current_user: Annotated[User, Depends(get_current_user)]):
    
    # 1. Use the FULL_API_PATH for signature generation
    signature = SignatureService.generate_signature(
        "POST",
        FULL_API_PATH, 
        request_body
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json;charset=UTF-8",
        "Content-MD5": signature["Content-MD5"],
        "X-Ca-Key": signature["X-Ca-Key"],
        "X-Ca-Signature": signature["X-Ca-Signature"],
        "X-Ca-Signature-Headers": signature["X-Ca-Signature-Headers"],
    }

    # 2. CRITICAL FIX: EXECUTE THE API CALL
    # Use the SHORT_API_PATH for execution (Host + Short Path = Correct URL)
    try:
        response = requests.post(
            signature["Host"] + SHORT_API_PATH,
            headers=headers,
            json=request_body,
            verify=False
        )
    except requests.exceptions.RequestException as e:
         # Handle network/connection failures cleanly
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Network connection failed when reaching VMS host: {e}"
        )


    # 3. Debugging check: If VMS fails, return detailed error
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"VMS API Request Failed. Status: {response.status_code}. VMS Response: {response.text[:200]}"
        )

    return response.json()