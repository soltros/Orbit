from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import func
from app import db
from app.models import Track, Genre, InteractionHistory, QueueItem
from app.routes.queue_routes import get_or_create_default_user, get_effective_mode

library_bp = Blueprint('library', __name__, url_prefix='/api/library')


@library_bp.route('/artists', methods=['GET'])
def get_artists():
    """
    Returns a list of all artists in the local track cache, sorted
    alphabetically, with track counts and genre tags per artist.

    Optional query params:
      ?q=<search>    Filter artists by name (case-insensitive)
      ?limit=<int>   Max artists to return (default 500)
    """
    search = request.args.get('q', '').strip().lower()
    limit = min(int(request.args.get('limit', 500)), 1000)

    try:
        # Aggregate track counts per artist
        query = (
            db.session.query(
                Track.artist,
                func.count(Track.id).label('track_count')
            )
            .group_by(Track.artist)
        )

        if search:
            query = query.filter(func.lower(Track.artist).contains(search))

        results = query.order_by(func.lower(Track.artist)).limit(limit).all()

        artists = []
        for row in results:
            artists.append({
                "name": row.artist,
                "track_count": row.track_count,
            })

        return jsonify({"status": "success", "artists": artists, "total": len(artists)}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching artist list: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500


@library_bp.route('/artists/<path:artist_name>/tracks', methods=['GET'])
def get_artist_tracks(artist_name):
    """
    Returns all tracks for a specific artist, sorted by album then title.
    """
    try:
        tracks = (
            Track.query
            .filter(func.lower(Track.artist) == artist_name.lower())
            .order_by(Track.album, Track.title)
            .all()
        )

        if not tracks:
            return jsonify({"status": "error", "message": "Artist not found."}), 404

        return jsonify({
            "status": "success",
            "artist": tracks[0].artist,  # canonical casing from DB
            "tracks": [t.to_dict() for t in tracks]
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching tracks for artist '{artist_name}': {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500


@library_bp.route('/seed', methods=['POST'])
def seed_station():
    """
    Seeds the recommendation engine with a specific track or a random track
    from a given artist, then generates an initial queue.

    Body (JSON):
      { "track_id": "abc123" }          — seed from a specific track
      { "artist": "Gin Blossoms" }      — seed from a random track by that artist
    """
    data = request.get_json(silent=True) or {}
    track_id = data.get('track_id')
    artist_name = data.get('artist')

    try:
        user = get_or_create_default_user()

        seed_track = None

        if track_id:
            seed_track = Track.query.get(track_id)
            if not seed_track:
                return jsonify({"status": "error", "message": "Track not found."}), 404

        elif artist_name:
            # Pick a random track from this artist
            seed_track = (
                Track.query
                .filter(func.lower(Track.artist) == artist_name.lower())
                .order_by(db.func.random())
                .first()
            )
            if not seed_track:
                return jsonify({"status": "error", "message": f"No tracks found for artist '{artist_name}'."}), 404

        else:
            return jsonify({"status": "error", "message": "Provide either 'track_id' or 'artist'."}), 400

        # Clear any existing queue so the seed starts fresh
        QueueItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        
        # Dump the temp buffer since the old station was abandoned
        from app.routes.subsonic_routes import clear_local_buffer
        clear_local_buffer()

        # Add the seed track as the first item and mark it playing immediately
        next_position = 1
        seed_item = QueueItem(
            user_id=user.id,
            track_id=seed_track.id,
            why_queued=f"Seeded from {seed_track.artist}.",
            position=next_position,
            status='playing'
        )
        db.session.add(seed_item)

        # Log it as a play so the recommendation engine uses it as the anchor
        history_entry = InteractionHistory(
            user_id=user.id,
            track_id=seed_track.id,
            action='play'
        )
        db.session.add(history_entry)
        db.session.commit()

        # Now generate recommendations based on this seed
        rec_mode = get_effective_mode(user)

        recommendations = []
        if rec_mode == "local":
            from app.recommendations import get_hybrid_recommendations
            recommendations = get_hybrid_recommendations(user, count=5)
        else:
            from app.routes.queue_routes import get_candidate_tracks
            from app.llm import LLMClient
            candidates = get_candidate_tracks(user, count=60)
            if candidates:
                llm = LLMClient()
                user_profile = user.llm_preferences.get(
                    "generated_profile",
                    "A general music lover who enjoys diverse sounds."
                )
                recommendations = llm.generate_recommendations(
                    user_profile=user_profile,
                    listening_history=[{
                        "title": seed_track.title,
                        "artist": seed_track.artist,
                        "action": "play",
                        "timestamp": history_entry.timestamp.isoformat()
                    }],
                    candidate_tracks=candidates,
                    count=5
                )

        # Insert recommended tracks after the seed
        added_items = []
        for idx, rec in enumerate(recommendations):
            rec_track_id = rec.get("track_id")
            why_queued = rec.get("why_queued", "")
            rec_track = Track.query.get(rec_track_id)
            if not rec_track:
                continue
            q_item = QueueItem(
                user_id=user.id,
                track_id=rec_track_id,
                why_queued=why_queued,
                position=next_position + 1 + idx,
                status='pending'
            )
            db.session.add(q_item)
            added_items.append(q_item)

        db.session.commit()

        return jsonify({
            "status": "success",
            "seed_track": seed_track.to_dict(),
            "seed_queue_item": seed_item.to_dict(),
            "queued_count": len(added_items),
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding station: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500
