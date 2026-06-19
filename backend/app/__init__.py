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

    # Simple healthcheck endpoint
    @app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200

    # Register blueprints
    from app.routes.subsonic_routes import subsonic_bp
    from app.routes.queue_routes import queue_bp
    from app.routes.profile_routes import profile_bp
    from app.routes.playlist_routes import playlist_bp
    from app.routes.library_routes import library_bp
    app.register_blueprint(subsonic_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(playlist_bp)
    app.register_blueprint(library_bp)

    # Register custom CLI commands
    from app.commands import register_commands
    register_commands(app)
    
    return app
