from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'love_secret!')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Store active pairs {pair_code: [host_sid, partner_sid]}
active_pairs = {}
# Store creation times {pair_code: timestamp}
pair_timestamps = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_pair')
def handle_create_pair():
    code = generate_pairing_code()
    active_pairs[code] = [request.sid]
    pair_timestamps[code] = time.time()
    emit('pair_created', {'code': code}, room=request.sid)
    print(f"Pair created: {code}")

@socketio.on('join_pair')
def handle_join_pair(code):
    if code in active_pairs and len(active_pairs[code]) < 2:
        active_pairs[code].append(request.sid)
        # Notify both users that they are paired
        emit('pair_joined', {'partner_sid': request.sid}, room=active_pairs[code][0])
        emit('pair_joined', {'partner_sid': active_pairs[code][0]}, room=request.sid)
        print(f"Pair joined: {code}")
    else:
        emit('pair_error', {'message': 'Invalid code or pair full'}, room=request.sid)

@socketio.on('user_update')
def handle_user_update(data):
    # Data should be encrypted; we decrypt here with the code (which acts as secret)
    # In a real app, we would use proper end-to-end encryption. Here, we trust the client to have encrypted.
    for code, sids in active_pairs.items():
        if request.sid in sids:
            partner_sid = sids[0] if sids[1] == request.sid else sids[1]
            emit('partner_update', data, room=partner_sid)
            break

@socketio.on('send_notification')
def handle_notification():
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
                if code in pair_timestamps:
                    del pair_timestamps[code]
            else:
                # Notify the remaining partner
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

# Generate a 6-digit pairing code
def generate_pairing_code():
    import random
    return str(random.randint(100000, 999999))

# Schedule the background task to check for expired pairs
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_expired_pairs, trigger="interval", hours=1)
scheduler.start()