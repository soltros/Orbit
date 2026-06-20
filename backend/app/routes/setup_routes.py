import os
import json
import shutil
from flask import Blueprint, current_app, jsonify, request, session, send_file
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
    if not current_app.config.get('SETUP_COMPLETED'):
        user = session.get('subsonic_user')
        if user == 'admin':
            return jsonify({"needs_setup": True})
        
    return jsonify({"needs_setup": False})

@setup_bp.route('/config', methods=['GET'])
def get_config():
    """Returns the current configuration (with passwords/keys masked or omitted for security)."""
    user = session.get('subsonic_user')
    if user != current_app.config.get('SUBSONIC_USER'):
        return jsonify({"status": "error", "message": "Unauthorized. Admin access required."}), 403

    return jsonify({
        "SUBSONIC_URL": current_app.config.get('SUBSONIC_URL', ''),
        "SUBSONIC_USER": current_app.config.get('SUBSONIC_USER', ''),
        "RECOMMENDATION_MODE": current_app.config.get('RECOMMENDATION_MODE', 'local'),
        "LLM_PROVIDER": current_app.config.get('LLM_PROVIDER', 'openai'),
        "HAS_OPENAI_KEY": bool(current_app.config.get('OPENAI_API_KEY')),
        "HAS_ANTHROPIC_KEY": bool(current_app.config.get('ANTHROPIC_API_KEY')),
        "HAS_LASTFM_KEY": bool(current_app.config.get('LASTFM_API_KEY')),
        "HAS_LASTFM_SECRET": bool(current_app.config.get('LASTFM_API_SECRET'))
    })

@setup_bp.route('/save', methods=['POST'])
def save_settings():
    """Saves persistent configuration to settings.json and live-reloads config."""
    # If a setup already exists, only the admin user can save new settings
    existing_url = current_app.config.get('SUBSONIC_URL')
    if existing_url and existing_url != "":
        user = session.get('subsonic_user')
        if user != current_app.config.get('SUBSONIC_USER'):
            return jsonify({"status": "error", "message": "Unauthorized. Admin access required."}), 403

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
                'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'LASTFM_API_KEY', 'LASTFM_API_SECRET', 'LLM_PROVIDER', 'RECOMMENDATION_MODE']:
        if key in data:
            settings[key] = data[key]
            # Live-reload into current app config
            current_app.config[key] = data[key]
            
    # Mark setup as completed
    settings['SETUP_COMPLETED'] = True
    current_app.config['SETUP_COMPLETED'] = True
            
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)
        return jsonify({"status": "success", "message": "Settings saved successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Failed to save settings: {str(e)}")
        return jsonify({"status": "error", "message": "Could not write settings file."}), 500

@setup_bp.route('/users', methods=['GET'])
def get_users():
    """Returns a list of all Orbit users (UserProfiles). Admin only."""
    user = session.get('subsonic_user')
    if user != current_app.config.get('SUBSONIC_USER'):
        return jsonify({"status": "error", "message": "Unauthorized. Admin access required."}), 403

    from app.models import UserProfile, InteractionHistory
    try:
        profiles = UserProfile.query.all()
        users_list = []
        for p in profiles:
            play_count = InteractionHistory.query.filter_by(user_id=p.id, action='play').count()
            users_list.append({
                "id": p.id,
                "username": p.username,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "play_count": play_count
            })
        return jsonify({"status": "success", "users": users_list}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching users: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to fetch users."}), 500

@setup_bp.route('/export-db', methods=['GET'])
def export_db():
    """Exports the SQLite database file."""
    user = session.get('subsonic_user')
    if user != current_app.config.get('SUBSONIC_USER'):
        return jsonify({"status": "error", "message": "Unauthorized. Admin access required."}), 403

    db_path = current_app.config.get("DATABASE_PATH", "/app/data/orbit.db")
    if not os.path.exists(db_path):
        return jsonify({"status": "error", "message": "Database file not found."}), 404

    return send_file(db_path, as_attachment=True, download_name="orbit_backup.db")

@setup_bp.route('/import-db', methods=['POST'])
def import_db():
    """Imports and overwrites the SQLite database file."""
    user = session.get('subsonic_user')
    if user != current_app.config.get('SUBSONIC_USER'):
        return jsonify({"status": "error", "message": "Unauthorized. Admin access required."}), 403

    if 'db_file' not in request.files:
        return jsonify({"status": "error", "message": "No file provided."}), 400

    file = request.files['db_file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Empty file provided."}), 400

    db_path = current_app.config.get("DATABASE_PATH", "/app/data/orbit.db")
    
    try:
        # Create a backup of the current db just in case
        if os.path.exists(db_path):
            shutil.copy2(db_path, f"{db_path}.bak")
            
        file.save(db_path)
        return jsonify({"status": "success", "message": "Database imported successfully! Please restart Orbit to apply changes."}), 200
    except Exception as e:
        current_app.logger.error(f"Error importing database: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to import database."}), 500
