"""
__init__.py — creates and configures the Flask application.

This file is the entry point for the flask_app package. Its job is to:
  1. Load configuration (API keys from .env)
  2. Set up the database (create tables, load CSV data)
  3. Register routes (the URL paths the app responds to)
  4. Set up Socket.IO (for real-time chat)
  5. Return the configured app so app.py can run it

WHY A create_app() FUNCTION?
  Wrapping setup in a function (rather than running code at import time)
  is a common Flask pattern. It makes the app easier to test and configure.
  This pattern is called an "application factory".

# QUESTION: What does purge=True do in db.createTables(purge=True)?
#           Try changing it to False, add a row to a CSV, and restart.
#           What happens? Why?
"""

from flask import Flask
from flask_socketio import SocketIO
from dotenv import load_dotenv

# Create the SocketIO instance here at module level.
# Both this file and socket_events.py need to reference the same instance,
# so it lives here where both can import it.
socketio = SocketIO()


def create_app():
    """
    Build and return the configured Flask application.

    Returns:
        tuple: (app, socketio) — both are needed to run the server.
    """

    # load_dotenv() reads the .env file and puts its values into os.environ.
    # This is how OPENROUTER_API_KEY becomes available throughout the app
    # without ever being written in the source code.
    load_dotenv()

    app = Flask(__name__)

    # The secret_key is used to cryptographically sign session cookies.
    # Change this to a long random string in any real deployment.
    app.secret_key = 'dev-key-change-for-production'

    # Set up the database: create tables and load CSV data
    from flask_app.utils.database import database
    db = database()
    print("Setting up database...")
    
    # ======================================================
    # DATABASE INITIALIZATION SETTINGS
    # ======================================================
    
    # 1.(purge=False) PERSISTENCE MODE (Recommended for Demo & Recording)
    # It creates tables only if they do not exist (INSERT OR IGNORE), and preserves existing data.. 
    # New skills added via chat will NOT be deleted on server restart.
    db.createTables(purge=False)
    
    # 2.(purge=True) RESET MODE (For Testing & Resetting)
    # Deletes all tables (DROP TABLE) and reloads default data from CSV files.
    # Use this ONLY if you edited CSV files or want to start fresh.
    # db.createTables(purge=True) #Cancel the comment if you want to activate it.

    # Homework 2: embed any CSV-seeded row that doesn't have one yet
    db.backfillEmbeddings()

    # Homework 1 (Step 0): Attach db instance to the app so that other 
    # modules (like routes.py and socket_events.py) can access it safely via current_app.db
    app.db = db

    print("Database ready.")
    
    # Connect Socket.IO to the Flask app
    socketio.init_app(app)

    # Register routes and socket events inside the app context.
    with app.app_context():
        from flask_app import routes
        from flask_app.utils import socket_events
        # Note: routes and socket_events now access the database via current_app.db

    # Prevent browsers from caching old versions of pages during development
    @app.after_request
    def disable_cache(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app, socketio
