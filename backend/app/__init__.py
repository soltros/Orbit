import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from app.config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)

    # Ensure the SQLite database directory exists
    db_dir = os.path.dirname(app.config["DATABASE_PATH"])
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Create tables
    with app.app_context():
        from app import models
        db.create_all()
        
        # Ensure indexes exist for older databases upgrading to this version
        from sqlalchemy import text
        try:
            with db.engine.connect() as conn:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_queue_items_user_id ON queue_items (user_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_queue_items_track_id ON queue_items (track_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_queue_items_position ON queue_items (position);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_queue_items_status ON queue_items (status);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_interaction_history_user_id ON interaction_history (user_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_interaction_history_track_id ON interaction_history (track_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_interaction_history_action ON interaction_history (action);"))
                conn.commit()
        except Exception as e:
            app.logger.warning(f"Could not create indexes manually: {e}")

    # Simple healthcheck endpoint
    @app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200

    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.subsonic_routes import subsonic_bp
    from app.routes.queue_routes import queue_bp
    from app.routes.profile_routes import profile_bp
    from app.routes.playlist_routes import playlist_bp
    from app.routes.library_routes import library_bp
    from app.routes.lastfm_routes import lastfm_bp
    
    from app.routes.setup_routes import setup_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(subsonic_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(playlist_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(lastfm_bp)

    # Register custom CLI commands
    from app.commands import register_commands
    register_commands(app)
    
    return app
