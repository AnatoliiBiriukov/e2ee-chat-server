import os
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ================= APP =================

app = FastAPI()

# Разрешаем CORS (для теста/локальной разработки)
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

            # ---------- РЕГИСТРАЦИЯ ----------
            # Клиент должен прислать {"type": "register", "id": "..."}
            if msg["type"] == "register":
                client_id = msg["id"]
                connected[client_id] = ws
                print(f"[+] {client_id} connected")

                # Отправляем накопленные оффлайн‑сообщения
                for m in offline_messages.get(client_id, []):
                    await ws.send_text(json.dumps(m))
                offline_messages[client_id] = []

            # ---------- СООБЩЕНИЕ ----------
            # Клиент отправляет {"type":"message","from":"A","to":"B","text":"..."}
            elif msg["type"] == "message":
                to_id = msg["to"]
                payload = {"type":"message","from":msg["from"],"text":msg["text"]}

                # Если получатель онлайн
                if to_id in connected:
                    try:
                        await connected[to_id].send_text(json.dumps(payload))
                    except Exception as e:
                        # Если отправка не удалась, складываем в очередь
                        offline_messages.setdefault(to_id, []).append(payload)
                else:
                    # Оффлайн — в очередь
                    offline_messages.setdefault(to_id, []).append(payload)

    except Exception as e:
        # Закрытие соединения или ошибка
        pass

    finally:
        if client_id and client_id in connected:
            connected.pop(client_id)
            print(f"[-] {client_id} disconnected")

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"[INFO] Server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
