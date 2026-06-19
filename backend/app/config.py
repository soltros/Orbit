import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")
    
    # SQLite configuration
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/orbit.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Navidrome/Subsonic Connection
    SUBSONIC_URL = os.environ.get("SUBSONIC_URL")
    SUBSONIC_USER = os.environ.get("SUBSONIC_USER")
    SUBSONIC_PASS = os.environ.get("SUBSONIC_PASS")  # Can be raw password or token/salt
    
    # LLM Settings
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")  # openai or anthropic
