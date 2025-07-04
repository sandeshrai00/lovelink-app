import os
import time
import random
import threading
from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit
import uvicorn
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'love_secret!')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active pairs
active_pairs = {}
pair_timestamps = {}
user_data = {}

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LoveLink ❤️</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 500px; margin: 0 auto; background: rgba(255, 255, 255, 0.95); border-radius: 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1); overflow: hidden; }
        header { background: #e91e63; color: white; text-align: center; padding: 20px; }
        .screen { padding: 20px; display: none; }
        .active { display: block; }
        h1 { font-size: 1.8rem; margin-bottom: 5px; }
        h2 { color: #e91e63; margin: 15px 0 10px; font-size: 1.4rem; }
        .qr-container { text-align: center; margin: 20px 0; }
        #qr-canvas { width: 200px; height: 200px; margin: 0 auto; border: 10px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .code-display { font-size: 2.5rem; letter-spacing: 5px; color: #e91e63; margin: 20px 0; font-weight: bold; text-align: center; }
        .input-group { margin: 20px 0; }
        input { width: 100%; padding: 15px; border: 2px solid #e91e63; border-radius: 50px; font-size: 1.1rem; text-align: center; }
        button { background: #e91e63; color: white; border: none; padding: 15px 30px; border-radius: 50px; font-size: 1.1rem; width: 100%; cursor: pointer; margin: 10px 0; transition: all 0.3s; }
        button:hover { background: #c2185b; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .heart-btn { width: 80px; height: 80px; border-radius: 50%; background: #e91e63; display: flex; align-items: center; justify-content: center; margin: 20px auto; cursor: pointer; box-shadow: 0 5px 15px rgba(233, 30, 99, 0.4); transition: all 0.3s; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
        .heart-btn::after { content: "❤️"; font-size: 2.5rem; }
        .map-container { height: 250px; border-radius: 15px; overflow: hidden; margin: 15px 0; border: 2px solid #e91e63; }
        .status-container { display: flex; justify-content: space-between; margin: 15px 0; }
        .status-box { background: white; border-radius: 15px; padding: 15px; width: 48%; text-align: center; box-shadow: 0 3px 10px rgba(0,0,0,0.08); }
        .battery-display { font-size: 2rem; font-weight: bold; margin: 10px 0; }
        .battery-low { color: #ff5722; }
        .battery-medium { color: #ffc107; }
        .battery-high { color: #4caf50; }
        .notification { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #4caf50; color: white; padding: 15px 30px; border-radius: 50px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); z-index: 1000; display: none; }
        .camera-container { width: 100%; height: 300px; margin: 15px 0; position: relative; }
        #camera-preview { width: 100%; height: 100%; object-fit: cover; border-radius: 15px; }
        #scan-instruction { position: absolute; bottom: 10px; left: 0; width: 100%; text-align: center; color: white; background: rgba(0,0,0,0.5); padding: 10px; }
        .disclaimer { font-size: 0.8rem; color: #777; text-align: center; margin-top: 20px; }
        .error-message { color: #f44336; text-align: center; margin: 10px 0; }
        .expiry-box { background: #f5f5f5; padding: 10px; border-radius: 10px; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="notification" id="notification">❤️ Your partner is thinking of you!</div>
    
    <div class="container">
        <header>
            <h1>LoveLink ❤️</h1>
            <p>Share location and battery status with your partner</p>
        </header>
        
        <!-- Home Screen -->
        <div id="home-screen" class="screen active">
            <h2>Start Sharing with Your Partner</h2>
            <button id="create-link-btn">Create Love Link</button>
            <button id="join-link-btn">Join with Code</button>
            <p class="disclaimer">No accounts needed • Connection lasts 24 hours</p>
        </div>
        
        <!-- Create Link Screen -->
        <div id="create-screen" class="screen">
            <h2>Your Love Link Code</h2>
            <div class="code-display" id="pairing-code">------</div>
            <p>Share this code with your partner:</p>
            
            <div class="qr-container">
                <canvas id="qr-canvas"></canvas>
            </div>
            
            <div class="input-group">
                <input type="text" id="share-link" readonly>
                <button onclick="copyLink()">Copy Link</button>
            </div>
            
            <p>Waiting for partner to join...</p>
            <button id="cancel-create">Cancel</button>
        </div>
        
        <!-- Join Screen -->
        <div id="join-screen" class="screen">
            <h2>Enter Partner's Code</h2>
            <div class="input-group">
                <input type="text" id="partner-code" placeholder="Enter 6-digit code" maxlength="6">
                <button id="connect-btn">Connect with Partner</button>
            </div>
            <div id="join-error" class="error-message"></div>
            
            <button id="cancel-join">Cancel</button>
        </div>
        
        <!-- Connected Screen -->
        <div id="connected-screen" class="screen">
            <h2>Connected with Partner ❤️</h2>
            
            <div class="map-container" id="user-map"></div>
            <div class="map-container" id="partner-map"></div>
            
            <div class="status-container">
                <div class="status-box">
                    <h3>Your Battery</h3>
                    <div class="battery-display" id="user-battery">--%</div>
                </div>
                <div class="status-box">
                    <h3>Partner's Battery</h3>
                    <div class="battery-display" id="partner-battery">--%</div>
                </div>
            </div>
            
            <div class="heart-btn" id="notify-btn"></div>
            <p>Tap the heart to notify your partner</p>
            
            <div class="expiry-box">
                <p>Connection expires at:</p>
                <p id="expiry-time">--:--:--</p>
            </div>
        </div>
    </div>

    <script>
        // DOM Elements
        const screens = {
            home: document.getElementById('home-screen'),
            create: document.getElementById('create-screen'),
            join: document.getElementById('join-screen'),
            connected: document.getElementById('connected-screen')
        };
        
        const pairingCodeEl = document.getElementById('pairing-code');
        const shareLinkEl = document.getElementById('share-link');
        const partnerCodeEl = document.getElementById('partner-code');
        const joinErrorEl = document.getElementById('join-error');
        const userBatteryEl = document.getElementById('user-battery');
        const partnerBatteryEl = document.getElementById('partner-battery');
        const expiryTimeEl = document.getElementById('expiry-time');
        const notificationEl = document.getElementById('notification');
        
        // App State
        let socket = null;
        let userMap = null;
        let partnerMap = null;
        let userMarker = null;
        let partnerMarker = null;
        let pairingCode = '';
        let expiryDate = null;
        
        // Initialize App
        function initApp() {
            // Set up screen navigation
            document.getElementById('create-link-btn').addEventListener('click', showCreateScreen);
            document.getElementById('join-link-btn').addEventListener('click', showJoinScreen);
            document.getElementById('cancel-create').addEventListener('click', showHomeScreen);
            document.getElementById('cancel-join').addEventListener('click', showHomeScreen);
            document.getElementById('connect-btn').addEventListener('click', connectToPartner);
            document.getElementById('notify-btn').addEventListener('click', sendNotification);
            
            // Check if we have a code in URL
            const urlParams = new URLSearchParams(window.location.search);
            const joinCode = urlParams.get('code');
            
            if (joinCode && joinCode.length === 6) {
                partnerCodeEl.value = joinCode;
                showJoinScreen();
                setTimeout(connectToPartner, 500); // Small delay to ensure socket is connected
            }
            
            // Connect to Socket.IO server
            socket = io();
            
            // Socket event listeners
            socket.on('pair_created', (data) => {
                pairingCode = data.code;
                pairingCodeEl.textContent = pairingCode;
                shareLinkEl.value = `${window.location.origin}?code=${pairingCode}`;
                generateQRCode(shareLinkEl.value);
            });
            
            socket.on('pair_joined', (data) => {
                expiryDate = new Date(Date.now() + 24 * 60 * 60 * 1000);
                updateExpiryTime();
                startSharing();
                showScreen('connected');
            });
            
            socket.on('pair_error', (data) => {
                joinErrorEl.textContent = data.message;
            });
            
            socket.on('partner_update', (data) => {
                if (data.location) {
                    updatePartnerLocation(data.location);
                }
                if (data.battery !== undefined) {
                    updatePartnerBattery(data.battery);
                }
            });
            
            socket.on('partner_notification', () => {
                showNotification();
            });
            
            socket.on('partner_disconnected', () => {
                alert('Your partner has disconnected');
                showHomeScreen();
            });
            
            socket.on('pair_expired', () => {
                alert('Your 24-hour connection has expired');
                showHomeScreen();
            });
        }
        
        // Screen Navigation
        function showScreen(screenName) {
            Object.values(screens).forEach(screen => {
                screen.classList.remove('active');
            });
            screens[screenName].classList.add('active');
            
            // Reset error messages
            joinErrorEl.textContent = '';
        }
        
        function showHomeScreen() {
            if (socket) socket.disconnect();
            showScreen('home');
        }
        
        function showCreateScreen() {
            socket.emit('create_pair');
            showScreen('create');
        }
        
        function showJoinScreen() {
            showScreen('join');
        }
        
        // QR Code Generation
        function generateQRCode(text) {
            const canvas = document.getElementById('qr-canvas');
            const ctx = canvas.getContext('2d');
            
            // Clear canvas
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Generate QR-like pattern
            ctx.fillStyle = '#000000';
            ctx.fillRect(20, 20, 160, 160);
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(70, 70, 60, 60);
            
            // Add text
            ctx.fillStyle = '#E91E63';
            ctx.font = 'bold 20px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('LoveLink', canvas.width / 2, 210);
        }
        
        // Connection Functions
        function connectToPartner() {
            const code = partnerCodeEl.value;
            if (code.length !== 6) {
                joinErrorEl.textContent = 'Please enter a 6-digit code';
                return;
            }
            
            socket.emit('join_pair', code);
        }
        
        // Location and Battery Sharing
        function startSharing() {
            // Initialize maps
            initMaps();
            
            // Start sharing location and battery
            shareLocation();
            shareBattery();
            
            // Set up periodic updates
            setInterval(shareLocation, 30000);
            setInterval(shareBattery, 60000);
            setInterval(updateExpiryTime, 1000);
        }
        
        function initMaps() {
            userMap = L.map('user-map').setView([0, 0], 2);
            partnerMap = L.map('partner-map').setView([0, 0], 2);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(userMap);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(partnerMap);
            
            userMarker = L.marker([0, 0]).addTo(userMap)
                .bindPopup('Your location')
                .openPopup();
                
            partnerMarker = L.marker([0, 0]).addTo(partnerMap)
                .bindPopup('Partner location');
        }
        
        function shareLocation() {
            if (!navigator.geolocation) return;
            
            navigator.geolocation.getCurrentPosition(position => {
                const { latitude, longitude } = position.coords;
                
                // Update user map
                userMap.setView([latitude, longitude], 13);
                userMarker.setLatLng([latitude, longitude]);
                
                // Send to partner
                const data = { location: { lat: latitude, lng: longitude } };
                socket.emit('user_update', data);
            });
        }
        
        async function shareBattery() {
            if (!navigator.getBattery) return;
            
            try {
                const battery = await navigator.getBattery();
                const batteryPercent = Math.round(battery.level * 100);
                
                // Update UI
                updateBatteryUI(userBatteryEl, batteryPercent);
                
                // Send to partner
                const data = { battery: batteryPercent };
                socket.emit('user_update', data);
            } catch (error) {
                console.error('Battery API error:', error);
            }
        }
        
        function updatePartnerLocation(location) {
            partnerMap.setView([location.lat, location.lng], 13);
            partnerMarker.setLatLng([location.lat, location.lng]);
        }
        
        function updatePartnerBattery(batteryPercent) {
            updateBatteryUI(partnerBatteryEl, batteryPercent);
        }
        
        function updateBatteryUI(element, percent) {
            element.textContent = `${percent}%`;
            element.className = 'battery-display ';
            
            if (percent < 30) element.classList.add('battery-low');
            else if (percent < 60) element.classList.add('battery-medium');
            else element.classList.add('battery-high');
        }
        
        function updateExpiryTime() {
            if (!expiryDate) return;
            
            const now = new Date();
            const diff = expiryDate - now;
            
            if (diff <= 0) {
                expiryTimeEl.textContent = "Expired";
                return;
            }
            
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            
            expiryTimeEl.textContent = 
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
        
        // Notification System
        function sendNotification() {
            socket.emit('send_notification');
            
            // Local feedback
            if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
        }
        
        function showNotification() {
            notificationEl.style.display = 'block';
            
            // Vibrate if supported
            if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
            
            // Show notification
            if (Notification.permission === 'granted') {
                new Notification('❤️ LoveLink', {
                    body: 'Your partner is thinking about you!'
                });
            }
            
            setTimeout(() => {
                notificationEl.style.display = 'none';
            }, 3000);
        }
        
        // Helper Functions
        function copyLink() {
            shareLinkEl.select();
            document.execCommand('copy');
            alert('Link copied to clipboard!');
        }
        
        // Initialize when page loads
        window.addEventListener('load', initApp);
        
        // Request notification permission
        if ('Notification' in window) {
            Notification.requestPermission();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# SocketIO Handlers
@socketio.on('create_pair')
def handle_create_pair():
    """Generate a new pairing code and store it"""
    code = str(random.randint(100000, 999999))
    active_pairs[code] = []
    pair_timestamps[code] = time.time()
    
    # Store the session ID for the creator
    active_pairs[code].append(request.sid)
    user_data[request.sid] = {'code': code}
    
    emit('pair_created', {'code': code}, room=request.sid)

@socketio.on('join_pair')
def handle_join_pair(code):
    """Join an existing pair with the provided code"""
    if code in active_pairs and len(active_pairs[code]) < 2:
        # Add the new user to the pair
        active_pairs[code].append(request.sid)
        user_data[request.sid] = {'code': code}
        
        # Notify both users that they are paired
        for sid in active_pairs[code]:
            emit('pair_joined', {}, room=sid)
    else:
        emit('pair_error', {'message': 'Invalid code or pair full'}, room=request.sid)

@socketio.on('user_update')
def handle_user_update(data):
    """Forward user updates to their partner"""
    if request.sid in user_data:
        code = user_data[request.sid]['code']
        for sid in active_pairs[code]:
            if sid != request.sid:
                emit('partner_update', data, room=sid)

@socketio.on('send_notification')
def handle_notification():
    """Send a notification to the partner"""
    if request.sid in user_data:
        code = user_data[request.sid]['code']
        for sid in active_pairs[code]:
            if sid != request.sid:
                emit('partner_notification', room=sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up when a user disconnects"""
    for sid, data in list(user_data.items()):
        if sid == request.sid:
            code = data['code']
            if code in active_pairs:
                active_pairs[code].remove(request.sid)
                if not active_pairs[code]:
                    del active_pairs[code]
                    del pair_timestamps[code]
                else:
                    # Notify the remaining partner
                    emit('partner_disconnected', room=active_pairs[code][0])
            del user_data[request.sid]
            break

def check_expired_pairs():
    """Check and expire old pairs every minute"""
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

# Start background task to check expired pairs
def start_background_task():
    def task():
        while True:
            check_expired_pairs()
            time.sleep(60)  # Check every minute
    
    thread = threading.Thread(target=task)
    thread.daemon = True
    thread.start()

start_background_task()

# Run the application
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)