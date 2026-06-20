from app import db
from datetime import datetime

# Association table for many-to-many relationship between tracks and genres
track_genres = db.Table('track_genres',
    db.Column('track_id', db.String(64), db.ForeignKey('tracks.id', ondelete='CASCADE'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True)
)

class Genre(db.Model):
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }

class ArtistCache(db.Model):
    __tablename__ = 'artist_cache'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False, index=True) # lowercase artist name
    image_url = db.Column(db.Text)
    bio = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "name": self.name,
            "image_url": self.image_url,
            "bio": self.bio
        }

class Track(db.Model):
    __tablename__ = 'tracks'
    id = db.Column(db.String(64), primary_key=True) # Usually the Subsonic ID
    title = db.Column(db.String(255), nullable=False, index=True)
    artist = db.Column(db.String(255), nullable=False, index=True)
    album = db.Column(db.String(255), index=True)
    duration = db.Column(db.Integer) # in seconds
    path = db.Column(db.Text)
    
    # Mutagen extended tags
    bpm = db.Column(db.Integer)
    custom_tags = db.Column(db.JSON) # Stores tags list or key-values
    last_synced = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Acoustic features
    acoustic_embedding = db.Column(db.JSON) # List of floats
    acoustic_status = db.Column(db.String(20), default='pending', index=True) # pending, processing, completed, failed
    acoustic_error = db.Column(db.Text)
    key = db.Column(db.String(10)) # e.g. C Major
    energy = db.Column(db.Float) # 0.0 to 1.0

    # Relationships
    genres = db.relationship('Genre', secondary=track_genres, backref=db.backref('tracks', lazy='dynamic'))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration,
            "path": self.path,
            "bpm": self.bpm,
            "custom_tags": self.custom_tags,
            "genres": [g.name for g in self.genres],
            "acoustic_status": self.acoustic_status,
            "key": self.key,
            "energy": self.energy,
            "last_synced": self.last_synced.isoformat() if self.last_synced else None
        }

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    llm_preferences = db.Column(db.JSON, default=dict) # e.g., prompt directives, model choices
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "llm_preferences": self.llm_preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class QueueItem(db.Model):
    __tablename__ = 'queue_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    track_id = db.Column(db.String(64), db.ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False, index=True)
    why_queued = db.Column(db.Text) # LLM explanation sentence
    position = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', index=True) # pending, playing, played, skipped
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    played_at = db.Column(db.DateTime)
    skipped_at = db.Column(db.DateTime)

    # Relationships
    track = db.relationship('Track', backref='queue_items')
    user = db.relationship('UserProfile', backref='queue_items')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "track": self.track.to_dict() if self.track else None,
            "why_queued": self.why_queued,
            "position": self.position,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "played_at": self.played_at.isoformat() if self.played_at else None,
            "skipped_at": self.skipped_at.isoformat() if self.skipped_at else None
        }

class InteractionHistory(db.Model):
    __tablename__ = 'interaction_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    track_id = db.Column(db.String(64), db.ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False, index=True) # play, skip, like, dislike
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    track = db.relationship('Track')
    user = db.relationship('UserProfile')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "track_id": self.track_id,
            "action": self.action,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
