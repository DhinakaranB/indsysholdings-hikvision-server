# backend/controllers/visitorregister_controller.py
from fastapi import APIRouter, Depends, HTTPException, status 
import requests
from app.backend.services.signature_service import SignatureService
from app.backend.services.auth_service import get_current_user, User 
from typing import Annotated 

router = APIRouter(prefix="/visitor", tags=["Visitor Registration"])

SHORT_API_PATH = "/api/visitor/v1/appointment"

FULL_API_PATH = "/artemis" + SHORT_API_PATH 


@router.post("/register")
# Assuming JWT is re-enabled for final production code
def register_visitor(request_body: dict, current_user: Annotated[User, Depends(get_current_user)]):

    # 1. Use the FULL_API_PATH for signature generation (CRITICAL FIX)
    signature = SignatureService.generate_signature(
        "POST",
        FULL_API_PATH, # <-- Uses the full path for signing
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

    # 2. Use the SHORT_API_PATH for execution (to prevent 404/double slash)
    response = requests.post(
        signature["Host"] + SHORT_API_PATH, # Host (ending in /artemis) + Short Path
        headers=headers,
        json=request_body,
        verify=False
    )
    
    # Debugging check: If VMS fails, return detailed error
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"VMS API Request Failed. Status: {response.status_code}. VMS Response: {response.text[:200]}"
        )

    return response.json()