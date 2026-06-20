import os
import json
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

def load_persistent_settings():
    settings_path = os.environ.get("DATABASE_PATH", "/app/data/orbit.db")
    settings_file = os.path.join(os.path.dirname(settings_path), "settings.json")
    settings = {}
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)
        except Exception as e:
            print(f"Error loading settings.json: {e}")
            
    # Production security: ensure we have a persistent SECRET_KEY
    if "SECRET_KEY" not in settings and not os.environ.get("SECRET_KEY"):
        import secrets
        settings["SECRET_KEY"] = secrets.token_hex(32)
        try:
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving generated SECRET_KEY to settings.json: {e}")
            
    return settings

_persistent = load_persistent_settings()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or _persistent.get("SECRET_KEY")
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_HTTPONLY = True
    
    # SQLite configuration
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/orbit.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Navidrome/Subsonic Connection
    SUBSONIC_URL = _persistent.get("SUBSONIC_URL") or os.environ.get("SUBSONIC_URL")
    SUBSONIC_USER = _persistent.get("SUBSONIC_USER") or os.environ.get("SUBSONIC_USER")
    SUBSONIC_PASS = _persistent.get("SUBSONIC_PASS") or os.environ.get("SUBSONIC_PASS")
    
    # LLM Settings
    OPENAI_API_KEY = _persistent.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = _persistent.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    LASTFM_API_KEY = _persistent.get("LASTFM_API_KEY") or os.environ.get("LASTFM_API_KEY")
    LASTFM_API_SECRET = _persistent.get("LASTFM_API_SECRET") or os.environ.get("LASTFM_API_SECRET")
    LLM_PROVIDER = _persistent.get("LLM_PROVIDER") or os.environ.get("LLM_PROVIDER", "openai")

    # Default recommendation engine mode ('llm' or 'local')
    RECOMMENDATION_MODE = _persistent.get("RECOMMENDATION_MODE") or os.environ.get("RECOMMENDATION_MODE", "llm")
    
    # Optional local track buffering to avoid constant remote streaming connections
    raw_buffering = _persistent.get("ENABLE_LOCAL_BUFFERING") or os.environ.get("ENABLE_LOCAL_BUFFERING", "true")
    ENABLE_LOCAL_BUFFERING = str(raw_buffering).lower() == "true"

