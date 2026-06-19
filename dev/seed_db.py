"""
seed_db.py
==========
Directly seeds the Orbit SQLite database with tracks from dev/music/
WITHOUT needing Subsonic sync to work first.

This is useful for testing the acoustic worker, local recommendation engine,
and the LLM queue generation without wiring everything up together first.

Usage:
  python dev/seed_db.py

It will:
  1. Scan dev/music/ for audio files
  2. Compute stable track IDs (same algo as mock_subsonic.py)
  3. Insert them into the orbit database
  4. Mark acoustic_status = 'pending' so the worker picks them up
"""

import os
import sys
import hashlib

# Add the backend to the Python path so we can import the Flask app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Point the database to the dev location
DEV_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "orbit_dev.db")
os.makedirs(os.path.dirname(DEV_DB_PATH), exist_ok=True)
os.environ.setdefault("DATABASE_PATH", DEV_DB_PATH)

# Use safe dummy values for Subsonic (not needed for seeding)
os.environ.setdefault("SUBSONIC_URL", "http://localhost:4533")
os.environ.setdefault("SUBSONIC_USER", "dev")
os.environ.setdefault("SUBSONIC_PASS", "dev")

MUSIC_DIR = os.path.join(os.path.dirname(__file__), "music")
SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav", ".aac", ".wma"}


def extract_metadata(filepath, filename):
    """Reads audio tags; falls back to filename/folder for title/artist/album."""
    title = os.path.splitext(filename)[0]
    artist = "Unknown Artist"
    album = "Unknown Album"
    genre = None
    duration = 0
    bpm = None

    try:
        import mutagen
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
    except Exception as e:
        print(f"  [warn] mutagen failed on {filename}: {e}")

    return title, artist, album, genre, duration, bpm


def scan_music_dir(music_dir):
    tracks = []
    for root, dirs, files in os.walk(music_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, music_dir)
            track_id = hashlib.md5(rel_path.encode()).hexdigest()[:16]

            title, artist, album, genre, duration, bpm = extract_metadata(filepath, filename)

            # Folder-based artist/album fallback
            parts = rel_path.replace("\\", "/").split("/")
            if len(parts) >= 3 and artist == "Unknown Artist":
                artist = parts[-3]
                album = parts[-2]
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
            })
    return tracks


def main():
    print("=" * 55)
    print("  Orbit Dev Database Seeder")
    print("=" * 55)
    print(f"  Music dir  : {MUSIC_DIR}")
    print(f"  Database   : {DEV_DB_PATH}")
    print()

    if not os.path.exists(MUSIC_DIR):
        print(f"  [error] Music directory not found: {MUSIC_DIR}")
        print("  Create dev/music/ and drop some audio files in there.")
        sys.exit(1)

    # Scan for files
    print("  Scanning music directory...")
    tracks = scan_music_dir(MUSIC_DIR)
    if not tracks:
        print("  [warn] No audio files found in dev/music/")
        print("  Drop some .mp3 / .flac / .ogg files into dev/music/ and re-run.")
        sys.exit(0)

    print(f"  Found {len(tracks)} audio file(s).")
    print()

    # Import Flask app with correct DB path
    from app import create_app, db
    from app.models import Track, Genre

    app = create_app()

    with app.app_context():
        inserted = 0
        updated = 0

        for t in tracks:
            existing = Track.query.get(t["id"])
            if existing:
                # Update metadata but don't reset acoustic status
                existing.title = t["title"]
                existing.artist = t["artist"]
                existing.album = t["album"]
                existing.duration = t["duration"]
                existing.path = t["path"]
                if t["bpm"] and not existing.bpm:
                    existing.bpm = t["bpm"]
                updated += 1
                print(f"  [update] {t['artist']} — {t['title']}")
            else:
                track = Track(
                    id=t["id"],
                    title=t["title"],
                    artist=t["artist"],
                    album=t["album"],
                    duration=t["duration"],
                    path=t["path"],
                    bpm=t["bpm"],
                    acoustic_status="pending",
                )
                db.session.add(track)
                inserted += 1
                print(f"  [insert] {t['artist']} — {t['title']}")

            # Handle genre
            if t.get("genre"):
                genre = Genre.query.filter_by(name=t["genre"]).first()
                if not genre:
                    genre = Genre(name=t["genre"])
                    db.session.add(genre)

                track_obj = existing if existing else Track.query.get(t["id"])
                db.session.flush()  # So we can reference the newly added track
                if track_obj and genre not in track_obj.genres:
                    track_obj.genres.append(genre)

        db.session.commit()
        print()
        print(f"  Done. {inserted} inserted, {updated} updated.")
        print(f"  Total tracks in DB: {Track.query.count()}")
        print()
        print("  Next steps:")
        print("    1. Start docker compose dev stack:  docker compose -f docker-compose.dev.yml up")
        print("    2. Open http://localhost:5173 in your browser")
        print("    3. The acoustic worker will start analyzing tracks automatically")


if __name__ == "__main__":
    main()
