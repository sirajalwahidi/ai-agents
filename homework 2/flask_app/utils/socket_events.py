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

from flask import current_app, session
from flask_socketio import emit
from flask_app import socketio
from flask_app.utils.llm import (
    handle_ai_chat_request,
    assess_message_risk,
    request_human_validation,
    handle_validation_response,
)

# db is attached to the Flask app instance by create_app() in __init__.py
# (app.db = db). Flask-SocketIO runs event handlers inside an app context,
# so current_app.db reaches that same shared instance here too -- no
# separate module-level variable needed.
#
# `session` (Homework 2) works here the same way: Flask-SocketIO ties its
# event handlers to the same signed session cookie the page's HTTP requests
# use, so state stashed here in one message (see request_human_validation
# in llm.py) is still there on the next.

# الحالي Flask يتم جلب قاعدة البيانات والجلسة مباشرة من سياق تطبيق
# (App Context) يعمل داخل سياق التطبيق SocketIO للبيانات المشتركة لأن session و current_app.db تصل
# للحفاظ على الحالة بين الرسائل المتتابعة. HTTP ويشارك نفس كوكيز الجلسة مع طلبات

@socketio.on('send_message')
def handle_message(data):
    """
    Called automatically when the browser emits a 'send_message' event.

    Args:
        data (dict): Contains 'message' — the text typed by the user.

    Flow:
        1. Check if a confirmation is already pending in the session.
        2. Otherwise, check if the incoming message contains risky keywords.
        3. Otherwise, proceed with the normal Orchestrator chat flow.
    """
    # Extract user message from event data / استخراج نص الرسالة وتنظيف المساحات
    user_message = data.get('message', '').strip()

    if not user_message:
        return

    try:
        # Retrieve the database instance attached to the active Flask application
        # جلب كائن قاعدة البيانات من التطبيق النشط
        db = current_app.db

        # 1. Is a confirmation already pending?
        # فحص ما إذا كانت الرسالة عبارة عن إجابة (yes/no) على طلب تأكيد معلق
        if session.get('pending_validation'):
            ai_response = handle_validation_response(db, user_message)

        # 2. Otherwise, does this message look risky?
        # فحص خطورة الرسالة وتنسيق طلب التأكيد إذا احتوت كلمات تدميرية
        elif assess_message_risk(user_message):
            ai_response = request_human_validation(user_message)

        # 3. Otherwise, proceed as normal through the Orchestrator
        # إرسال الرسائل الآمنة العادية مباشرة للمنسق الرئيسي
        else:
            ai_response = handle_ai_chat_request(db, role="Orchestrator", message=user_message)

    except Exception as error:
        # Handle execution exceptions gracefully
        # معالجة الاستثناءات والأخطاء وطباعتها في التيرمينال
        print(f"LLM error: {error}")
        ai_response = "Sorry, something went wrong answering that."

    # Emit the AI's reply back to the browser as 'receive_message'
    # // للواجهة الأمامية WebSocket إرسال الرد النهائي عبر الـ
    emit('receive_message', {'response': ai_response})