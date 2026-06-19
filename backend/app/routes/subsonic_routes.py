import os
import threading
import requests
import subprocess
from flask import Blueprint, current_app, jsonify, request, Response, stream_with_context, send_file, session
from app.subsonic import SubsonicClient
from app.models import Track

CACHE_DIR = "/tmp/orbit_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def clear_local_buffer():
    """Empties the temporary audio cache directory."""
    if os.path.exists(CACHE_DIR):
        for f in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except Exception as e:
                pass

def buffer_track(track_id, app_config):
    """Background task to download a track into the local cache."""
    cache_path = os.path.join(CACHE_DIR, track_id)
    if os.path.exists(cache_path):
        return

    try:
        client = SubsonicClient(
            base_url=app_config['SUBSONIC_URL'],
            username=app_config['SUBSONIC_USER'],
            password=app_config['SUBSONIC_PASS']
        )
        url = client.get_stream_url(track_id)
        req = requests.get(url, stream=True, timeout=30)
        req.raise_for_status()
        
        # Download to a temporary file first to avoid serving incomplete files
        temp_path = cache_path + ".tmp"
        with open(temp_path, 'wb') as f:
            for chunk in req.iter_content(chunk_size=65536):
                f.write(chunk)
        os.rename(temp_path, cache_path)
    except Exception as e:
        print(f"Failed to buffer track {track_id}: {str(e)}")

def trigger_buffer_tracks(track_ids, app):
    """Triggers background buffering for a list of tracks if enabled."""
    if not app.config.get("ENABLE_LOCAL_BUFFERING", False):
        return
        
    config_copy = {
        'SUBSONIC_URL': session.get('subsonic_url') or app.config.get('SUBSONIC_URL'),
        'SUBSONIC_USER': session.get('subsonic_user') or app.config.get('SUBSONIC_USER'),
        'SUBSONIC_PASS': session.get('subsonic_pass') or app.config.get('SUBSONIC_PASS')
    }
    
    for tid in track_ids:
        threading.Thread(target=buffer_track, args=(tid, config_copy)).start()

subsonic_bp = Blueprint('subsonic', __name__, url_prefix='/api/subsonic')

@subsonic_bp.route('/cover/<track_id>')
def stream_cover(track_id):
    """Proxy the cover art from Navidrome."""
    client = SubsonicClient(
        base_url=current_app.config['SUBSONIC_URL'],
        username=current_app.config['SUBSONIC_USER'],
        password=current_app.config['SUBSONIC_PASS']
    )
    url = client.get_cover_art_url(track_id)
    try:
        req = requests.get(url, stream=True, timeout=10)
        req.raise_for_status()
        return Response(stream_with_context(req.iter_content(chunk_size=8192)), content_type=req.headers.get('Content-Type', 'image/jpeg'))
    except Exception as e:
        current_app.logger.error(f"Failed to fetch cover art for {track_id}: {str(e)}")
        return "Not found", 404

def get_subsonic_client():
    from flask import has_request_context
    url = user = password = None
    
    if has_request_context():
        url = session.get('subsonic_url')
        user = session.get('subsonic_user')
        password = session.get('subsonic_pass')
        
    url = url or current_app.config.get('SUBSONIC_URL')
    user = user or current_app.config.get('SUBSONIC_USER')
    password = password or current_app.config.get('SUBSONIC_PASS')
    
    if not url or not user or not password:
        raise Exception("Authentication required. Please log in.")
        
    return SubsonicClient(
        base_url=url,
        username=user,
        password=password
    )

@subsonic_bp.route('/ping', methods=['GET'])
def ping():
    try:
        client = get_subsonic_client()
        client.ping()
        return jsonify({"status": "success", "message": "Successfully connected to Subsonic/Navidrome server."}), 200
    except Exception as e:
        current_app.logger.error(f"Error in ping: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@subsonic_bp.route('/playlists', methods=['GET'])
def get_playlists():
    try:
        client = get_subsonic_client()
        playlists = client.get_playlists()
        return jsonify({"status": "success", "playlists": playlists}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching playlists: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@subsonic_bp.route('/playlists/<playlist_id>', methods=['GET'])
def get_playlist(playlist_id):
    try:
        client = get_subsonic_client()
        playlist = client.get_playlist(playlist_id)
        return jsonify({"status": "success", "playlist": playlist}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching playlist {playlist_id}: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@subsonic_bp.route('/star/<track_id>', methods=['POST'])
def star_track(track_id):
    try:
        client = get_subsonic_client()
        client.star_track(track_id, star=True)
        return jsonify({"status": "success", "message": f"Track {track_id} starred successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Error starring track {track_id}: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@subsonic_bp.route('/unstar/<track_id>', methods=['POST'])
def unstar_track(track_id):
    try:
        client = get_subsonic_client()
        client.star_track(track_id, star=False)
        return jsonify({"status": "success", "message": f"Track {track_id} unstarred successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Error unstarring track {track_id}: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@subsonic_bp.route('/stream/<track_id>', methods=['GET'])
def stream_track(track_id):
    try:
        # If buffering is enabled and the file is already cached, stream it directly
        if current_app.config.get("ENABLE_LOCAL_BUFFERING", False):
            cache_path = os.path.join(CACHE_DIR, track_id)
            if os.path.exists(cache_path):
                # Also start buffering the next tracks maybe? Handled by the queue generation.
                return send_file(cache_path, conditional=True)
                
            # If it's not cached yet but buffering is enabled, start buffering it now 
            # while we fall back to proxying the stream
            trigger_buffer_tracks([track_id], current_app)

        client = get_subsonic_client()
        url = client.get_stream_url(track_id)
        
        # Forward range headers for scrubbing/seeking in audio players
        headers = {}
        if "Range" in request.headers:
            headers["Range"] = request.headers["Range"]
            
        req = requests.get(url, headers=headers, stream=True, timeout=15)
        
        response_headers = {}
        # Forward key headers for audio streaming
        for h in ["Content-Type", "Content-Length", "Accept-Ranges", "Content-Range", "Content-Disposition"]:
            if h in req.headers:
                response_headers[h] = req.headers[h]
                
        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                yield chunk
                
        return Response(
            stream_with_context(generate()),
            status=req.status_code,
            headers=response_headers
        )
    except Exception as e:
        current_app.logger.error(f"Error streaming track {track_id}: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@subsonic_bp.route('/stats', methods=['GET'])
def get_stats():
    try:
        # Get count of locally cached tracks and genres
        cached_tracks = Track.query.count()
        analyzed_tracks = Track.query.filter_by(acoustic_status='completed').count()
        pending_tracks = Track.query.filter_by(acoustic_status='pending').count()
        failed_tracks = Track.query.filter_by(acoustic_status='failed').count()
        
        client = get_subsonic_client()
        playlists = client.get_playlists()
        playlist_count = len(playlists)
        
        return jsonify({
            "status": "success",
            "stats": {
                "cached_tracks": cached_tracks,
                "playlists": playlist_count,
                "subsonic_connected": True,
                "analyzed_tracks": analyzed_tracks,
                "pending_tracks": pending_tracks,
                "failed_tracks": failed_tracks
            }
        }), 200
    except Exception as e:
        # Subsonic offline, but sqlite might be online
        current_app.logger.warning(f"Subsonic error fetching stats: {str(e)}")
        try:
            cached_tracks = Track.query.count()
            analyzed_tracks = Track.query.filter_by(acoustic_status='completed').count()
            pending_tracks = Track.query.filter_by(acoustic_status='pending').count()
            failed_tracks = Track.query.filter_by(acoustic_status='failed').count()
            
            return jsonify({
                "status": "partial_success",
                "stats": {
                    "cached_tracks": cached_tracks,
                    "playlists": 0,
                    "subsonic_connected": False,
                    "analyzed_tracks": analyzed_tracks,
                    "pending_tracks": pending_tracks,
                    "failed_tracks": failed_tracks,
                    "error": "Failed to connect to Subsonic server."
                }
            }), 200
        except Exception as db_err:
            current_app.logger.error(f"DB Error: {str(db_err)}")
            return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@subsonic_bp.route('/sync', methods=['POST'])
def sync_subsonic():
    try:
        # Run the flask command in the background
        # Since we are already inside the container, we don't need docker exec
        # We need to pass the current session's config environment variables so the CLI knows who to sync for
        env = os.environ.copy()
        
        # We pass the session credentials to the env so the CLI sync command uses the correct user
        url = session.get('subsonic_url') or current_app.config.get('SUBSONIC_URL', '')
        user = session.get('subsonic_user') or current_app.config.get('SUBSONIC_USER', '')
        password = session.get('subsonic_pass') or current_app.config.get('SUBSONIC_PASS', '')
        
        env['SUBSONIC_URL'] = url
        env['SUBSONIC_USER'] = user
        env['SUBSONIC_PASS'] = password

        subprocess.Popen(
            ["flask", "sync-subsonic"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return jsonify({"status": "success", "message": "Subsonic sync started in the background."}), 200
    except Exception as e:
        current_app.logger.error(f"Failed to start sync: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@subsonic_bp.route('/sync/status', methods=['GET'])
def sync_status():
    is_syncing = os.path.exists("/tmp/orbit_sync.lock")
    try:
        count = Track.query.count()
    except Exception:
        count = 0
    return jsonify({
        "status": "success",
        "is_syncing": is_syncing,
        "track_count": count
    }), 200

