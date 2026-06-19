from flask import Blueprint, current_app, jsonify, request
import requests
import urllib.parse

lastfm_bp = Blueprint('lastfm', __name__, url_prefix='/api/lastfm')

@lastfm_bp.route('/artist', methods=['GET'])
def get_artist_info():
    artist_name = request.args.get('name')
    if not artist_name:
        return jsonify({"error": "Artist name is required"}), 400

    api_key = current_app.config.get('LASTFM_API_KEY')
    if not api_key:
        return jsonify({"error": "LastFM API key not configured"}), 404

    try:
        encoded_name = urllib.parse.quote(artist_name)
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={encoded_name}&api_key={api_key}&format=json"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if 'error' in data:
            return jsonify({"error": data['message']}), 404
            
        artist_data = data.get('artist', {})
        
        # Last.fm provides a list of images. Get the largest one.
        images = artist_data.get('image', [])
        image_url = None
        for img in reversed(images):
            if img.get('#text'):
                image_url = img.get('#text')
                break
                
        # Extract bio
        bio = artist_data.get('bio', {}).get('summary', '')
        # Clean up lastfm html link
        if '<a href' in bio:
            bio = bio.split('<a href')[0].strip()
            
        return jsonify({
            "name": artist_data.get('name'),
            "image": image_url,
            "bio": bio,
            "tags": [t.get('name') for t in artist_data.get('tags', {}).get('tag', [])],
            "similar": [a.get('name') for a in artist_data.get('similar', {}).get('artist', [])]
        })
        
    except Exception as e:
        current_app.logger.error(f"LastFM API error: {str(e)}")
        return jsonify({"error": "Failed to fetch artist info from LastFM"}), 500
