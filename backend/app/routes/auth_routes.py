from flask import Blueprint, jsonify, request, session, current_app
from app.subsonic import SubsonicClient

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    url = data.get('url') or current_app.config.get('SUBSONIC_URL')

    if not username or not password or not url:
        return jsonify({"status": "error", "message": "Username, password, and URL are required."}), 400

    try:
        # Check for initial setup admin credentials
        is_setup_admin = False
        if not current_app.config.get('SETUP_COMPLETED'):
            if username == 'admin' and password == 'admin123':
                is_setup_admin = True
                
        if not is_setup_admin:
            # Try to ping Subsonic server with these credentials
            client = SubsonicClient(
                base_url=url,
                username=username,
                password=password
            )
            client.ping()

        # If successful, save to session
        session.permanent = True
        session['subsonic_url'] = url
        session['subsonic_user'] = username
        session['subsonic_pass'] = password
        
        return jsonify({
            "status": "success", 
            "message": "Logged in successfully.",
            "user": username
        }), 200
    except Exception as e:
        current_app.logger.error(f"Login failed: {str(e)}")
        return jsonify({"status": "error", "message": f"Login failed: {str(e)}"}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully."}), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    user = session.get('subsonic_user')
    admin_user = current_app.config.get('SUBSONIC_USER')
    if user:
        is_setup_admin = not current_app.config.get('SETUP_COMPLETED') and user == 'admin'
        return jsonify({
            "status": "success", 
            "user": user,
            "url": session.get('subsonic_url'),
            "is_admin": is_setup_admin or user == admin_user
        }), 200
    return jsonify({"status": "error", "message": "Not authenticated."}), 401
