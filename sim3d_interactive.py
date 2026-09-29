import asyncio
import collections
from contextlib import asynccontextmanager
import heapq
import json
import math
import random
import time
from typing import Dict, List, Optional, Set, Tuple

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

# ==============================================================================
# 1. WAREHOUSE GRID TOPOLOGY (24x24 Industrial Center)
# ==============================================================================
GRID_SIZE = 24

SHELVES: List[Tuple[int, int]] = [
    # Aisle A (Left Racks)
    (3, 4), (4, 4), (5, 4), (3, 5), (4, 5), (5, 5),
    (3, 8), (4, 8), (5, 8), (3, 9), (4, 9), (5, 9),
    (3, 14), (4, 14), (5, 14), (3, 15), (4, 15), (5, 15),
    (3, 18), (4, 18), (5, 18), (3, 19), (4, 19), (5, 19),
    # Aisle B (Right Racks)
    (18, 4), (19, 4), (20, 4), (18, 5), (19, 5), (20, 5),
    (18, 8), (19, 8), (20, 8), (18, 9), (19, 9), (20, 9),
    (18, 14), (19, 14), (20, 14), (18, 15), (19, 15), (20, 15),
    (18, 18), (19, 18), (20, 18), (18, 19), (19, 19), (20, 19),
    # Central Storage Racks
    (10, 8), (11, 8), (12, 8), (13, 8),
    (10, 9), (11, 9), (12, 9), (13, 9),
    (10, 14), (11, 14), (12, 14), (13, 14),
    (10, 15), (11, 15), (12, 15), (13, 15),
]
SHELVES_SET: Set[Tuple[int, int]] = set(SHELVES)

CHARGING_STATIONS: List[Tuple[int, int]] = [(1, 1), (22, 1), (1, 22), (22, 22)]
PICKUP_ZONES: List[Tuple[int, int]] = [(1, 10), (1, 11), (1, 12), (1, 13), (22, 10), (22, 11), (22, 12), (22, 13)]

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def get_accessible_neighbors(cell: Tuple[int, int], dynamic_obstacles: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
    x, y = cell
    neighbors = []
    for dx, dy in DIRECTIONS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            if (nx, ny) not in SHELVES_SET and (nx, ny) not in dynamic_obstacles:
                neighbors.append((nx, ny))
    return neighbors


def a_star_search(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    dynamic_obstacles: Optional[Set[Tuple[int, int]]] = None
) -> Optional[List[Tuple[int, int]]]:
    if dynamic_obstacles is None:
        dynamic_obstacles = set()

    if goal in SHELVES_SET or not (0 <= goal[0] < GRID_SIZE and 0 <= goal[1] < GRID_SIZE):
        candidates = []
        for dx, dy in DIRECTIONS:
            cx, cy = goal[0] + dx, goal[1] + dy
            if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE and (cx, cy) not in SHELVES_SET and (cx, cy) not in dynamic_obstacles:
                candidates.append((cx, cy))
        if candidates:
            goal = min(candidates, key=lambda c: abs(c[0] - start[0]) + abs(c[1] - start[1]))
        else:
            return None

    if start == goal:
        return [start]

    def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    frontier = []
    heapq.heappush(frontier, (0.0, start))
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    cost_so_far: Dict[Tuple[int, int], float] = {start: 0.0}

    found = False
    while frontier:
        _, current = heapq.heappop(frontier)

        if current == goal:
            found = True
            break

        for next_cell in get_accessible_neighbors(current, dynamic_obstacles):
            new_cost = cost_so_far[current] + 1.0
            if next_cell not in cost_so_far or new_cost < cost_so_far[next_cell]:
                cost_so_far[next_cell] = new_cost
                priority = new_cost + heuristic(goal, next_cell)
                heapq.heappush(frontier, (priority, next_cell))
                came_from[next_cell] = current

    if not found:
        return None

    curr = goal
    path = []
    while curr is not None:
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    return path


# ==============================================================================
# 2. AMR AGENT CLASS WITH 3D TELEMETRY & DYNAMIC AVOIDANCE
# ==============================================================================
class AMR:
    def __init__(self, bot_id: int, name: str, x: float, y: float, color: str):
        self.id = bot_id
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.heading = 0.0
        self.speed = 0.16
        self.battery = random.uniform(88.0, 98.0)
        self.cpu_load = random.uniform(22.0, 35.0)
        self.color = color
        self.lidar_range = 2.2
        self.trail: collections.deque = collections.deque(maxlen=16)

        self.status = "IDLE"
        self.has_cargo = False
        self.target_x = float(x)
        self.target_y = float(y)
        self.goal_cell: Tuple[int, int] = (int(round(x)), int(round(y)))
        self.path: List[Tuple[int, int]] = []
        self.path_index = 0
        self.wait_counter = 0
        self.missions_completed = 0
        self.distance_traveled = 0.0

    def get_grid_pos(self) -> Tuple[int, int]:
        return int(round(self.x)), int(round(self.y))

    def set_target(self, goal: Tuple[int, int], dynamic_obstacles: Optional[Set[Tuple[int, int]]] = None) -> bool:
        start_cell = self.get_grid_pos()
        planned = a_star_search(start_cell, goal, dynamic_obstacles)
        if planned and len(planned) > 0:
            self.goal_cell = goal
            self.target_x, self.target_y = float(goal[0]), float(goal[1])
            self.path = planned
            self.path_index = 1 if len(planned) > 1 and planned[0] == start_cell else 0
            return True
        return False

    def assign_next_mission(self, engine: "SimulationEngine"):
        if self.battery < 22.0:
            nearest_station = min(
                CHARGING_STATIONS,
                key=lambda s: abs(s[0] - self.x) + abs(s[1] - self.y)
            )
            self.status = "RETURNING_TO_CHARGER"
            self.set_target(nearest_station, engine.active_hazards)
            engine.log_event(f"{self.name}: Low battery ({self.battery:.1f}%) - Rerouting to Dock {nearest_station}")
            return

        if not self.has_cargo:
            zone = random.choice(PICKUP_ZONES)
            self.status = "EN_ROUTE_PICKUP"
            self.set_target(zone, engine.active_hazards)
        else:
            shelf = random.choice(SHELVES)
            candidates = []
            for dx, dy in DIRECTIONS:
                cx, cy = shelf[0] + dx, shelf[1] + dy
                if 0 <= cx < GRID_SIZE and 0 <= cy < GRID_SIZE and (cx, cy) not in SHELVES_SET and (cx, cy) not in engine.active_hazards:
                    candidates.append((cx, cy))
            target_cell = random.choice(candidates) if candidates else random.choice(PICKUP_ZONES)
            self.status = "TRANSIT_DELIVERY"
            self.set_target(target_cell, engine.active_hazards)

    def step(self, fleet: List["AMR"], engine: "SimulationEngine"):
        self.trail.append((round(self.x, 2), round(self.y, 2)))

        if self.battery <= 0.0:
            self.status = "CRITICAL_POWER_HALT"
            return

        gx, gy = self.get_grid_pos()
        if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
            engine.heatmap_grid[gx][gy] += 1

        # 1. Charging Station Dwell
        if self.status == "CHARGING":
            self.battery = min(100.0, self.battery + 0.45)
            self.cpu_load = max(12.0, self.cpu_load - 0.4)
            if self.battery >= 96.0:
                self.status = "IDLE"
                engine.log_event(f"{self.name}: Fully recharged (96%). Resuming autonomous missions.")
                self.assign_next_mission(engine)
            return

        # 2. Loading / Unloading Dwell
        if self.status in ("LOADING", "UNLOADING"):
            self.wait_counter -= 1
            if self.wait_counter <= 0:
                if self.status == "LOADING":
                    self.has_cargo = True
                    engine.log_event(f"{self.name}: Pallet loaded. In transit to storage rack.")
                    self.assign_next_mission(engine)
                elif self.status == "UNLOADING":
                    self.has_cargo = False
                    self.missions_completed += 1
                    engine.stats["missions_completed"] += 1
                    engine.log_event(f"{self.name}: Pallet delivered to Bay ({int(self.x)}, {int(self.y)}).")
                    self.assign_next_mission(engine)
            return

        # 3. Path Completion & Mission Transition
        if self.status == "IDLE" or not self.path or self.path_index >= len(self.path):
            curr_pos = (int(round(self.x)), int(round(self.y)))
            if self.status == "RETURNING_TO_CHARGER" and curr_pos in CHARGING_STATIONS:
                self.status = "CHARGING"
                engine.log_event(f"{self.name}: Docked at high-rate inductive charging dock.")
                return
            elif self.status == "EN_ROUTE_PICKUP" and curr_pos in PICKUP_ZONES:
                self.status = "LOADING"
                self.wait_counter = 16
                return
            elif self.status == "TRANSIT_DELIVERY":
                self.status = "UNLOADING"
                self.wait_counter = 16
                return
            else:
                self.assign_next_mission(engine)
                if not self.path or self.path_index >= len(self.path):
                    return

        # 4. Check If Active Hazards Block Planned Path
        if engine.active_hazards:
            for wp in self.path[self.path_index:]:
                if wp in engine.active_hazards:
                    engine.log_event(f"{self.name}: Obstacle detected in route path. Engaging dynamic A* replanning.")
                    all_obs = set(SHELVES_SET).union(engine.active_hazards)
                    self.set_target(self.goal_cell, dynamic_obstacles=all_obs)
                    break

        # 5. Waypoint Trajectory Step
        target_wp = self.path[self.path_index]
        tx, ty = float(target_wp[0]), float(target_wp[1])
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist < 0.15:
            self.path_index += 1
            if self.path_index >= len(self.path):
                return
            target_wp = self.path[self.path_index]
            tx, ty = float(target_wp[0]), float(target_wp[1])
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)

        target_angle = math.atan2(dy, dx)
        self.heading = target_angle
        step_speed = self.speed * engine.speed_multiplier
        vx = (dx / dist) * step_speed if dist > 0 else 0
        vy = (dy / dist) * step_speed if dist > 0 else 0

        predicted_x = self.x + vx * 2.5
        predicted_y = self.y + vy * 2.5

        # 6. Decentralized Priority Conflict Resolution
        yield_movement = False
        for peer in fleet:
            if peer.id == self.id or peer.status in ("CHARGING", "IDLE"):
                continue

            peer_dist = math.hypot(self.x - peer.x, self.y - peer.y)
            pred_peer_dist = math.hypot(predicted_x - peer.x, predicted_y - peer.y)

            if peer_dist < self.lidar_range or pred_peer_dist < 1.3:
                self_prio = (2 if self.has_cargo else 0) + (1 if self.status == "RETURNING_TO_CHARGER" else 0) - (self.id * 0.01)
                peer_prio = (2 if peer.has_cargo else 0) + (1 if peer.status == "RETURNING_TO_CHARGER" else 0) - (peer.id * 0.01)

                if self_prio < peer_prio:
                    yield_movement = True
                    self.wait_counter += 1
                    if self.wait_counter == 1:
                        engine.stats["conflicts_resolved"] += 1
                        engine.log_event(
                            f"Conflict Resolution: {self.name} yielded right-of-way to {peer.name} at junction ({int(round(self.x))}, {int(round(self.y))})"
                        )

                    if self.wait_counter > 20:
                        obs = set(SHELVES_SET).union(engine.active_hazards)
                        obs.add(peer.get_grid_pos())
                        recalc = self.set_target(self.goal_cell, dynamic_obstacles=obs)
                        if recalc:
                            engine.log_event(f"{self.name}: Recalculating dynamic alternate A* corridor.")
                        self.wait_counter = 0
                    break

        if yield_movement:
            self.cpu_load = min(88.0, self.cpu_load + 0.3)
            return

        self.wait_counter = max(0, self.wait_counter - 1)

        # 7. Apply Movement & Telemetry
        self.x += vx
        self.y += vy
        self.distance_traveled += math.hypot(vx, vy)
        engine.stats["total_distance"] += math.hypot(vx, vy)

        drain_rate = 0.0035 * (1.4 if self.has_cargo else 1.0) * engine.speed_multiplier
        self.battery = max(0.0, self.battery - drain_rate)
        self.cpu_load = min(85.0, max(18.0, self.cpu_load + random.uniform(-1.2, 1.4)))


# ==============================================================================
# 3. SIMULATION ENGINE MANAGER
# ==============================================================================
class SimulationEngine:
    def __init__(self):
        self.fleet: List[AMR] = [
            AMR(0, "AMR-A1 (UnitAlpha)", 2.0, 2.0, "#00f0ff"),
            AMR(1, "AMR-B2 (UnitBravo)", 21.0, 2.0, "#ff0055"),
            AMR(2, "AMR-C3 (UnitCharlie)", 2.0, 21.0, "#00ff88"),
            AMR(3, "AMR-D4 (UnitDelta)", 21.0, 21.0, "#ffaa00"),
        ]
        self.e_stop: bool = False
        self.speed_multiplier: float = 1.0
        self.event_logs: collections.deque = collections.deque(maxlen=50)
        self.stats = {
            "conflicts_resolved": 42,
            "missions_completed": 128,
            "total_distance": 1420.5,
        }
        self.active_hazards: Set[Tuple[int, int]] = set()
        self.heatmap_grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.active_connections: List[WebSocket] = []
        self._running = False
        self.log_event("FleetGuard-AI Industrial 3D Digital Twin Initialized.")
        self.log_event("P2P Telemetry Stream Active. 4 Units Online.")

    def log_event(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        self.event_logs.append(f"[{timestamp}] {msg}")

    def trigger_headon_scenario(self):
        self.log_event("SIMULATION SCENARIO: Direct Head-On Aisle Conflict initiated.")
        b0 = self.fleet[0]
        b1 = self.fleet[1]

        b0.x, b0.y = 8.0, 12.0
        b0.has_cargo = True
        b0.set_target((16, 12), self.active_hazards)

        b1.x, b1.y = 16.0, 12.0
        b1.has_cargo = False
        b1.set_target((8, 12), self.active_hazards)

    def toggle_hazard(self, gx: int, gy: int):
        if (gx, gy) in SHELVES_SET:
            return
        cell = (gx, gy)
        if cell in self.active_hazards:
            self.active_hazards.remove(cell)
            self.log_event(f"HAZARD CLEARED: Aisle corridor cell ({gx}, {gy}) restored to service.")
        else:
            self.active_hazards.add(cell)
            self.log_event(f"HAZARD DEPLOYED: Obstacle barrier placed at ({gx}, {gy}). Active fleet rerouting.")

    def step(self):
        if not self.e_stop:
            for bot in self.fleet:
                bot.step(self.fleet, self)

    def get_snapshot(self) -> dict:
        return {
            "e_stop": self.e_stop,
            "speed_multiplier": self.speed_multiplier,
            "stats": {
                "conflicts_resolved": self.stats["conflicts_resolved"],
                "missions_completed": self.stats["missions_completed"],
                "total_distance": round(self.stats["total_distance"], 1),
                "fleet_size": len(self.fleet),
            },
            "logs": list(self.event_logs),
            "shelves": SHELVES,
            "charging": CHARGING_STATIONS,
            "stations": PICKUP_ZONES,
            "hazards": list(self.active_hazards),
            "heatmap": self.heatmap_grid,
            "robots": [
                {
                    "id": b.id,
                    "name": b.name,
                    "x": round(b.x, 3),
                    "y": round(b.y, 3),
                    "heading": round(b.heading, 3),
                    "target_x": round(b.target_x, 1),
                    "target_y": round(b.target_y, 1),
                    "battery": round(b.battery, 1),
                    "cpu_load": round(b.cpu_load, 1),
                    "status": b.status,
                    "has_cargo": b.has_cargo,
                    "color": b.color,
                    "lidar_range": b.lidar_range,
                    "trail": list(b.trail),
                    "path": b.path[b.path_index:] if b.path else [],
                    "missions": b.missions_completed
                }
                for b in self.fleet
            ]
        }

    async def run_loop(self):
        self._running = True
        while self._running:
            start_t = time.time()
            self.step()

            if self.active_connections:
                payload = json.dumps(self.get_snapshot())
                dead = []
                for ws in self.active_connections:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        dead.append(ws)
                for d in dead:
                    if d in self.active_connections:
                        self.active_connections.remove(d)

            elapsed = time.time() - start_t
            await asyncio.sleep(max(0.01, 0.04 - elapsed))


engine = SimulationEngine()


# ==============================================================================
# 4. LIFESPAN CONTEXT & FASTAPI APP
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(engine.run_loop())
    yield
    engine._running = False
    task.cancel()


app = FastAPI(title="FleetGuard-AI-3D", lifespan=lifespan)


# ==============================================================================
# 5. PROFESSIONAL HIGH-TECH 3D MISSION CONTROL INTERFACE
# ==============================================================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>FleetGuard-AI // 3D Autonomous Fleet Command</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #050811;
            --panel-bg: rgba(11, 18, 28, 0.92);
            --panel-card: #0d1726;
            --border-dim: #1a273a;
            --border-glow: #2d4566;
            --accent-cyan: #00f0ff;
            --accent-red: #ff0055;
            --accent-green: #00ff88;
            --accent-amber: #ffaa00;
            --accent-purple: #a855f7;
            --text-main: #f1f5f9;
            --text-muted: #64748b;
            --text-dim: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background: var(--bg-deep);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', sans-serif;
            height: 100vh;
            overflow: hidden;
            user-select: none;
        }

        /* Top Command Header */
        #topbar {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 64px;
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-dim);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            z-index: 100;
        }

        .brand-cluster {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-icon {
            width: 34px;
            height: 34px;
            border-radius: 6px;
            background: rgba(0, 240, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--accent-cyan);
            box-shadow: 0 0 16px rgba(0, 240, 255, 0.18);
        }

        .brand-text {
            display: flex;
            flex-direction: column;
        }

        .brand-name {
            font-weight: 800;
            font-size: 1.05rem;
            letter-spacing: 1.2px;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .brand-badge {
            background: rgba(0, 240, 255, 0.1);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 240, 255, 0.3);
            font-size: 0.62rem;
            padding: 2px 7px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .brand-sub {
            font-size: 0.64rem;
            color: var(--text-muted);
            letter-spacing: 0.6px;
            font-weight: 600;
        }

        /* KPI Group */
        .kpi-row {
            display: flex;
            align-items: center;
            gap: 28px;
        }

        .kpi-block {
            display: flex;
            flex-direction: column;
        }

        .kpi-label {
            font-size: 0.62rem;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }

        .kpi-val {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.92rem;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .pulse-indicator {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
            animation: pulseDot 1.8s infinite;
        }

        @keyframes pulseDot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.35; transform: scale(1.3); }
        }

        /* Action Toolbar */
        .controls-deck {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn {
            background: var(--panel-card);
            border: 1px solid var(--border-dim);
            color: var(--text-main);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            font-weight: 600;
            padding: 7px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn svg {
            width: 13px;
            height: 13px;
            stroke-width: 2.2;
        }

        .btn:hover {
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
            background: rgba(0, 240, 255, 0.08);
        }

        .btn.active {
            background: rgba(0, 240, 255, 0.16);
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
            box-shadow: 0 0 12px rgba(0, 240, 255, 0.2);
        }

        .btn-hazard.active {
            background: rgba(255, 0, 85, 0.2);
            border-color: var(--accent-red);
            color: var(--accent-red);
            box-shadow: 0 0 12px rgba(255, 0, 85, 0.3);
        }

        .btn-estop {
            background: rgba(255, 0, 85, 0.16);
            border: 1px solid var(--accent-red);
            color: #fff;
            font-weight: 800;
            letter-spacing: 0.6px;
            padding: 7px 15px;
        }

        .btn-estop:hover {
            background: var(--accent-red);
            box-shadow: 0 0 16px rgba(255, 0, 85, 0.5);
        }

        .btn-estop.active {
            background: var(--accent-red);
            animation: estopFlash 0.7s infinite alternate;
        }

        @keyframes estopFlash {
            0% { opacity: 1; }
            100% { opacity: 0.55; }
        }

        /* Camera Control Segmented Bar */
        #cameraToolbar {
            position: absolute;
            top: 76px;
            left: 24px;
            background: var(--panel-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-dim);
            border-radius: 6px;
            display: flex;
            padding: 3px;
            gap: 4px;
            z-index: 100;
        }

        .cam-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            font-weight: 700;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .cam-btn:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.05);
        }

        .cam-btn.active {
            background: rgba(0, 240, 255, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 240, 255, 0.3);
        }

        /* Floating Notice Pill */
        #hudNotice {
            position: absolute;
            top: 78px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(255, 0, 85, 0.18);
            border: 1px solid var(--accent-red);
            color: #fff;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-family: 'JetBrains Mono', monospace;
            display: none;
            z-index: 100;
            backdrop-filter: blur(8px);
            box-shadow: 0 0 16px rgba(255, 0, 85, 0.35);
        }

        /* Telemetry & Audit Sidebar */
        #sidebar {
            position: absolute;
            right: 20px;
            top: 76px;
            bottom: 20px;
            width: 370px;
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-dim);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            z-index: 100;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        }

        .sidebar-header {
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--border-dim);
            font-size: 0.68rem;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.8px;
            text-transform: uppercase;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        #botCards {
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            overflow-y: auto;
            flex: 1;
        }

        .bot-card {
            background: var(--panel-card);
            border: 1px solid var(--border-dim);
            border-left: 3px solid #334155;
            border-radius: 6px;
            padding: 11px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .bot-card:hover {
            border-color: var(--border-glow);
            transform: translateY(-1px);
        }

        .bot-card.selected {
            border-color: var(--accent-cyan);
            background: #112035;
            box-shadow: 0 0 16px rgba(0, 240, 255, 0.15);
        }

        .bot-card-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }

        .bot-title {
            font-weight: 700;
            font-size: 0.82rem;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 7px;
        }

        .bot-status-tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.62rem;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: 700;
        }

        .bot-grid-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            color: var(--text-dim);
            margin-bottom: 6px;
        }

        .stat-bar-track {
            width: 100%;
            height: 4px;
            background: #192433;
            border-radius: 2px;
            overflow: hidden;
        }

        .stat-bar-fill {
            height: 100%;
            transition: width 0.3s ease;
        }

        /* Terminal Feed */
        #logPanel {
            border-top: 1px solid var(--border-dim);
            height: 160px;
            display: flex;
            flex-direction: column;
            background: #060a10;
        }

        #terminalFeed {
            flex: 1;
            padding: 8px 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.64rem;
            line-height: 1.45;
            color: #94a3b8;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        .log-entry.warn { color: var(--accent-amber); }
        .log-entry.cyan { color: var(--accent-cyan); }
        .log-entry.green { color: var(--accent-green); }

        /* Bottom Floor HUD Legend */
        #legendOverlay {
            position: absolute;
            bottom: 20px;
            left: 24px;
            background: var(--panel-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-dim);
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 0.68rem;
            display: flex;
            gap: 16px;
            font-family: 'JetBrains Mono', monospace;
            pointer-events: none;
            z-index: 100;
        }

        .legend-chip {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .legend-box {
            width: 9px;
            height: 9px;
            border-radius: 2px;
        }

        #canvas3d {
            width: 100%;
            height: 100%;
            display: block;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <!-- Top Command Deck -->
    <header id="topbar">
        <div class="brand-cluster">
            <div class="brand-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <rect x="2" y="2" width="20" height="20" rx="4"></rect>
                    <path d="M12 6v12M6 12h12"></path>
                    <circle cx="12" cy="12" r="3" fill="#00f0ff"></circle>
                </svg>
            </div>
            <div class="brand-text">
                <div class="brand-name">
                    FLEETGUARD-AI
                    <span class="brand-badge">MAPF 3D DIGITAL TWIN</span>
                </div>
                <div class="brand-sub">Autonomous Decentralized CBS Mission Control</div>
            </div>
        </div>

        <div class="kpi-row">
            <div class="kpi-block">
                <span class="kpi-label">P2P Mesh Network</span>
                <span class="kpi-val" style="color:var(--accent-green);"><span class="pulse-indicator"></span> 802.11s // ONLINE</span>
            </div>
            <div class="kpi-block">
                <span class="kpi-label">Deadlocks Averted</span>
                <span class="kpi-val" style="color:var(--accent-cyan);" id="conflictCount">42</span>
            </div>
            <div class="kpi-block">
                <span class="kpi-label">Missions Delivered</span>
                <span class="kpi-val" style="color:var(--accent-green);" id="missionsCount">128</span>
            </div>
            <div class="kpi-block">
                <span class="kpi-label">Edge Inference</span>
                <span class="kpi-val" style="color:#fff;">11.2 ms</span>
            </div>
        </div>

        <div class="controls-deck">
            <button class="btn btn-hazard" id="btnHazard" title="Deploy dynamic obstacle to test real-time A* rerouting">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                DYNAMIC HAZARD
            </button>
            <button class="btn" id="btnHeadOn" title="Trigger head-on conflict scenario in center aisle">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="16 3 21 3 21 8"></polyline><line x1="4" y1="20" x2="21" y2="3"></line><polyline points="21 16 21 21 16 21"></polyline><line x1="15" y1="15" x2="21" y2="21"></line><line x1="4" y1="4" x2="9" y2="9"></line></svg>
                HEAD-ON SCENARIO
            </button>
            <button class="btn" id="btnHeatmap" title="Toggle traffic occupancy density heatmap">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                HEATMAP
            </button>
            <button class="btn" id="btnExportCSV" title="Export incident and telemetry audit logs">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                EXPORT CSV
            </button>
            <button class="btn btn-estop" id="btnEStop" title="Immediate fleet-wide emergency stop">
                EMERGENCY STOP
            </button>
        </div>
    </header>

    <!-- Camera Perspective Segmented Controls -->
    <div id="cameraToolbar">
        <button class="cam-btn active" id="camIso" onclick="setCameraView('iso')">ISOMETRIC</button>
        <button class="cam-btn" id="camTop" onclick="setCameraView('top')">TOP-DOWN 2D</button>
        <button class="cam-btn" id="camChase" onclick="setCameraView('chase')">CHASE CAM</button>
    </div>

    <!-- Active Hazard Notice Pill -->
    <div id="hudNotice">INTERACTIVE HAZARD MODE: CLICK OPEN AISLE CELL TO SPAWN / REMOVE BARRIER</div>

    <!-- Telemetry Sidebar -->
    <aside id="sidebar">
        <div class="sidebar-header">
            <span>Fleet Telemetry (25Hz)</span>
            <span style="font-family:'JetBrains Mono', monospace; color:var(--accent-cyan);" id="fleetStatusText">CBS ACTIVE</span>
        </div>
        <div id="botCards"></div>
        <div id="logPanel">
            <div class="sidebar-header" style="background:#090e16; border-top:1px solid var(--border-dim);">
                <span>Audit & Incident Stream</span>
                <span style="font-family:'JetBrains Mono', monospace; color:var(--accent-green);">LIVE</span>
            </div>
            <div id="terminalFeed"></div>
        </div>
    </aside>

    <!-- Map Legend -->
    <div id="legendOverlay">
        <div class="legend-chip"><div class="legend-box" style="background:#1a2736; border: 1px solid #2d4158;"></div> Storage Racks</div>
        <div class="legend-chip"><div class="legend-box" style="background:#0284c7;"></div> Conveyor In/Out Bays</div>
        <div class="legend-chip"><div class="legend-box" style="background:#15803d; border: 1px solid #22c55e;"></div> Inductive Charger</div>
        <div class="legend-chip"><div class="legend-box" style="background:var(--accent-amber);"></div> Cargo Pallet</div>
        <div class="legend-chip"><div class="legend-box" style="background:var(--accent-red);"></div> Safety Barrier</div>
    </div>

    <!-- 3D Canvas -->
    <canvas id="canvas3d"></canvas>

    <script>
        let hazardMode = false;
        let heatmapMode = false;
        let selectedBotId = 0;
        let cameraMode = 'iso';
        let latestData = null;
        let ws;

        // Scene, Camera, Renderer Setup
        const canvas = document.getElementById("canvas3d");
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x050811);
        scene.fog = new THREE.FogExp2(0x050811, 0.015);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(-8, 22, 36);

        const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.target.set(12, 0, 12);
        controls.enableDamping = true;
        controls.dampingFactor = 0.06;

        // Lighting Architecture
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.55);
        scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0xdff4ff, 0.95);
        dirLight.position.set(12, 38, 12);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        scene.add(dirLight);

        // Floor Blueprint with Industrial Border
        const floorGeo = new THREE.PlaneGeometry(26, 26);
        const floorMat = new THREE.MeshStandardMaterial({ color: 0x080e18, roughness: 0.8, metalness: 0.25 });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.set(12, 0, 12);
        floor.receiveShadow = true;
        scene.add(floor);

        const gridHelper = new THREE.GridHelper(24, 24, 0x00f0ff, 0x141f2d);
        gridHelper.position.set(12, 0.01, 12);
        scene.add(gridHelper);

        // Heatmap Alpha Tiles Grid
        const heatTiles = [];
        const heatGeo = new THREE.PlaneGeometry(0.95, 0.95);
        for (let x = 0; x < 24; x++) {
            heatTiles[x] = [];
            for (let y = 0; y < 24; y++) {
                const hMat = new THREE.MeshBasicMaterial({ color: 0xff3b30, transparent: true, opacity: 0.0 });
                const hMesh = new THREE.Mesh(heatGeo, hMat);
                hMesh.rotation.x = -Math.PI / 2;
                hMesh.position.set(x + 0.5, 0.02, y + 0.5);
                scene.add(hMesh);
                heatTiles[x][y] = hMesh;
            }
        }

        // Storage Racks & Pallet Boxes
        const rackGeo = new THREE.BoxGeometry(0.85, 2.2, 0.85);
        const rackMat = new THREE.MeshStandardMaterial({ color: 0x131f2d, roughness: 0.5, metalness: 0.6 });
        const boxGeo = new THREE.BoxGeometry(0.65, 0.45, 0.65);
        const boxMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.7 });

        function buildRack(x, z) {
            const group = new THREE.Group();
            const r = new THREE.Mesh(rackGeo, rackMat);
            r.position.y = 1.1;
            r.castShadow = true;
            r.receiveShadow = true;
            group.add(r);

            const b1 = new THREE.Mesh(boxGeo, boxMat);
            b1.position.y = 0.75;
            group.add(b1);

            const b2 = new THREE.Mesh(boxGeo, boxMat);
            b2.position.y = 1.55;
            group.add(b2);

            group.position.set(x + 0.5, 0, z + 0.5);
            scene.add(group);
        }

        // Charging Bays Ground Plates
        const chargerGeo = new THREE.PlaneGeometry(0.85, 0.85);
        const chargerMat = new THREE.MeshBasicMaterial({ color: 0x15803d });
        function buildCharger(x, z) {
            const mesh = new THREE.Mesh(chargerGeo, chargerMat);
            mesh.rotation.x = -Math.PI / 2;
            mesh.position.set(x + 0.5, 0.015, z + 0.5);
            scene.add(mesh);
        }

        // Conveyor Pickup Bays Plates
        const stationGeo = new THREE.PlaneGeometry(0.85, 0.85);
        const stationMat = new THREE.MeshBasicMaterial({ color: 0x0284c7 });
        function buildStation(x, z) {
            const mesh = new THREE.Mesh(stationGeo, stationMat);
            mesh.rotation.x = -Math.PI / 2;
            mesh.position.set(x + 0.5, 0.015, z + 0.5);
            scene.add(mesh);
        }

        // Dynamic Hazard Barrier Meshes
        const hazardMeshes = {};
        function spawnHazardBarrier(x, z) {
            const group = new THREE.Group();
            const coneGeo = new THREE.ConeGeometry(0.32, 0.85, 16);
            const coneMat = new THREE.MeshStandardMaterial({ color: 0xff0055, emissive: 0xff0055, emissiveIntensity: 0.4 });
            const cone = new THREE.Mesh(coneGeo, coneMat);
            cone.position.y = 0.42;
            cone.castShadow = true;
            group.add(cone);

            // Glowing Danger Perimeter Ring
            const ringGeo = new THREE.RingGeometry(0.48, 0.54, 24);
            const ringMat = new THREE.MeshBasicMaterial({ color: 0xff0055, side: THREE.DoubleSide });
            const ring = new THREE.Mesh(ringGeo, ringMat);
            ring.rotation.x = Math.PI / 2;
            ring.position.y = 0.02;
            group.add(ring);

            group.position.set(x + 0.5, 0, z + 0.5);
            scene.add(group);
            hazardMeshes[`${x},${z}`] = group;
        }

        // AMR 3D Model Constructor
        const botMeshes = {};
        const pathLineMeshes = {};

        function createAMRMesh(colorHex) {
            const group = new THREE.Group();

            // Lower Cylindrical Chassis Base
            const baseGeo = new THREE.CylinderGeometry(0.42, 0.44, 0.22, 24);
            const baseMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.3, metalness: 0.7 });
            const base = new THREE.Mesh(baseGeo, baseMat);
            base.position.y = 0.15;
            base.castShadow = true;
            group.add(base);

            // LED Status Collar
            const bandGeo = new THREE.CylinderGeometry(0.441, 0.441, 0.05, 24);
            const bandMat = new THREE.MeshBasicMaterial({ color: parseInt(colorHex.replace("#", "0x")) });
            const band = new THREE.Mesh(bandGeo, bandMat);
            band.position.y = 0.18;
            group.add(band);

            // LiDAR Turret
            const lidarGeo = new THREE.CylinderGeometry(0.09, 0.09, 0.12, 16);
            const lidarMat = new THREE.MeshStandardMaterial({ color: 0x00f0ff, emissive: 0x00f0ff, emissiveIntensity: 0.6 });
            const lidar = new THREE.Mesh(lidarGeo, lidarMat);
            lidar.position.set(0.2, 0.3, 0);
            group.add(lidar);

            // Cargo Pallet Container
            const cargoGeo = new THREE.BoxGeometry(0.48, 0.3, 0.48);
            const cargoMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.8 });
            const cargo = new THREE.Mesh(cargoGeo, cargoMat);
            cargo.position.y = 0.42;
            cargo.name = "cargo";
            cargo.castShadow = true;
            group.add(cargo);

            // LiDAR Perimeter Ring
            const ringGeo = new THREE.RingGeometry(1.9, 1.96, 32);
            const ringMat = new THREE.MeshBasicMaterial({
                color: parseInt(colorHex.replace("#", "0x")),
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.35
            });
            const ring = new THREE.Mesh(ringGeo, ringMat);
            ring.rotation.x = Math.PI / 2;
            ring.position.y = 0.03;
            group.add(ring);

            return group;
        }

        // Raycasting for Floor Interaction
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        window.addEventListener("click", (evt) => {
            if (!hazardMode) return;
            mouse.x = (evt.clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(evt.clientY / window.innerHeight) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);

            const intersects = raycaster.intersectObject(floor);
            if (intersects.length > 0) {
                const pt = intersects[0].point;
                const gx = Math.floor(pt.x);
                const gy = Math.floor(pt.z);
                if (gx >= 0 && gx < 24 && gy >= 0 && gy < 24) {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ action: "toggle_hazard", x: gx, y: gy }));
                    }
                }
            }
        });

        // WebSocket Connection
        let infrastructureBuilt = false;
        function connectWS() {
            ws = new WebSocket(`ws://${location.host}/ws`);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                latestData = data;

                if (!infrastructureBuilt) {
                    data.shelves.forEach(([x, y]) => buildRack(x, y));
                    data.charging.forEach(([x, y]) => buildCharger(x, y));
                    data.stations.forEach(([x, y]) => buildStation(x, y));
                    infrastructureBuilt = true;
                }

                // Update Dynamic Obstacles
                Object.keys(hazardMeshes).forEach(k => {
                    const [hx, hy] = k.split(",").map(Number);
                    if (!data.hazards.some(([x, y]) => x === hx && y === hy)) {
                        scene.remove(hazardMeshes[k]);
                        delete hazardMeshes[k];
                    }
                });
                data.hazards.forEach(([hx, hy]) => {
                    if (!hazardMeshes[`${hx},${hy}`]) spawnHazardBarrier(hx, hy);
                });

                // Update Heatmap Opacity
                if (heatmapMode) {
                    let maxHits = 1;
                    for (let x = 0; x < 24; x++) {
                        for (let y = 0; y < 24; y++) {
                            if (data.heatmap[x][y] > maxHits) maxHits = data.heatmap[x][y];
                        }
                    }
                    for (let x = 0; x < 24; x++) {
                        for (let y = 0; y < 24; y++) {
                            const val = data.heatmap[x][y] / maxHits;
                            heatTiles[x][y].material.opacity = Math.min(0.7, val * 1.5);
                        }
                    }
                } else {
                    for (let x = 0; x < 24; x++) {
                        for (let y = 0; y < 24; y++) {
                            heatTiles[x][y].material.opacity = 0.0;
                        }
                    }
                }

                // Update AMRs and Planned 3D Path Vectors
                let cardsHtml = "";
                data.robots.forEach(bot => {
                    if (!botMeshes[bot.id]) {
                        const mesh = createAMRMesh(bot.color);
                        scene.add(mesh);
                        botMeshes[bot.id] = mesh;
                    }
                    const m = botMeshes[bot.id];
                    m.position.x = bot.x + 0.5;
                    m.position.z = bot.y + 0.5;
                    m.rotation.y = -bot.heading;

                    const cargo = m.getObjectByName("cargo");
                    if (cargo) cargo.visible = bot.has_cargo;

                    // Draw Planned 3D Waypoint Path Trajectory
                    if (pathLineMeshes[bot.id]) {
                        scene.remove(pathLineMeshes[bot.id]);
                        delete pathLineMeshes[bot.id];
                    }
                    if (bot.path && bot.path.length > 0) {
                        const points = [new THREE.Vector3(bot.x + 0.5, 0.05, bot.y + 0.5)];
                        bot.path.forEach(([wx, wy]) => points.push(new THREE.Vector3(wx + 0.5, 0.05, wy + 0.5)));
                        const pathGeo = new THREE.BufferGeometry().setFromPoints(points);
                        const pathMat = new THREE.LineBasicMaterial({
                            color: parseInt(bot.color.replace("#", "0x")),
                            transparent: true,
                            opacity: 0.65
                        });
                        const line = new THREE.Line(pathGeo, pathMat);
                        scene.add(line);
                        pathLineMeshes[bot.id] = line;
                    }

                    // Telemetry Card
                    const isSelected = (bot.id === selectedBotId);
                    let tagBg = "rgba(148, 163, 184, 0.15)";
                    let tagColor = "var(--text-dim)";
                    if (bot.status === "TRANSIT_DELIVERY" || bot.status === "EN_ROUTE_PICKUP") {
                        tagBg = "rgba(0, 240, 255, 0.15)"; tagColor = "var(--accent-cyan)";
                    } else if (bot.status === "CHARGING") {
                        tagBg = "rgba(0, 255, 136, 0.15)"; tagColor = "var(--accent-green)";
                    } else if (bot.status === "RETURNING_TO_CHARGER") {
                        tagBg = "rgba(255, 170, 0, 0.15)"; tagColor = "var(--accent-amber)";
                    }

                    cardsHtml += `
                        <div class="bot-card ${isSelected ? 'selected' : ''}" onclick="selectBot(${bot.id})" style="border-left-color:${bot.color}">
                            <div class="bot-card-head">
                                <span class="bot-title">
                                    <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:${bot.color}"></span>
                                    ${bot.name}
                                    ${bot.has_cargo ? '<span style="font-size:0.6rem; color:var(--accent-amber);">[CARGO]</span>' : ''}
                                </span>
                                <span class="bot-status-tag" style="background:${tagBg}; color:${tagColor}">${bot.status}</span>
                            </div>
                            <div class="bot-grid-metrics">
                                <div>POS: [${bot.x.toFixed(1)}, ${bot.y.toFixed(1)}]</div>
                                <div>CPU: ${bot.cpu_load.toFixed(0)}% (Edge)</div>
                                <div>GOAL: [${bot.target_x.toFixed(0)}, ${bot.target_y.toFixed(0)}]</div>
                                <div>DELIVERED: ${bot.missions}</div>
                            </div>
                            <div class="stat-bar-track">
                                <div class="stat-bar-fill" style="width:${bot.battery}%; background:${bot.battery < 22 ? 'var(--accent-red)' : bot.color};"></div>
                            </div>
                        </div>
                    `;
                });
                document.getElementById("botCards").innerHTML = cardsHtml;
                document.getElementById("conflictCount").innerText = data.stats.conflicts_resolved;
                document.getElementById("missionsCount").innerText = data.stats.missions_completed;

                // Terminal Audit Logs
                const term = document.getElementById("terminalFeed");
                term.innerHTML = data.logs.map(log => {
                    let cls = "log-entry";
                    if (log.includes("HAZARD") || log.includes("SCENARIO") || log.includes("Low battery")) cls += " warn";
                    if (log.includes("Resolution") || log.includes("recharged") || log.includes("delivered")) cls += " green";
                    if (log.includes("A*") || log.includes("replanning")) cls += " cyan";
                    return `<div class="${cls}">${log}</div>`;
                }).join("");
                term.scrollTop = term.scrollHeight;

                const estopBtn = document.getElementById("btnEStop");
                estopBtn.classList.toggle("active", data.e_stop);
                estopBtn.innerText = data.e_stop ? "E-STOP ENGAGED" : "EMERGENCY STOP";
            };
        }
        connectWS();

        window.selectBot = function(id) {
            selectedBotId = id;
            if (cameraMode === 'chase') updateChaseCamera();
        };

        // Camera Views
        window.setCameraView = function(view) {
            cameraMode = view;
            document.getElementById("camIso").classList.toggle("active", view === 'iso');
            document.getElementById("camTop").classList.toggle("active", view === 'top');
            document.getElementById("camChase").classList.toggle("active", view === 'chase');

            if (view === 'iso') {
                camera.position.set(-8, 22, 36);
                controls.target.set(12, 0, 12);
            } else if (view === 'top') {
                camera.position.set(12, 36, 12);
                controls.target.set(12, 0, 12);
            }
        };

        function updateChaseCamera() {
            if (cameraMode === 'chase' && botMeshes[selectedBotId]) {
                const targetBot = botMeshes[selectedBotId];
                camera.position.x = targetBot.position.x - Math.sin(-targetBot.rotation.y) * 6;
                camera.position.z = targetBot.position.z + Math.cos(-targetBot.rotation.y) * 6;
                camera.position.y = 5.5;
                controls.target.set(targetBot.position.x, 0.4, targetBot.position.z);
            }
        }

        // Action Toolbar Event Listeners
        document.getElementById("btnHazard").addEventListener("click", () => {
            hazardMode = !hazardMode;
            document.getElementById("btnHazard").classList.toggle("active", hazardMode);
            document.getElementById("hudNotice").style.display = hazardMode ? "block" : "none";
        });

        document.getElementById("btnHeadOn").addEventListener("click", () => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: "head_on_scenario" }));
            }
        });

        document.getElementById("btnHeatmap").addEventListener("click", () => {
            heatmapMode = !heatmapMode;
            document.getElementById("btnHeatmap").classList.toggle("active", heatmapMode);
        });

        document.getElementById("btnEStop").addEventListener("click", () => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: "e_stop" }));
            }
        });

        document.getElementById("btnExportCSV").addEventListener("click", () => {
            if (!latestData || !latestData.logs) return;
            let csv = "Timestamp,Event\\n";
            latestData.logs.forEach(l => {
                const parts = l.split("] ");
                const t = parts[0].replace("[", "");
                const msg = parts[1] ? parts[1].replace(/,/g, ";") : "";
                csv += `${t},${msg}\\n`;
            });
            const blob = new Blob([csv], { type: "text/csv" });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.setAttribute("href", url);
            a.setAttribute("download", `fleetguard_audit_${Date.now()}.csv`);
            a.click();
        });

        window.addEventListener("resize", () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        function animate() {
            requestAnimationFrame(animate);
            if (cameraMode === 'chase') {
                updateChaseCamera();
            }
            controls.update();
            renderer.render(scene, camera);
        }
        animate();
    </script>
</body>
</html>
"""

# ==============================================================================
# 6. ROUTING & WEBSOCKET DISPATCH
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTMLResponse(HTML_CONTENT)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    engine.active_connections.append(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                action = data.get("action")
                if action == "e_stop":
                    engine.e_stop = not engine.e_stop
                    status_text = "TRIGGERED" if engine.e_stop else "CLEARED"
                    engine.log_event(f"E-STOP {status_text} by operator.")
                elif action == "head_on_scenario":
                    engine.trigger_headon_scenario()
                elif action == "toggle_hazard":
                    engine.toggle_hazard(data.get("x"), data.get("y"))
            except Exception:
                pass
    except WebSocketDisconnect:
        if websocket in engine.active_connections:
            engine.active_connections.remove(websocket)
    except Exception:
        if websocket in engine.active_connections:
            engine.active_connections.remove(websocket)


if __name__ == "__main__":
    uvicorn.run("sim3d_interactive:app", host="127.0.0.1", port=8000, reload=False)