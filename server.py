import os
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ================= APP =================
app = FastAPI()

# Разрешаем все CORS (для теста)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ================= STATE =================
connected = {}          # client_id -> WebSocket
offline_messages = {}   # client_id -> [messages]

# ================= WEBSOCKET =================
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    client_id = None
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            # ---------- регистрация ----------
            if msg["type"] == "register":
                client_id = msg["id"]
                connected[client_id] = ws
                print(f"[+] {client_id} connected")

                # Отправляем оффлайн-сообщения
                for m in offline_messages.get(client_id, []):
                    await ws.send_text(json.dumps(m))
                offline_messages[client_id] = []

            # ---------- сообщение ----------
            elif msg["type"] == "message":
                to_id = msg["to"]
                payload = {"type":"message", "from":msg["from"], "text":msg["text"]}

                if to_id in connected:
                    await connected[to_id].send_text(json.dumps(payload))
                else:
                    offline_messages.setdefault(to_id, []).append(payload)

    except:
        pass
    finally:
        if client_id and client_id in connected:
            connected.pop(client_id)
            print(f"[-] {client_id} disconnected")

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
