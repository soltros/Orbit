import os
import json
from flask import Blueprint, current_app, jsonify, request
from app import db
from app.models import Track, QueueItem, InteractionHistory
from app.subsonic import SubsonicClient

setup_bp = Blueprint('setup', __name__, url_prefix='/api/setup')

def get_settings_path():
    db_path = current_app.config.get("DATABASE_PATH", "/app/data/orbit.db")
    return os.path.join(os.path.dirname(db_path), "settings.json")

@setup_bp.route('/status', methods=['GET'])
def setup_status():
    """Checks if Orbit needs initial configuration."""
    url = current_app.config.get('SUBSONIC_URL')
    if not url or url.startswith("your-") or url == "":
        return jsonify({"needs_setup": True})
        
    return jsonify({"needs_setup": False})

@setup_bp.route('/config', methods=['GET'])
def get_config():
    """Returns the current configuration (with passwords/keys masked or omitted for security)."""
    return jsonify({
        "SUBSONIC_URL": current_app.config.get('SUBSONIC_URL', ''),
        "SUBSONIC_USER": current_app.config.get('SUBSONIC_USER', ''),
        "RECOMMENDATION_MODE": current_app.config.get('RECOMMENDATION_MODE', 'local'),
        "LLM_PROVIDER": current_app.config.get('LLM_PROVIDER', 'openai'),
        "HAS_OPENAI_KEY": bool(current_app.config.get('OPENAI_API_KEY')),
        "HAS_ANTHROPIC_KEY": bool(current_app.config.get('ANTHROPIC_API_KEY')),
        "HAS_LASTFM_KEY": bool(current_app.config.get('LASTFM_API_KEY'))
    })

@setup_bp.route('/save', methods=['POST'])
def save_settings():
    """Saves persistent configuration to settings.json and live-reloads config."""
    data = request.get_json(silent=True) or {}
    
    url = data.get('SUBSONIC_URL')
    user = data.get('SUBSONIC_USER')
    password = data.get('SUBSONIC_PASS')
    
    if not url or not user or not password:
        return jsonify({"status": "error", "message": "Subsonic URL, Username, and Password are required."}), 400
        
    # Verify the connection before saving
    try:
        client = SubsonicClient(base_url=url, username=user, password=password)
        client.ping()
    except Exception as e:
        return jsonify({"status": "error", "message": f"Could not connect to Navidrome: {str(e)}"}), 400

    # Check if URL is changing to trigger a database wipe
    existing_url = current_app.config.get('SUBSONIC_URL')
    url_changed = existing_url and existing_url != url
    
    if url_changed:
        try:
            QueueItem.query.delete()
            InteractionHistory.query.delete()
            Track.query.delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to wipe old server data: {str(e)}")

    # Build settings dict
    settings = {}
    settings_path = get_settings_path()
    
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        except Exception:
            pass
            
    # Update settings
    for key in ['SUBSONIC_URL', 'SUBSONIC_USER', 'SUBSONIC_PASS', 
                'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'LASTFM_API_KEY', 'LLM_PROVIDER', 'RECOMMENDATION_MODE']:
        if key in data:
            settings[key] = data[key]
            # Live-reload into current app config
            current_app.config[key] = data[key]
            
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)
        return jsonify({"status": "success", "message": "Settings saved successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Failed to save settings: {str(e)}")
        return jsonify({"status": "error", "message": "Could not write settings file."}), 500
