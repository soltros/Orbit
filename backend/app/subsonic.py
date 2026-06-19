import hashlib
import string
import random
import requests

class SubsonicClient:
    def __init__(self, base_url, username, password, client_name="Orbit", version="1.16.1"):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.client_name = client_name
        self.version = version

    def _get_auth_params(self):
        # Generate a random 6-character salt
        salt = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        # token = md5(password + salt)
        token_src = self.password + salt
        token = hashlib.md5(token_src.encode('utf-8')).hexdigest()
        
        return {
            'u': self.username,
            't': token,
            's': salt,
            'v': self.version,
            'c': self.client_name,
            'f': 'json'
        }

    def _make_request(self, endpoint, additional_params=None):
        if not self.base_url or not self.username or not self.password:
            raise Exception("Subsonic Client is not fully configured. Missing URL, username or password.")
            
        url = f"{self.base_url}/rest/{endpoint}"
        params = self._get_auth_params()
        if additional_params:
            params.update(additional_params)
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            subsonic_response = data.get('subsonic-response', {})
            if subsonic_response.get('status') == 'failed':
                error = subsonic_response.get('error', {})
                raise Exception(f"Subsonic Error: {error.get('message', 'Unknown error')} (Code: {error.get('code')})")
            
            return subsonic_response
        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP request to Subsonic failed: {str(e)}")

    def ping(self):
        return self._make_request("ping.view")

    def get_playlists(self):
        res = self._make_request("getPlaylists.view")
        playlists = res.get("playlists", {}).get("playlist", [])
        if isinstance(playlists, dict):
            playlists = [playlists]
        return playlists

    def get_playlist(self, playlist_id):
        res = self._make_request("getPlaylist.view", {"id": playlist_id})
        playlist = res.get("playlist", {})
        # Normalize songs list if only 1 item
        if "entry" in playlist:
            songs = playlist["entry"]
            if isinstance(songs, dict):
                playlist["entry"] = [songs]
        return playlist

    def get_song(self, song_id):
        res = self._make_request("getSong.view", {"id": song_id})
        return res.get("song", {})

    def get_album_list(self, list_type="random", size=20):
        res = self._make_request("getAlbumList2.view", {"type": list_type, "size": size})
        albums = res.get("albumList2", {}).get("album", [])
        if isinstance(albums, dict):
            albums = [albums]
        return albums

    def get_album(self, album_id):
        res = self._make_request("getAlbum.view", {"id": album_id})
        album = res.get("album", {})
        if "song" in album:
            songs = album["song"]
            if isinstance(songs, dict):
                album["song"] = [songs]
        return album

    def star_track(self, track_id, star=True):
        endpoint = "star.view" if star else "unstar.view"
        return self._make_request(endpoint, {"id": track_id})

    def get_stream_url(self, track_id, max_bit_rate=None):
        params = self._get_auth_params()
        params['id'] = track_id
        if max_bit_rate:
            params['maxBitRate'] = max_bit_rate
        # Convert params to query string
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}/rest/stream.view?{query_string}"

    def get_cover_art_url(self, item_id, size=500):
        params = self._get_auth_params()
        params['id'] = item_id
        params['size'] = size
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}/rest/getCoverArt.view?{query_string}"

    def search_songs(self, query=" ", count=500, offset=0):
        res = self._make_request("search3.view", {
            "query": query,
            "songCount": count,
            "songOffset": offset
        })
        search_res = res.get("searchResult3", {})
        songs = search_res.get("song", [])
        if isinstance(songs, dict):
            songs = [songs]
        return songs
