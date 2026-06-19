import random
from datetime import datetime, timedelta
from flask import Blueprint, current_app, jsonify, request
from app import db
from app.models import Track, Genre, UserProfile, QueueItem, InteractionHistory
from app.llm import LLMClient
from app.routes.subsonic_routes import get_subsonic_client
from app.rate_limiter import is_rate_limited

queue_bp = Blueprint('queue', __name__, url_prefix='/api/queue')

def get_or_create_default_user():
    """Helper to ensure a default user exists for this single-user system."""
    user = UserProfile.query.filter_by(username="default").first()
    if not user:
        user = UserProfile(username="default")
        db.session.add(user)
        db.session.commit()
    return user

def get_candidate_tracks(user, count=50):
    """
    Selects a pool of candidate tracks from the database to present to the LLM.
    Mixes:
    - 50% tracks from user's preferred genres (based on history and likes)
    - 30% random tracks for serendipitous discovery
    - 20% tracks with similar BPM range to recently enjoyed songs
    """
    # 1. Gather recently played or liked track IDs to exclude
    recent_history = InteractionHistory.query.filter_by(user_id=user.id)\
        .filter(InteractionHistory.timestamp > datetime.utcnow() - timedelta(hours=6))\
        .all()
    exclude_ids = {h.track_id for h in recent_history}
    
    # Also exclude songs currently in the active upcoming queue
    active_queue = QueueItem.query.filter_by(user_id=user.id)\
        .filter(QueueItem.status.in_(['pending', 'playing']))\
        .all()
    for item in active_queue:
        exclude_ids.add(item.track_id)
        
    # Get all tracks in local DB
    all_tracks_query = Track.query.filter(~Track.id.in_(exclude_ids)) if exclude_ids else Track.query
    
    # If db is empty, return empty list
    total_available = all_tracks_query.count()
    if total_available == 0:
        return []
        
    # 2. Extract preferred genres from history
    liked_history = InteractionHistory.query.filter_by(user_id=user.id, action='like').all()
    preferred_genres = set()
    for h in liked_history:
        if h.track:
            for g in h.track.genres:
                preferred_genres.add(g.name)
                
    # If no preferences, pick top genres in DB
    if not preferred_genres:
        top_genres = Genre.query.limit(5).all()
        preferred_genres = {g.name for g in top_genres}

    # 3. Pull candidates from preferred genres
    genre_candidates = []
    if preferred_genres:
        genre_candidates = Track.query.join(Track.genres).filter(
            Genre.name.in_(preferred_genres)
        ).filter(~Track.id.in_(exclude_ids) if exclude_ids else True).limit(30).all()

    # 4. Pull some random candidates
    random_candidates = []
    needed_random = count - len(genre_candidates)
    if needed_random > 0:
        random_candidates = all_tracks_query.order_by(db.func.random()).limit(needed_random).all()

    # Merge candidates and remove duplicates
    candidates = list({t.id: t for t in (genre_candidates + random_candidates)}.values())
    
    # Shuffle so LLM doesn't just see ordered list
    random.shuffle(candidates)
    
    return candidates[:count]

@queue_bp.route('/', methods=['GET'])
def get_queue():
    try:
        user = get_or_create_default_user()
        queue_items = QueueItem.query.filter_by(user_id=user.id, status='pending')\
            .order_by(QueueItem.position.asc()).all()
        
        current_playing = QueueItem.query.filter_by(user_id=user.id, status='playing')\
            .order_by(QueueItem.created_at.desc()).first()
            
        res = {
            "current": current_playing.to_dict() if current_playing else None,
            "upcoming": [item.to_dict() for item in queue_items]
        }
        return jsonify({"status": "success", "queue": res}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching queue: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@queue_bp.route('/generate', methods=['POST'])
def generate_queue():
    try:
        user = get_or_create_default_user()
        
        # Get request options
        req_data = request.get_json() or {}
        try:
            requested_count = min(int(req_data.get('count', 5)), 10)
        except (ValueError, TypeError):
            requested_count = 5
        
        # Check current queue size
        existing_pending = QueueItem.query.filter_by(user_id=user.id, status='pending').count()
        if existing_pending >= 5:
            return jsonify({
                "status": "success",
                "message": "Queue already has sufficient pending tracks.",
                "count": 0
            }), 200
            
        # Determine recommendation mode
        rec_mode = user.llm_preferences.get("recommendation_mode", current_app.config.get("RECOMMENDATION_MODE", "llm"))
        
        recommendations = []
        if rec_mode == "local":
            # Local-First Hybrid recommendation logic
            from app.recommendations import get_hybrid_recommendations
            recommendations = get_hybrid_recommendations(user, count=requested_count)
        else:
            # Rate limiting for LLM queries
            if is_rate_limited(max_requests=10, period=300):
                return jsonify({
                    "status": "error",
                    "message": "Rate limit exceeded. Too many requests to the LLM API. Please wait a few minutes."
                }), 429
                
            # Get candidates
            candidates = get_candidate_tracks(user, count=60)
            if not candidates:
                return jsonify({
                    "status": "error",
                    "message": "No candidate tracks found. Sync Subsonic and/or ingest Mutagen metadata first."
                }), 400
                
            # Build LLM inputs
            llm = LLMClient()
            user_profile = user.llm_preferences.get("generated_profile", "A general music lover who enjoys diverse sounds.")
            
            # Get recent interaction history (last 15 interactions)
            history_items = InteractionHistory.query.filter_by(user_id=user.id)\
                .order_by(InteractionHistory.timestamp.desc()).limit(15).all()
                
            history_summary = []
            for h in history_items:
                history_summary.append({
                    "title": h.track.title if h.track else "Unknown",
                    "artist": h.track.artist if h.track else "Unknown",
                    "action": h.action,
                    "timestamp": h.timestamp.isoformat()
                })
                
            # Call LLM recommendations
            recommendations = llm.generate_recommendations(
                user_profile=user_profile,
                listening_history=history_summary,
                candidate_tracks=candidates,
                count=requested_count
            )
        
        # Insert recommended tracks into queue
        start_position = existing_pending + 1
        added_items = []
        
        for idx, rec in enumerate(recommendations):
            track_id = rec.get("track_id")
            why_queued = rec.get("why_queued")
            
            # Double check track exists
            track = Track.query.get(track_id)
            if not track:
                continue
                
            q_item = QueueItem(
                user_id=user.id,
                track_id=track_id,
                why_queued=why_queued,
                position=start_position + idx,
                status='pending'
            )
            db.session.add(q_item)
            added_items.append(q_item)
            
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Successfully added {len(added_items)} recommendations to the queue.",
            "recommendations": [item.to_dict() for item in added_items]
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating queue: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@queue_bp.route('/play/<int:queue_item_id>', methods=['POST'])
def play_track(queue_item_id):
    try:
        user = get_or_create_default_user()
        
        # Mark currently playing tracks as played
        current_playing = QueueItem.query.filter_by(user_id=user.id, status='playing').all()
        for item in current_playing:
            item.status = 'played'
            item.played_at = datetime.utcnow()
            
        # Set this queue item as playing
        q_item = QueueItem.query.get(queue_item_id)
        if not q_item or q_item.user_id != user.id:
            return jsonify({"status": "error", "message": "Queue item not found"}), 404
            
        q_item.status = 'playing'
        
        # Log to interaction history
        history = InteractionHistory(
            user_id=user.id,
            track_id=q_item.track_id,
            action='play'
        )
        db.session.add(history)
        
        # Shift down positions of remaining pending queue items
        pending_items = QueueItem.query.filter_by(user_id=user.id, status='pending')\
            .order_by(QueueItem.position.asc()).all()
        for idx, item in enumerate(pending_items):
            item.position = idx + 1
            
        db.session.commit()
        
        return jsonify({"status": "success", "playing": q_item.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error playing track: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@queue_bp.route('/skip/<int:queue_item_id>', methods=['POST'])
def skip_track(queue_item_id):
    try:
        user = get_or_create_default_user()
        
        q_item = QueueItem.query.get(queue_item_id)
        if not q_item or q_item.user_id != user.id:
            return jsonify({"status": "error", "message": "Queue item not found"}), 404
            
        q_item.status = 'skipped'
        q_item.skipped_at = datetime.utcnow()
        
        # Log to interaction history
        history = InteractionHistory(
            user_id=user.id,
            track_id=q_item.track_id,
            action='skip'
        )
        db.session.add(history)
        
        # Perform Course Correction:
        # Since user skipped, we clear remaining pending items, and trigger an instant recalculation 
        # so the LLM adjusts the next batch immediately to respect the skip.
        QueueItem.query.filter_by(user_id=user.id, status='pending').delete()
        db.session.commit()
        
        # Trigger an automatic replenishment (e.g. 5 tracks)
        # Note: in a production setting we do this asynchronously or return the signal to the frontend
        # so it pulls a fresh queue. Let's run it inline for simplicity and reliability.
        return generate_queue()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error skipping track: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@queue_bp.route('/like/<string:track_id>', methods=['POST'])
def like_track(track_id):
    try:
        user = get_or_create_default_user()
        
        # Add to history
        history = InteractionHistory(
            user_id=user.id,
            track_id=track_id,
            action='like'
        )
        db.session.add(history)
        
        # Also proxy to Subsonic
        try:
            client = get_subsonic_client()
            client.star_track(track_id, star=True)
            subsonic_synced = True
        except Exception as e:
            current_app.logger.warning(f"Failed to sync like with Subsonic: {str(e)}")
            subsonic_synced = False
            
        db.session.commit()
        return jsonify({"status": "success", "subsonic_synced": subsonic_synced}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error liking track: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@queue_bp.route('/dislike/<string:track_id>', methods=['POST'])
def dislike_track(track_id):
    try:
        user = get_or_create_default_user()
        
        # Add to history
        history = InteractionHistory(
            user_id=user.id,
            track_id=track_id,
            action='dislike'
        )
        db.session.add(history)
        
        # Unstar on Subsonic
        try:
            client = get_subsonic_client()
            client.star_track(track_id, star=False)
            subsonic_synced = True
        except Exception as e:
            current_app.logger.warning(f"Failed to sync dislike with Subsonic: {str(e)}")
            subsonic_synced = False
            
        # Also clear this track if it is in the upcoming queue
        QueueItem.query.filter_by(user_id=user.id, track_id=track_id, status='pending').delete()
        
        db.session.commit()
        return jsonify({"status": "success", "subsonic_synced": subsonic_synced}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error disliking track: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@queue_bp.route('/clear', methods=['POST'])
def clear_queue():
    try:
        user = get_or_create_default_user()
        QueueItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return jsonify({"status": "success", "message": "Queue cleared successfully."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing queue: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@queue_bp.route('/mode', methods=['GET', 'POST'])
def recommendation_mode():
    try:
        user = get_or_create_default_user()
        if request.method == 'POST':
            data = request.get_json() or {}
            mode = data.get('mode', 'llm').lower()
            if mode not in ['llm', 'local']:
                return jsonify({"status": "error", "message": "Invalid mode. Must be 'llm' or 'local'"}), 400
                
            prefs = user.llm_preferences or {}
            prefs["recommendation_mode"] = mode
            user.llm_preferences = prefs
            db.session.commit()
            
            # Clear upcoming queue when mode switches to recalculate properly
            QueueItem.query.filter_by(user_id=user.id, status='pending').delete()
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "message": f"Recommendation mode successfully updated to {mode}",
                "mode": mode
            }), 200
        else:
            current_mode = user.llm_preferences.get(
                "recommendation_mode", 
                current_app.config.get("RECOMMENDATION_MODE", "llm")
            )
            return jsonify({"status": "success", "mode": current_mode}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in recommendation_mode: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500
