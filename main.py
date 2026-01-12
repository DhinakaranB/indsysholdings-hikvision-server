import sys
import os
import logging
import uvicorn
import json

# --- PATH FIXER ---
# This ensures we always find files next to the EXE, not in the temp folder
if getattr(sys, 'frozen', False):
    # If running as an EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # If running as a script (python main.py)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup logging
log_file = os.path.join(BASE_DIR, 'service_debug.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s: %(message)s')

def get_protocol_config():
    """Reads server_config.json from the correct folder"""
    config_path = os.path.join(BASE_DIR, 'server_config.json')
    try:
        if not os.path.exists(config_path):
            logging.warning(f"Config file not found at {config_path}. Defaulting to HTTP.")
            return "http"
            
        with open(config_path, 'r') as f:
            data = json.load(f)
            mode = data.get("protocol", "http").lower()
            logging.info(f"Read config: {mode}")
            return mode
    except Exception as e:
        logging.warning(f"Config read failed ({e}), defaulting to HTTP.")
        return "http"

if __name__ == '__main__':
    logging.info(f"Service starting from: {BASE_DIR}")
    
    # 1. Load the App
    try:
        from app import app
        # Or: from app.backend import app (depending on your structure)
    except ImportError:
        try:
            from app.backend import app
        except ImportError:
            logging.error("CRITICAL: Could not find 'app'.")
            sys.exit(1)

    # 2. Check Protocol
    protocol = get_protocol_config()
    logging.info(f"Starting VMS Controller in {protocol.upper()} mode...")

    # 3. Start Uvicorn
    try:
        if protocol == "https":
            # Look for certs in the BASE_DIR (next to the exe)
            cert_file = os.path.join(BASE_DIR, "cert.pem")
            key_file = os.path.join(BASE_DIR, "key.pem")
            
            if not os.path.exists(cert_file) or not os.path.exists(key_file):
                logging.error(f"CRITICAL: HTTPS selected but keys not found at: {cert_file}")
                # Fallback to HTTP but DISABLE log_config to prevent crash
                uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
            else:
                # HTTPS Mode with log_config disabled
                uvicorn.run(app, host="0.0.0.0", port=8000, ssl_certfile=cert_file, ssl_keyfile=key_file, log_config=None)
        else:
            # HTTP Mode with log_config disabled
            uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
            
    except Exception as e:
        logging.error(f"Server crashed: {e}")