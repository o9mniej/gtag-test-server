from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import time
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# player_id -> player data
players: Dict[str, dict] = {}
LOCK = threading.Lock()

TIMEOUT = 8.0  # seconds until player is considered gone


def cleanup_loop():
    while True:
        time.sleep(2)
        now = time.time()

        with LOCK:
            dead = [
                pid for pid, pdata in players.items()
                if now - pdata["last_seen"] > TIMEOUT
            ]

            for pid in dead:
                name = players[pid]["name"]
                print(f"[LEAVE] {name} ({pid})")
                del players[pid]


threading.Thread(target=cleanup_loop, daemon=True).start()


@app.post("/sync/{player_id}")
async def sync(player_id: str, data: dict):
    now = time.time()

    with LOCK:
        is_new = player_id not in players

        # Extract name and color from the rig if present
        name = data.get("name", "Player")
        color = f"#{int(data.get('r', 1)*255):02x}{int(data.get('g',1)*255):02x}{int(data.get('b',1)*255):02x}"

        players[player_id] = {
            "name": name,
            "color": color,
            "rig": data,  # store the full RigNetData dict
            "last_seen": now
        }

    if is_new:
        print(f"[JOIN] {players[player_id]['name']} ({player_id})")
    else:
        print(f"[UPDATE] {players[player_id]['name']}")

    # return everyone except the caller
    with LOCK:
        others = {
            pid: pdata
            for pid, pdata in players.items()
            if pid != player_id
        }

    return {"players": others}

@app.get("/status")
async def status():
    now = time.time()
    with LOCK:
        return {
            "playerCount": len(players),
            "players": [
                {
                    "name": pdata["name"],
                    "color": pdata["color"],
                    "secondsAgo": round(now - pdata["last_seen"], 2),
                    "rig": pdata["rig"]  # <-- added rig info here
                }
                for pdata in players.values()
            ]
        }


@app.get("/")
async def root():
    return {
        "status": "Gray Server Running",
        "players": len(players)
    }

