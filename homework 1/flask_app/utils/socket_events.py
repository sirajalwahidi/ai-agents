"""
socket_events.py — Handles real-time chat messages using WebSockets.

WEBSOCKETS vs. HTTP:
  When you visit /resume, your browser makes one HTTP request and gets one
  HTML response — then the connection closes. That's how most web pages work.

  WebSockets are different: the connection stays open, like a phone call.
  Both sides (browser and server) can send messages at any time without
  making a new request. This is why the chat feels instant.

HOW EVENTS WORK:
  Instead of URL routes, WebSockets use named events:
    - Browser emits 'send_message'  →  server handles it here
    - Server emits 'receive_message' →  browser displays the reply

  The @socketio.on(...) decorator works just like @app.route(...) in Flask,
  but for WebSocket events instead of HTTP requests.
"""

# Step 0: Note that 'db = None' was removed because database is attached to app (current_app.db)

from flask import current_app
from flask_socketio import emit
from flask_app import socketio
from flask_app.utils.llm import handle_ai_chat_request


@socketio.on("send_message")
def handle_message(data):
    """
    Called automatically when the browser emits a 'send_message' event.

    Args:
        data (dict): Contains 'message' — the text typed by the user.

    Flow:
        1. Extract the user's message from event data.
        2. Retrieve the database instance from the Flask app context (current_app.db).
        3. Pass the request to handle_ai_chat_request with role="Orchestrator".
        4. Emit the AI's orchestrated reply back to the browser as 'receive_message'.
    """
    user_message = data.get("message", "").strip()

    if not user_message:
        return

    # Step 0: Read database directly from the current app instance
    # Get the database instance attached to the active Flask application
    db = current_app.db

    # إرسال الرسالة إلى الـ Orchestrator للتحليل والتنسيق بين الخبراء
    # Route the user's request through the Orchestrator expert
    try:
        ai_response = handle_ai_chat_request(db, role="Orchestrator", message=user_message)
    except Exception as error:
        print(f"LLM error: {error}")
        ai_response = f"⚠️ Could not reach the AI: {error}"

    # إرسال الرد المكتمل إلى واجهة المستخدم
    # Emit the final combined answer back to the front-end JavaScript listener
    emit("receive_message", {"response": ai_response})