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
                print(f"[LEAVE] {players[pid]['name']} ({pid})")
                del players[pid]


threading.Thread(target=cleanup_loop, daemon=True).start()


# -------------------------------
# POST = SEND YOUR DATA
# -------------------------------
@app.post("/sync/{player_id}")
async def sync_post(player_id: str, data: dict):
    now = time.time()

    with LOCK:
        is_new = player_id not in players

        name = data.get("name", "Player")

        players[player_id] = {
            "name": name,
            "rig": data,
            "last_seen": now
        }

    if is_new:
        print(f"[JOIN] {name} ({player_id})")

    return {"ok": True}


# -------------------------------
# GET = RECEIVE OTHER PLAYERS
# -------------------------------
@app.get("/sync/{player_id}")
async def sync_get(player_id: str):
    with LOCK:
        others = {
            pid: pdata["rig"]
            for pid, pdata in players.items()
            if pid != player_id
        }

    return {"players": others}


# -------------------------------
# DEBUG / STATUS
# -------------------------------
@app.get("/status")
async def status():
    now = time.time()
    with LOCK:
        return {
            "playerCount": len(players),
            "players": [
                {
                    "name": pdata["name"],
                    "secondsAgo": round(now - pdata["last_seen"], 2),
                    "rig": pdata["rig"]
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
