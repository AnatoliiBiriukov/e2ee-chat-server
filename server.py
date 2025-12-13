from fastapi import FastAPI, WebSocket
import json
import uuid

app = FastAPI()
clients = {}  # id -> websocket
nicks = {}    # id -> nick

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()

    client_id = str(uuid.uuid4())[:8]
    clients[client_id] = ws
    nick = await ws.receive_text()
    nicks[client_id] = nick

    # отправляем клиенту его ID
    await ws.send_text(json.dumps({"type": "id", "id": client_id}))

    async def broadcast_list():
        data = json.dumps({"type": "list", "users": nicks})
        for c in clients.values():
            await c.send_text(data)

    await broadcast_list()

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            # передача сообщений выбранным пользователям
            if msg_type == "msg":
                targets = msg.get("to", [])
                data = msg.get("data")
                for t in targets:
                    if t in clients:
                        await clients[t].send_text(json.dumps({
                            "from": client_id,
                            "type": "msg",
                            "data": data
                        }))

            # передача публичного ключа для E2EE
            elif msg_type == "key":
                to = msg.get("to")
                if to in clients:
                    await clients[to].send_text(json.dumps({
                        "from": client_id,
                        "type": "key",
                        "key": msg["key"]
                    }))

            # обновляем список пользователей
            await broadcast_list()

    except:
        pass
    finally:
        clients.pop(client_id, None)
        nicks.pop(client_id, None)
        await broadcast_list()
