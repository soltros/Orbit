import requests
import logging

logger = logging.getLogger("orbit-listenbrainz")

def get_artist_mbid(artist_name):
    """
    Looks up the MusicBrainz Identifier (MBID) for a given artist name
    using the public MusicBrainz XML/JSON Web Service.
    """
    if not artist_name:
        return None
        
    url = "https://musicbrainz.org/ws/2/artist/"
    params = {
        "query": f"artist:{artist_name}",
        "fmt": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "OrbitRadio/1.0.0 ( https://github.com/derrik/Orbit )"
    }
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        artists = data.get("artists", [])
        if artists:
            mbid = artists[0].get("id")
            logger.info(f"MusicBrainz match for '{artist_name}': MBID {mbid}")
            return mbid
    except Exception as e:
        logger.error(f"MusicBrainz lookup failed for '{artist_name}': {str(e)}")
        
    return None

def get_similar_artists(artist_name):
    """
    Fetches a list of similar artists from ListenBrainz labs API based on MBID.
    Returns list of artist names.
    """
    mbid = get_artist_mbid(artist_name)
    if not mbid:
        return []
        
    # ListenBrainz Labs similarity API
    url = "https://labs.api.listenbrainz.org/similar-artists"
    params = {
        "artist_mbid": mbid
    }
    
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        similar_artists = []
        # ListenBrainz returns a list of similar artists
        # Structure is usually: {"similar_artists": [{"artist_name": "...", "mbid": "..."}, ...]}
        for entry in data.get("similar_artists", []):
            name = entry.get("artist_name")
            if name:
                similar_artists.append(name)
                
        logger.info(f"ListenBrainz returned {len(similar_artists)} similar artists for '{artist_name}'")
        return similar_artists
    except Exception as e:
        logger.error(f"ListenBrainz similar artists fetch failed for '{artist_name}' (MBID: {mbid}): {str(e)}")
        
    return []
