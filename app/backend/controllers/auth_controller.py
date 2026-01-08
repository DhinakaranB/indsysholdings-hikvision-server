# backend/controllers/auth_controller.py

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.backend.services.auth_service import create_access_token, User 

router = APIRouter(tags=["Authentication"])

fake_users_db = {
    "vms_admin": {"username": "vms_admin", "password": "vms_secret"},
}

@router.post("/token")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    
    user_data = fake_users_db.get(form_data.username)
    
    if not user_data or form_data.password != user_data["password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user_data["username"]}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}