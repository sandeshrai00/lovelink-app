from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time
import threading
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'love_secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active pairs {pair_code: [host_sid, partner_sid]}
active_pairs = {}
# Store creation times {pair_code: timestamp}
pair_timestamps = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_pair')
def handle_create_pair(code):
    if code not in active_pairs:
        active_pairs[code] = [request.sid]
        pair_timestamps[code] = time.time()
        emit('pair_created', room=request.sid)
        print(f"Pair created: {code}")

@socketio.on('join_pair')
def handle_join_pair(code):
    if code in active_pairs and len(active_pairs[code]) < 2:
        active_pairs[code].append(request.sid)
        emit('pair_joined', room=active_pairs[code][0])  # Notify host
        emit('pair_joined', room=request.sid)           # Notify partner
        print(f"Pair joined: {code}")

@socketio.on('user_update')
def handle_user_update(data):
    # Find partner in the same pair
    for code, sids in active_pairs.items():
        if request.sid in sids:
            partner_sid = sids[0] if sids[1] == request.sid else sids[1]
            emit('partner_update', data, room=partner_sid)
            break

@socketio.on('send_notification')
def handle_notification():
    # Find partner in the same pair
    for code, sids in active_pairs.items():
        if request.sid in sids:
            partner_sid = sids[0] if sids[1] == request.sid else sids[1]
            emit('partner_notification', room=partner_sid)
            break

@socketio.on('disconnect')
def handle_disconnect():
    # Clean up disconnected clients
    for code, sids in list(active_pairs.items()):
        if request.sid in sids:
            sids.remove(request.sid)
            if not sids:
                del active_pairs[code]
                del pair_timestamps[code]
            else:
                # Notify remaining partner about disconnect
                emit('partner_disconnected', room=sids[0])
            break

def check_expired_pairs():
    current_time = time.time()
    expired_codes = []
    
    for code, timestamp in pair_timestamps.items():
        if current_time - timestamp > 86400:  # 24 hours
            expired_codes.append(code)
    
    for code in expired_codes:
        for sid in active_pairs.get(code, []):
            emit('pair_expired', room=sid)
        if code in active_pairs:
            del active_pairs[code]
        if code in pair_timestamps:
            del pair_timestamps[code]

# Start background task when app initializes
def start_background_task():
    def expire_checker():
        while True:
            check_expired_pairs()
            time.sleep(60)  # Check every minute
    
    threading.Thread(target=expire_checker, daemon=True).start()

# Start the background task when the app starts
start_background_task()
