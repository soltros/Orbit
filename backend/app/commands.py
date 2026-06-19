import os
import json
import click
from flask.cli import with_appcontext
from app import db
from app.models import Track, Genre
from app.routes.subsonic_routes import get_subsonic_client

def get_filename_or_suffix(path, parts_count=3):
    """
    Extracts the last parts_count components of a file path.
    Used to match local Mutagen paths with Subsonic paths.
    """
    if not path:
        return ""
    normalized = path.replace('\\', '/').strip('/')
    parts = normalized.split('/')
    return '/'.join(parts[-parts_count:]).lower()

@click.command('sync-subsonic')
@click.option('--limit', default=1000000, help='Maximum number of songs to sync.')
@with_appcontext
def sync_subsonic_command(limit):
    """Fetch all tracks from Subsonic/Navidrome and populate the local cache database."""
    click.echo("Starting Subsonic synchronization...")
    
    lock_file = "/tmp/orbit_sync.lock"
    with open(lock_file, "w") as f:
        f.write("syncing")
        
    try:
        client = get_subsonic_client()
    except Exception as e:
        click.echo(f"Error initializing Subsonic client: {str(e)}")
        return

    offset = 0
    batch_size = 500
    total_synced = 0
    
    # We will try a few wildcard/all queries in order if the first returns nothing
    search_queries = [" ", "*", ""]
    
    for query in search_queries:
        try:
            click.echo(f"Attempting to query Subsonic with query='{query}'...")
            test_songs = client.search_songs(query=query, count=5, offset=0)
            if test_songs:
                # Found a working query, let's use it
                click.echo(f"Query '{query}' returned songs. Proceeding with sync...")
                while total_synced < limit:
                    batch = client.search_songs(query=query, count=batch_size, offset=offset)
                    if not batch:
                        break
                    
                    for song_data in batch:
                        track_id = song_data.get('id')
                        if not track_id:
                            continue
                            
                        # Extract basic info
                        title = song_data.get('title', 'Unknown Title')
                        artist = song_data.get('artist', 'Unknown Artist')
                        album = song_data.get('album', 'Unknown Album')
                        duration = song_data.get('duration', 0)
                        path = song_data.get('path')
                        
                        # Find or create track
                        track = Track.query.get(track_id)
                        if not track:
                            track = Track(id=track_id)
                            db.session.add(track)
                            
                        track.title = title
                        track.artist = artist
                        track.album = album
                        track.duration = duration
                        track.path = path
                        
                        # Handle genres
                        genre_name = song_data.get('genre')
                        if genre_name:
                            genre = Genre.query.filter_by(name=genre_name).first()
                            if not genre:
                                genre = Genre(name=genre_name)
                                db.session.add(genre)
                            if genre not in track.genres:
                                track.genres.append(genre)
                                
                    db.session.commit()
                    total_synced += len(batch)
                    click.echo(f"Synced {total_synced} songs...")
                    
                    if len(batch) < batch_size:
                        break
                    offset += batch_size
                break
        except Exception as e:
            click.echo(f"Query '{query}' failed: {str(e)}")
            continue
            
    click.echo(f"Sync complete. Total tracks in database: {Track.query.count()}")
    
    if os.path.exists(lock_file):
        os.remove(lock_file)

@click.command('ingest-mutagen')
@click.argument('json_path')
@with_appcontext
def ingest_mutagen_command(json_path):
    """Ingest Mutagen JSON metadata to enrich local tracks with BPM and custom tags."""
    if not os.path.exists(json_path):
        click.echo(f"Error: JSON file not found at {json_path}")
        return
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            mutagen_data = json.load(f)
    except Exception as e:
        click.echo(f"Error reading JSON: {str(e)}")
        return
        
    if not isinstance(mutagen_data, list):
        click.echo("Error: Mutagen JSON must be a list of track metadata objects.")
        return
        
    click.echo(f"Loaded {len(mutagen_data)} Mutagen metadata entries. Correlating with database...")
    
    # Load all tracks from database to perform in-memory path matching for performance
    db_tracks = Track.query.all()
    # Create lookup map using trailing path components (e.g. Artist/Album/Song.mp3)
    track_map = {}
    for track in db_tracks:
        if track.path:
            # Try 3 parts matching first
            key3 = get_filename_or_suffix(track.path, 3)
            if key3:
                track_map[key3] = track
            # Also register filename only as fallback
            key1 = get_filename_or_suffix(track.path, 1)
            if key1 and key1 not in track_map:
                track_map[key1] = track
                
    updated_count = 0
    
    for entry in mutagen_data:
        path = entry.get('path')
        if not path:
            continue
            
        bpm = entry.get('bpm')
        genres = entry.get('genres', [])
        # If single string genre
        if isinstance(genres, str):
            genres = [genres]
        custom_tags = entry.get('custom_tags', {})
        
        # Try matching
        matched_track = None
        
        # 1. Try matching using trailing 3 parts
        key3 = get_filename_or_suffix(path, 3)
        if key3 in track_map:
            matched_track = track_map[key3]
        else:
            # 2. Fall back to filename only
            key1 = get_filename_or_suffix(path, 1)
            if key1 in track_map:
                matched_track = track_map[key1]
                
        if matched_track:
            # Found a match, update BPM and custom tags
            if bpm is not None:
                try:
                    matched_track.bpm = int(bpm)
                except (ValueError, TypeError):
                    pass
            
            if custom_tags:
                # Merge custom tags if existing
                existing_tags = matched_track.custom_tags or {}
                existing_tags.update(custom_tags)
                matched_track.custom_tags = existing_tags
                
            # Add any additional deep genres
            for g_name in genres:
                if not g_name:
                    continue
                genre = Genre.query.filter_by(name=g_name).first()
                if not genre:
                    genre = Genre(name=g_name)
                    db.session.add(genre)
                if genre not in matched_track.genres:
                    matched_track.genres.append(genre)
                    
            updated_count += 1
            if updated_count % 100 == 0:
                db.session.commit()
                click.echo(f"Correlated and updated {updated_count} tracks...")
                
    db.session.commit()
    click.echo(f"Ingestion complete. Successfully enriched {updated_count} out of {len(mutagen_data)} tracks in database.")

def register_commands(app):
    app.cli.add_command(sync_subsonic_command)
    app.cli.add_command(ingest_mutagen_command)
