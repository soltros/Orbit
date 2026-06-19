import random
import numpy as np
from datetime import datetime, timedelta
from app import db
from app.models import Track, Genre, InteractionHistory, UserProfile
from app.listenbrainz import get_similar_artists

def calculate_cosine_similarity(v1, v2):
    """Computes the cosine similarity between two numeric embedding vectors."""
    if not v1 or not v2:
        return 0.0
    a1 = np.array(v1)
    a2 = np.array(v2)
    norm1 = np.linalg.norm(a1)
    norm2 = np.linalg.norm(a2)
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return float(np.dot(a1, a2) / (norm1 * norm2))

def get_hybrid_recommendations(user, count=5):
    """
    Implements the Hybrid Recommendation Engine scoring workflow:
    - 40% Acoustic Similarity (Vector Cosine Distance)
    - 30% Metadata Tagging Relationships
    - 20% ListenBrainz Collaborative Graph
    - 10% User Listening & Skip History
    
    Returns a list of dicts with track_id and why_queued explanation.
    """
    # 1. Select seed track: Use the last played track or a random liked track
    last_played = InteractionHistory.query.filter_by(user_id=user.id, action='play')\
        .order_by(InteractionHistory.timestamp.desc()).first()
        
    seed_track = None
    if last_played:
        seed_track = Track.query.get(last_played.track_id)
        
    if not seed_track:
        # Fallback: check liked tracks
        last_liked = InteractionHistory.query.filter_by(user_id=user.id, action='like')\
            .order_by(InteractionHistory.timestamp.desc()).first()
        if last_liked:
            seed_track = Track.query.get(last_liked.track_id)
            
    if not seed_track:
        # Fallback to random track in library
        seed_track = Track.query.order_by(db.func.random()).first()
        
    if not seed_track:
        return []

    # 2. Compile list of excluded tracks (currently queued or played in the last 2 hours)
    recent_history = InteractionHistory.query.filter_by(user_id=user.id)\
        .filter(InteractionHistory.timestamp > datetime.utcnow() - timedelta(hours=2)).all()
    exclude_ids = {h.track_id for h in recent_history}
    
    # Exclude seed track itself
    exclude_ids.add(seed_track.id)
    
    # Select candidate pool
    candidates = Track.query.filter(~Track.id.in_(exclude_ids) if exclude_ids else True).limit(200).all()
    if not candidates:
        return []

    # 3. Pull ListenBrainz similar artists for seed artist
    similar_artists = []
    try:
        similar_artists = get_similar_artists(seed_track.artist)
    except Exception:
        pass
    similar_artists_set = {a.lower() for a in similar_artists}

    # 4. Score each candidate
    scored_candidates = []
    
    seed_genres = {g.name for g in seed_track.genres}
    
    # Gather user's history metrics
    likes_query = InteractionHistory.query.filter_by(user_id=user.id, action='like').all()
    liked_ids = {h.track_id for h in likes_query}
    
    skips_query = InteractionHistory.query.filter_by(user_id=user.id, action='skip').all()
    skipped_ids = {h.track_id for h in skips_query}

    for candidate in candidates:
        # A. Acoustic Score (40%)
        acoustic_score = 0.0
        if seed_track.acoustic_embedding and candidate.acoustic_embedding:
            acoustic_score = calculate_cosine_similarity(
                seed_track.acoustic_embedding, 
                candidate.acoustic_embedding
            )
            
        # B. Metadata Score (30%)
        metadata_score = 0.0
        # Check genre matches
        cand_genres = {g.name for g in candidate.genres}
        matching_genres = seed_genres.intersection(cand_genres)
        if matching_genres:
            metadata_score += 0.5 # Share genre
        if candidate.artist.lower() == seed_track.artist.lower():
            metadata_score += 0.3 # Same artist
        if candidate.bpm and seed_track.bpm and abs(candidate.bpm - seed_track.bpm) <= 10:
            metadata_score += 0.2 # Similar tempo (BPM)
            
        # C. Community ListenBrainz Score (20%)
        community_score = 0.0
        if candidate.artist.lower() in similar_artists_set:
            community_score = 1.0

        # D. User History Score (10%)
        history_score = 0.5 # Base baseline
        if candidate.id in liked_ids:
            history_score = 1.0
        elif candidate.id in skipped_ids:
            history_score = 0.0
            
        # Calculate combined weighted score
        final_score = (acoustic_score * 0.4) + (metadata_score * 0.3) + (community_score * 0.2) + (history_score * 0.1)
        
        # Build explanation justification
        explanation_reasons = []
        if acoustic_score > 0.8:
            explanation_reasons.append("has a highly matching acoustic frequency profile")
        elif matching_genres:
            explanation_reasons.append(f"shares the {list(matching_genres)[0]} style")
            
        if community_score > 0.0:
            explanation_reasons.append("matches your ListenBrainz community taste mappings")
        if candidate.bpm and seed_track.bpm and abs(candidate.bpm - seed_track.bpm) <= 5:
            explanation_reasons.append(f"keeps the beat at {candidate.bpm} BPM")
            
        if not explanation_reasons:
            explanation_reasons.append("continues the station transition flow")
            
        why_queued = f"Local DJ choice: This song {', and '.join(explanation_reasons[:2])} based on {seed_track.title}."
        
        scored_candidates.append({
            "track_id": candidate.id,
            "score": final_score,
            "why_queued": why_queued
        })
        
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    return scored_candidates[:count]
