import requests
from flask import Blueprint, current_app, jsonify, request, Response, stream_with_context
from app.subsonic import SubsonicClient
from app.models import Track

subsonic_bp = Blueprint('subsonic', __name__, url_prefix='/api/subsonic')

def get_subsonic_client():
    return SubsonicClient(
        base_url=current_app.config['SUBSONIC_URL'],
        username=current_app.config['SUBSONIC_USER'],
        password=current_app.config['SUBSONIC_PASS']
    )

@subsonic_bp.route('/ping', methods=['GET'])
def ping():
    try:
        client = get_subsonic_client()
        client.ping()
        return jsonify({"status": "success", "message": "Successfully connected to Subsonic/Navidrome server."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@subsonic_bp.route('/playlists', methods=['GET'])
def get_playlists():
    try:
        client = get_subsonic_client()
        playlists = client.get_playlists()
        return jsonify({"status": "success", "playlists": playlists}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@subsonic_bp.route('/playlists/<playlist_id>', methods=['GET'])
def get_playlist(playlist_id):
    try:
        client = get_subsonic_client()
        playlist = client.get_playlist(playlist_id)
        return jsonify({"status": "success", "playlist": playlist}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@subsonic_bp.route('/star/<track_id>', methods=['POST'])
def star_track(track_id):
    try:
        client = get_subsonic_client()
        client.star_track(track_id, star=True)
        return jsonify({"status": "success", "message": f"Track {track_id} starred successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@subsonic_bp.route('/unstar/<track_id>', methods=['POST'])
def unstar_track(track_id):
    try:
        client = get_subsonic_client()
        client.star_track(track_id, star=False)
        return jsonify({"status": "success", "message": f"Track {track_id} unstarred successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@subsonic_bp.route('/stream/<track_id>', methods=['GET'])
def stream_track(track_id):
    try:
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
        return jsonify({"status": "error", "message": str(e)}), 500

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
                    "error": str(e)
                }
            }), 200
        except Exception as db_err:
            return jsonify({"status": "error", "message": f"DB Error: {str(db_err)}, Subsonic Error: {str(e)}"}), 500
