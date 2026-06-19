import os
import json
from flask import Blueprint, jsonify, request

playlist_bp = Blueprint('playlist', __name__, url_prefix='/api/playlists')

@playlist_bp.route('/generate-smart', methods=['POST'])
def generate_smart_playlist():
    """
    Procedurally generates a Navidrome Smart Playlist (.nsp) JSON file 
    and saves it to the /music directory.
    """
    data = request.get_json() or {}
    name = data.get('name', 'Orbit Smart Playlist')
    comment = data.get('comment', 'Generated automatically by Orbit')
    min_bpm = data.get('min_bpm')
    max_bpm = data.get('max_bpm')
    genre = data.get('genre')
    limit = min(int(data.get('limit', 100)), 500)
    
    all_rules = []
    
    # Add BPM filters if present
    if min_bpm is not None:
        all_rules.append({"gt": {"bpm": int(min_bpm) - 1}})
    if max_bpm is not None:
        all_rules.append({"lt": {"bpm": int(max_bpm) + 1}})
        
    # Add Genre filter if present
    if genre:
        all_rules.append({"contains": {"genre": genre}})
        
    # Build the NSP content structure
    nsp_content = {
        "name": name,
        "comment": comment,
        "all": all_rules,
        "sort": "+random",
        "limit": limit
    }
    
    # Clean the filename
    clean_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
    filename = clean_name.lower().replace(' ', '_') + ".nsp"
    file_path = os.path.join("/music", filename)
    
    try:
        # Write file with pretty printing
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(nsp_content, f, indent=2)
            
        return jsonify({
            "status": "success",
            "message": f"Smart playlist file generated successfully.",
            "file_path": file_path,
            "filename": filename,
            "playlist_name": name
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Failed to save NSP file to music folder: {str(e)}"
        }), 500
