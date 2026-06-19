import os
import json
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

playlist_bp = Blueprint('playlist', __name__, url_prefix='/api/playlists')

@playlist_bp.route('/generate-smart', methods=['POST'])
def generate_smart_playlist():
    """
    Procedurally generates a Navidrome Smart Playlist (.nsp) JSON file 
    and saves it to the /music directory.
    """
    data = request.get_json() or {}
    name = str(data.get('name', 'Orbit Smart Playlist'))
    comment = str(data.get('comment', 'Generated automatically by Orbit'))
    min_bpm = data.get('min_bpm')
    max_bpm = data.get('max_bpm')
    genre = data.get('genre')
    
    try:
        limit = min(int(data.get('limit', 100)), 500)
    except (ValueError, TypeError):
        limit = 100
    
    all_rules = []
    
    # Add BPM filters if present
    if min_bpm is not None:
        try:
            all_rules.append({"gt": {"bpm": int(min_bpm) - 1}})
        except (ValueError, TypeError):
            pass
            
    if max_bpm is not None:
        try:
            all_rules.append({"lt": {"bpm": int(max_bpm) + 1}})
        except (ValueError, TypeError):
            pass
        
    # Add Genre filter if present
    if genre:
        all_rules.append({"contains": {"genre": str(genre)}})
        
    # Build the NSP content structure
    nsp_content = {
        "name": name,
        "comment": comment,
        "all": all_rules,
        "sort": "+random",
        "limit": limit
    }
    
    # Clean the filename using secure_filename and restrict to alphanumeric/spaces/underscores
    clean_name = secure_filename("".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip())
    if not clean_name:
        clean_name = "orbit_smart_playlist"
    filename = clean_name.lower().replace(' ', '_') + ".nsp"
    
    # Ensure it's inside /music and no traversal
    base_dir = "/music"
    file_path = os.path.abspath(os.path.join(base_dir, filename))
    if not file_path.startswith(base_dir):
        return jsonify({
            "status": "error",
            "message": "Invalid filename path."
        }), 400
    
    try:
        # Write file with pretty printing
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(nsp_content, f, indent=2)
            
        return jsonify({
            "status": "success",
            "message": "Smart playlist file generated successfully.",
            "file_path": file_path,
            "filename": filename,
            "playlist_name": name
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": "Failed to save NSP file to music folder."
        }), 500
