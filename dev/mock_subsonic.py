"""
mock_subsonic.py
================
A fake Navidrome/Subsonic API server for local Orbit development and testing.

It reads whatever audio files you drop into the dev/music/ directory and
serves them through the Subsonic API protocol that Orbit's backend expects.
No real Navidrome install needed.

Runs on http://localhost:4533

Supported endpoints:
  - /rest/ping.view
  - /rest/search3.view
  - /rest/getSong.view
  - /rest/getPlaylists.view
  - /rest/stream.view
  - /rest/star.view
  - /rest/unstar.view
"""

import os
import json
import hashlib
import mimetypes
import uuid
from flask import Flask, request, jsonify, send_file, abort

app = Flask(__name__)

# ----------------------------------------------------------------
# Config
# ----------------------------------------------------------------
MUSIC_DIR = os.environ.get("MOCK_MUSIC_DIR", os.path.join(os.path.dirname(__file__), "music"))
SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav", ".aac", ".wma"}

# In-memory store for starred tracks (resets on restart)
starred_tracks = set()


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------

def scan_music_dir():
    """Walks MUSIC_DIR and returns a list of track dicts with stable IDs."""
    tracks = []
    for root, dirs, files in os.walk(MUSIC_DIR):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, MUSIC_DIR)

            # Try to extract metadata via mutagen if available
            title, artist, album, genre, duration, bpm = extract_metadata(filepath, filename)

            # Stable ID = md5 of relative path so IDs don't change between restarts
            track_id = hashlib.md5(rel_path.encode()).hexdigest()[:16]

            # Derive artist/album from folder structure if mutagen didn't help
            parts = rel_path.replace("\\", "/").split("/")
            if len(parts) >= 3 and artist == "Unknown Artist":
                artist = parts[-3] if len(parts) > 2 else artist
                album = parts[-2] if len(parts) > 1 else album
            elif len(parts) == 2 and artist == "Unknown Artist":
                artist = parts[0]
                album = parts[0]

            tracks.append({
                "id": track_id,
                "title": title,
                "artist": artist,
                "album": album,
                "genre": genre,
                "duration": duration,
                "bpm": bpm,
                "path": rel_path,
                "filepath": filepath,
                "suffix": ext.lstrip(".")
            })
    return tracks


def extract_metadata(filepath, filename):
    """Tries to read ID3/Vorbis tags. Falls back to filename parsing."""
    title = os.path.splitext(filename)[0]
    artist = "Unknown Artist"
    album = "Unknown Album"
    genre = None
    duration = 0
    bpm = None

    try:
        import mutagen
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC
        from mutagen.mp4 import MP4
        from mutagen.oggvorbis import OggVorbis
        from mutagen.id3 import ID3NoHeaderError

        f = mutagen.File(filepath, easy=True)
        if f is not None:
            title = str(f.get("title", [title])[0]) if f.get("title") else title
            artist = str(f.get("artist", [artist])[0]) if f.get("artist") else artist
            album = str(f.get("album", [album])[0]) if f.get("album") else album
            genre = str(f.get("genre", [None])[0]) if f.get("genre") else None
            duration = int(f.info.length) if hasattr(f, "info") and f.info else 0
            bpm_raw = f.get("bpm", [None])[0] if f.get("bpm") else None
            if bpm_raw:
                try:
                    bpm = int(float(str(bpm_raw)))
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass

    return title, artist, album, genre, duration, bpm


def build_subsonic_response(status="ok", extra=None):
    """Wraps a dict in the standard Subsonic JSON envelope."""
    payload = {
        "subsonic-response": {
            "status": status,
            "version": "1.16.1",
            **(extra or {})
        }
    }
    return jsonify(payload)


def auth_ok():
    """Validates Subsonic token auth. Always returns True in dev mode."""
    # In a real server we'd validate u/t/s. In dev we trust everything.
    return True


# Build the track index once on startup, refresh on demand
_tracks_cache = None

def get_tracks():
    global _tracks_cache
    if _tracks_cache is None:
        _tracks_cache = scan_music_dir()
        print(f"[MockSubsonic] Scanned {len(_tracks_cache)} tracks from {MUSIC_DIR}")
    return _tracks_cache


def get_track_by_id(track_id):
    for t in get_tracks():
        if t["id"] == track_id:
            return t
    return None


# ----------------------------------------------------------------
# Subsonic API Endpoints
# ----------------------------------------------------------------

@app.route("/rest/ping.view")
def ping():
    print("[MockSubsonic] PING received")
    return build_subsonic_response()


@app.route("/rest/search3.view")
def search3():
    query = request.args.get("query", "").strip().lower()
    song_count = int(request.args.get("songCount", 500))
    song_offset = int(request.args.get("songOffset", 0))

    all_tracks = get_tracks()

    # If query is empty/whitespace/asterisk, return all tracks
    if not query or query in (" ", "*"):
        matched = all_tracks
    else:
        matched = [
            t for t in all_tracks
            if query in t["title"].lower()
            or query in t["artist"].lower()
            or query in t["album"].lower()
        ]

    paginated = matched[song_offset: song_offset + song_count]

    songs = []
    for t in paginated:
        song = {
            "id": t["id"],
            "title": t["title"],
            "artist": t["artist"],
            "album": t["album"],
            "duration": t["duration"],
            "path": t["path"],
            "suffix": t["suffix"],
            "isDir": False,
            "isVideo": False,
        }
        if t.get("genre"):
            song["genre"] = t["genre"]
        if t.get("bpm"):
            song["bpm"] = t["bpm"]
        songs.append(song)

    print(f"[MockSubsonic] search3 query='{query}' → {len(songs)} tracks (offset={song_offset})")

    return build_subsonic_response(extra={
        "searchResult3": {
            "song": songs,
            "artist": [],
            "album": []
        }
    })


@app.route("/rest/getSong.view")
def get_song():
    song_id = request.args.get("id")
    track = get_track_by_id(song_id)
    if not track:
        return build_subsonic_response(status="failed", extra={
            "error": {"code": 70, "message": f"Song {song_id} not found"}
        })

    return build_subsonic_response(extra={
        "song": {
            "id": track["id"],
            "title": track["title"],
            "artist": track["artist"],
            "album": track["album"],
            "duration": track["duration"],
            "path": track["path"],
            "suffix": track["suffix"],
        }
    })


@app.route("/rest/getPlaylists.view")
def get_playlists():
    # Return an empty playlist list — we don't mock playlists
    return build_subsonic_response(extra={"playlists": {"playlist": []}})


@app.route("/rest/getPlaylist.view")
def get_playlist():
    return build_subsonic_response(extra={"playlist": {"entry": []}})


@app.route("/rest/stream.view")
def stream():
    song_id = request.args.get("id")
    track = get_track_by_id(song_id)
    if not track:
        abort(404)

    filepath = track["filepath"]
    if not os.path.exists(filepath):
        abort(404)

    mime = mimetypes.guess_type(filepath)[0] or "audio/mpeg"
    print(f"[MockSubsonic] Streaming: {track['title']} from {filepath}")
    return send_file(filepath, mimetype=mime, conditional=True)


@app.route("/rest/star.view")
def star():
    song_id = request.args.get("id")
    if song_id:
        starred_tracks.add(song_id)
        print(f"[MockSubsonic] Starred track {song_id}")
    return build_subsonic_response()


@app.route("/rest/unstar.view")
def unstar():
    song_id = request.args.get("id")
    if song_id:
        starred_tracks.discard(song_id)
        print(f"[MockSubsonic] Unstarred track {song_id}")
    return build_subsonic_response()


@app.route("/refresh-index")
def refresh_index():
    """Dev-only: Force a rescan of the music directory."""
    global _tracks_cache
    _tracks_cache = None
    tracks = get_tracks()
    return jsonify({"status": "ok", "track_count": len(tracks)})


@app.route("/list-tracks")
def list_tracks():
    """Dev-only: View all indexed tracks as JSON."""
    return jsonify(get_tracks())


# ----------------------------------------------------------------
# Run
# ----------------------------------------------------------------
if __name__ == "__main__":
    print(f"[MockSubsonic] Starting mock Navidrome server")
    print(f"[MockSubsonic] Music directory: {MUSIC_DIR}")
    print(f"[MockSubsonic] Listening on http://0.0.0.0:4533")
    os.makedirs(MUSIC_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=4533, debug=True)
