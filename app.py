import os
import threading
import time
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='asgi')

# In-memory sessions: code -> {'time': timestamp, 'sids': set()}
sessions = {}
SESSION_TTL = 24 * 3600

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/connect/<code>')
def connect(code):
    return send_from_directory('.', 'index.html')

@socketio.on('join')
def on_join(code):
    sid = threading.current_thread().ident
    join_room(code)
    sessions.setdefault(code, {{'time': time.time(), 'sids': set()}})['sids'].add(sid)

@socketio.on('encrypted')
def on_encrypted(data):
    # Broadcast encrypted payload to other in room
    code = data.get('room') or data.get('code') or request.args.get('code')
    socketio.emit('encrypted', {{'payload': data['payload']}}, room=code, include_self=False)

# Background cleanup
def cleanup():
    while True:
        now = time.time()
        expired = [c for c, v in sessions.items() if now - v['time'] > SESSION_TTL]
        for c in expired:
            for sid in sessions[c]['sids']:
                leave_room(c, sid=sid)
            del sessions[c]
        time.sleep(600)

threading.Thread(target=cleanup, daemon=True).start()

if __name__ == '__main__':
    # For local dev
    socketio.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
