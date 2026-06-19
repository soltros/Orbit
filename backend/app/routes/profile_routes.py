from flask import Blueprint, jsonify, request, current_app
from app import db
from app.models import UserProfile, InteractionHistory, Track, Genre
from app.llm import LLMClient
from app.routes.queue_routes import get_or_create_default_user
from app.rate_limiter import is_rate_limited

profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')

@profile_bp.route('/', methods=['GET'])
def get_profile():
    try:
        user = get_or_create_default_user()
        return jsonify({
            "status": "success",
            "profile": user.to_dict()
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@profile_bp.route('/favorites', methods=['GET'])
def get_favorites():
    try:
        user = get_or_create_default_user()
        history_items = InteractionHistory.query.filter_by(user_id=user.id, action='like').order_by(InteractionHistory.timestamp.desc()).all()
        
        # We need distinct tracks. A user could theoretically like a track multiple times if we allow toggling, 
        # but dislike un-likes it. We'll just grab unique tracks.
        seen = set()
        favorites = []
        for h in history_items:
            if h.track and h.track.id not in seen:
                seen.add(h.track.id)
                favorites.append(h.track.to_dict())
                
        return jsonify({
            "status": "success",
            "favorites": favorites
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching favorites: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

@profile_bp.route('/regenerate', methods=['POST'])
def regenerate_profile():
    try:
        if is_rate_limited(max_requests=5, period=300): # max 5 profile updates / 5 mins
            return jsonify({
                "status": "error",
                "message": "Rate limit exceeded. Profile regeneration is limited to 5 attempts per 5 minutes."
            }), 429
            
        user = get_or_create_default_user()
        
        # 1. Summarize history
        history_items = InteractionHistory.query.filter_by(user_id=user.id).all()
        likes = [h.track.to_dict() for h in history_items if h.action == 'like' and h.track]
        skips = [h.track.to_dict() for h in history_items if h.action == 'skip' and h.track]
        plays = [h.track.to_dict() for h in history_items if h.action == 'play' and h.track]
        
        # Group likes/skips/plays by artist and genre for the LLM
        def aggregate_music_data(tracks_list):
            artists = {}
            genres = {}
            for t in tracks_list:
                art = t.get('artist', 'Unknown')
                artists[art] = artists.get(art, 0) + 1
                for g in t.get('genres', []):
                    genres[g] = genres.get(g, 0) + 1
            # Sort
            sorted_artists = sorted(artists.items(), key=lambda x: x[1], reverse=True)[:5]
            sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)[:5]
            return {
                "top_artists": [a[0] for a in sorted_artists],
                "top_genres": [g[0] for g in sorted_genres],
                "total_count": len(tracks_list)
            }
            
        history_summary = {
            "liked_songs": aggregate_music_data(likes),
            "skipped_songs": aggregate_music_data(skips),
            "recent_plays": aggregate_music_data(plays[-20:])
        }
        
        # 2. Summarize general library stats
        total_tracks = Track.query.count()
        bpm_tracks = Track.query.filter(Track.bpm.isnot(None)).all()
        if bpm_tracks and len(bpm_tracks) > 0:
            avg_bpm = int(sum(t.bpm for t in bpm_tracks) / len(bpm_tracks))
        else:
            avg_bpm = None
        
        genres_in_db = Genre.query.all()
        genres_list = [g.name for g in genres_in_db]
        
        library_summary = {
            "total_cached_tracks": total_tracks,
            "average_bpm": avg_bpm,
            "available_genres": genres_list[:25] # Limit list to keep context size clean
        }
        
        # 3. Call LLM to generate taste profile
        llm = LLMClient()
        new_profile = llm.generate_profile(
            user_history_summary=history_summary,
            library_stats_summary=library_summary
        )
        
        # 4. Save profile
        prefs = user.llm_preferences or {}
        prefs["generated_profile"] = new_profile
        user.llm_preferences = prefs
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "User profile successfully regenerated.",
            "profile": user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error regenerating profile: {str(e)}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500
