import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("app:asgi_app", host="0.0.0.0", port=port, proxy_headers=True)
