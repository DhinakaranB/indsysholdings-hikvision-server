import os

class Settings:
    # --- VMS / ARTEMIS CONFIGURATION ---
    # Replace this with your actual VMS Host IP/URL
    ARTEMIS_HOST = "https://192.168.1.100:443" 
    
    # These are placeholders; your signature_service loads the real ones from JSON
    APP_KEY = ""
    APP_SECRET = ""

    # --- SECURITY / JWT CONFIGURATION ---
    # Change this secret key for production!
    JWT_SECRET_KEY = "super_secret_key_change_me_in_production"
    JWT_ALGORITHM = "HS256"
    JWT_TOKEN_EXPIRE_MINUTES = 30

settings = Settings()

# Allow direct imports like "from config import ARTEMIS_HOST"
ARTEMIS_HOST = settings.ARTEMIS_HOST
APP_KEY = settings.APP_KEY
APP_SECRET = settings.APP_SECRET