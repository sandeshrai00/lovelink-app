import os
from app import app, socketio
import uvicorn
from pyvirtualdisplay import Display  # Only if running in a headless environment

# If running in a headless environment (like Render), start virtual display
if os.environ.get('RENDER'):
    display = Display(visible=0, size=(800, 600))
    display.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Use Uvicorn with WebSockets
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        ws='websockets'
    )