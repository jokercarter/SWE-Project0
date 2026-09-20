"""Ephemeral local multiplayer rooms for the Neon Rift Arena prototype.

The server owns rooms and relays only a deliberately small, validated game-state
surface. It has no database and disappears when the local server stops.
"""
import asyncio
import secrets
import time
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

from .main import app

MAPS = {
    'foundry': {'name': 'Foundry', 'accent': '#56e8ff', 'obstacles': [[190,128,100,42],[655,110,120,40],[405,305,152,44],[145,475,130,36],[670,470,100,45]]},
    'crossfire': {'name': 'Crossfire', 'accent': '#ff6b88', 'obstacles': [[390,90,180,35],[165,245,100,120],[695,245,100,120],[390,515,180,35],[435,230,90,180]]},
    'drift': {'name': 'Drift', 'accent': '#a58cff', 'obstacles': [[125,130,150,42],[685,130,150,42],[125,468,150,42],[685,468,150,42],[410,292,140,56]]},
}
WEAPONS = {'pulse': {'damage': 18, 'cooldown': .12}, 'scatter': {'damage': 12, 'cooldown': .5}, 'rail': {'damage': 46, 'cooldown': .9}, 'arc': {'damage': 8, 'cooldown': .07}}
UPGRADES = {'vitality', 'velocity', 'amplify'}

@dataclass
class Player:
    id: str
    name: str
    x: float
    y: float
    hue: str
    hp: int = 100
    weapon: str = 'pulse'
    upgrades: dict = field(default_factory=lambda: {'vitality': 0, 'velocity': 0, 'amplify': 0})
    score: int = 0
    deaths: int = 0
    last_seen: float = field(default_factory=time.time)

@dataclass
class Room:
    code: str
    map_id: str
    players: dict = field(default_factory=dict)
    sockets: dict = field(default_factory=dict)
    created: float = field(default_factory=time.time)

rooms: dict[str, Room] = {}
lock = asyncio.Lock()
colors = ['#56e8ff', '#ff6b88', '#a58cff', '#77ffc1', '#ffb86b', '#f7e66d']

def player_view(player: Player):
    return {'id': player.id, 'name': player.name, 'x': round(player.x, 1), 'y': round(player.y, 1), 'hue': player.hue, 'hp': player.hp, 'weapon': player.weapon, 'upgrades': player.upgrades, 'score': player.score, 'deaths': player.deaths}

def room_view(room: Room):
    return {'type': 'state', 'room': room.code, 'map': room.map_id, 'players': [player_view(p) for p in room.players.values()]}

def collides(map_id: str, x: float, y: float, radius: float = 16):
    if x < radius + 18 or x > 960 - radius - 18 or y < radius + 18 or y > 640 - radius - 18:
        return True
    return any(x + radius > ox and x - radius < ox + width and y + radius > oy and y - radius < oy + height
               for ox, oy, width, height in MAPS[map_id]['obstacles'])

async def broadcast(room: Room, message: dict):
    stale = []
    for player_id, socket in room.sockets.items():
        try:
            await socket.send_json(message)
        except Exception:
            stale.append(player_id)
    for player_id in stale:
        room.sockets.pop(player_id, None)
        room.players.pop(player_id, None)

@app.get('/api/arena/maps')
def arena_maps():
    return [{'id': key, 'name': value['name'], 'accent': value['accent']} for key, value in MAPS.items()]

@app.websocket('/ws/arena')
async def arena_socket(socket: WebSocket):
    await socket.accept()
    player = None
    room = None
    try:
        hello = await asyncio.wait_for(socket.receive_json(), timeout=12)
        if hello.get('type') != 'join':
            await socket.close(code=1008)
            return
        code = ''.join(c for c in str(hello.get('room', '')).upper() if c.isalnum())[:8] or secrets.token_hex(3).upper()
        name = ''.join(c for c in str(hello.get('name', 'Rifter')) if c.isalnum() or c in ' -_')[:18].strip() or 'Rifter'
        map_id = hello.get('map', 'foundry')
        if map_id not in MAPS:
            map_id = 'foundry'
        async with lock:
            room = rooms.get(code)
            if not room:
                room = rooms[code] = Room(code=code, map_id=map_id)
            if len(room.players) >= 12:
                await socket.send_json({'type': 'error', 'message': 'This room is full.'})
                await socket.close(code=1008)
                return
            player = Player(id=secrets.token_urlsafe(6), name=name, x=150 + len(room.players) * 70, y=170 + len(room.players) * 55, hue=colors[len(room.players) % len(colors)])
            room.players[player.id] = player
            room.sockets[player.id] = socket
        await socket.send_json({**room_view(room), 'type': 'welcome', 'id': player.id, 'maps': MAPS})
        await broadcast(room, room_view(room))
        while True:
            message = await socket.receive_json()
            if not isinstance(message, dict):
                continue
            player.last_seen = time.time()
            kind = message.get('type')
            if kind == 'move':
                x, y = message.get('x'), message.get('y')
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    x, y = max(34, min(926, x)), max(34, min(606, y))
                    if not collides(room.map_id, x, player.y):
                        player.x = x
                    if not collides(room.map_id, player.x, y):
                        player.y = y
            elif kind == 'weapon' and message.get('weapon') in WEAPONS:
                player.weapon = message['weapon']
            elif kind == 'upgrade' and message.get('upgrade') in UPGRADES:
                upgrade = message['upgrade']
                if player.score >= 200 and player.upgrades[upgrade] < 3:
                    player.score -= 200
                    player.upgrades[upgrade] += 1
                    if upgrade == 'vitality':
                        player.hp = min(160, player.hp + 25)
            elif kind == 'damage':
                target_id, damage = message.get('target'), message.get('damage')
                target = room.players.get(target_id)
                if target and target.id != player.id and isinstance(damage, (int, float)) and 0 < damage <= 60:
                    target.hp -= int(damage)
                    if target.hp <= 0:
                        target.deaths += 1
                        target.hp = 100 + target.upgrades['vitality'] * 20
                        target.x, target.y = 100 + secrets.randbelow(760), 90 + secrets.randbelow(460)
                        player.score += 100
                        await broadcast(room, {'type': 'event', 'kind': 'kill', 'payload': {'by': player.name, 'target': target.name}})
            elif kind == 'chat':
                content = ' '.join(str(message.get('content', '')).split())[:180]
                if content:
                    await broadcast(room, {'type': 'event', 'kind': 'chat', 'payload': {'name': player.name, 'content': content}})
                    continue
            elif kind == 'event':
                payload = message.get('payload', {})
                if isinstance(payload, dict):
                    await broadcast(room, {'type': 'event', 'from': player.id, 'kind': str(message.get('kind', 'shot'))[:16], 'payload': payload})
                    continue
            await broadcast(room, room_view(room))
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        if room and player:
            async with lock:
                room.players.pop(player.id, None)
                room.sockets.pop(player.id, None)
                if room.players:
                    await broadcast(room, room_view(room))
                else:
                    rooms.pop(room.code, None)
