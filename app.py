from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room
from threading import Thread
import time
import os

app = Flask(__name__, static_folder='.')
app.config['SECRET_KEY'] = 'lovelink-secret'

# Allow unsafe Werkzeug in production (Render-specific workaround)
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# In-memory session tracker
rooms = {}

@app.route('/')
@app.route('/connect/<code>')
def index(code=None):
    return send_from_directory('.', 'index.html')

@socketio.on('join')
def on_join(code):
    join_room(code)
    rooms[code] = time.time()

@socketio.on('status')
def on_status(data):
    emit('status', data, to=request.sid, include_self=False, room=request.namespace.rooms[0])

@socketio.on('notify')
def on_notify(data):
    emit('notify', data, room=request.namespace.rooms[0])

# Background thread to expire sessions after 24 hours
def cleanup():
    while True:
        now = time.time()
        expired = [code for code, ts in rooms.items() if now - ts > 86400]
        for code in expired:
            del rooms[code]
        time.sleep(600)

Thread(target=cleanup, daemon=True).start()
