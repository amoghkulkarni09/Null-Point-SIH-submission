"""
EdgeNav Swarm Engine — SIH 2026 PS 123
Blueprint workflow:
  1) Contract Net task auction (marginal cost self-assignment)
  2) Space-Time A* corridor reservation (x, z, t, radius)
  3) P2P right-of-way when corridors overlap in space-time
  4) Wait-For-Graph deadlock → local Raft leader → step-back
  5) Local ORCA velocity adjustment for dynamic hazards (no global replan)
"""

from __future__ import annotations

import asyncio
import heapq
import json
import math
import random
import time
from typing import Dict, List, Optional, Set, Tuple

import websockets

Vec = Tuple[float, float]
CorridorPoint = Dict  # {x,z,t,radius}

WAREHOUSE_CONFIG = {
    "dimensions": {"width": 40, "length": 40},
    "racks": [
        {"id": "RACK-A1", "x": -12, "z": -8, "w": 4, "d": 7, "label": "Fast Movers A1", "status": "OPTIMAL"},
        {"id": "RACK-A2", "x": -12, "z": 8, "w": 4, "d": 7, "label": "Fast Movers A2", "status": "OPTIMAL"},
        {"id": "RACK-B1", "x": 12, "z": -8, "w": 4, "d": 7, "label": "Bulk Storage B1", "status": "OPTIMAL"},
        {"id": "RACK-B2", "x": 12, "z": 8, "w": 4, "d": 7, "label": "Bulk Storage B2", "status": "OPTIMAL"},
        {"id": "RACK-C1", "x": 0, "z": -12, "w": 6, "d": 3, "label": "Cold Chain C1", "status": "OPTIMAL"},
        {"id": "RACK-C2", "x": 0, "z": 12, "w": 6, "d": 3, "label": "Hazardous C2", "status": "ATTENTION"},
    ],
    "zones": [
        {"id": "PICKUP-1", "x": -16, "z": -15, "w": 4, "d": 4, "type": "PICKUP", "label": "Inbound Bay 01"},
        {"id": "PICKUP-2", "x": 16, "z": -15, "w": 4, "d": 4, "type": "PICKUP", "label": "Inbound Bay 02"},
        {"id": "DROP-1", "x": -16, "z": 15, "w": 4, "d": 4, "type": "DROP", "label": "Outbound Dock 01"},
        {"id": "DROP-2", "x": 16, "z": 15, "w": 4, "d": 4, "type": "DROP", "label": "Outbound Dock 02"},
        {"id": "CHARGER-1", "x": -6, "z": 0, "w": 3, "d": 3, "type": "CHARGING", "label": "Inductive Pad A"},
        {"id": "CHARGER-2", "x": 6, "z": 0, "w": 3, "d": 3, "type": "CHARGING", "label": "Inductive Pad B"},
    ],
}

ROBOT_RADIUS = 0.65
CORRIDOR_RADIUS = 1.15
MIN_SEP = 2.4
RACK_PADDING = 1.0
WORLD_LIMIT = 18.5
GRID_STEP = 1.0
NOMINAL_SPEED = 1.2
TIME_SAMPLE = 0.45  # seconds between corridor samples


def normalize_angle(a: float) -> float:
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def lerp_angle(a: float, b: float, t: float) -> float:
    return a + normalize_angle(b - a) * max(0.0, min(1.0, t))


# =============================================================================
# NAV MAP — spatial A* (aisle-aware, no rack traversal)
# =============================================================================
class NavigationMap:
    def __init__(self):
        self.rack_boxes = []
        for r in WAREHOUSE_CONFIG["racks"]:
            hw, hd = r["w"] / 2 + RACK_PADDING, r["d"] / 2 + RACK_PADDING
            self.rack_boxes.append((r["x"] - hw, r["z"] - hd, r["x"] + hw, r["z"] + hd))
        self.free_cells: Set[Tuple[int, int]] = set()
        lo, hi = int(-WORLD_LIMIT), int(WORLD_LIMIT) + 1
        for ix in range(lo, hi):
            for iz in range(lo, hi):
                if not self.point_in_rack(float(ix), float(iz)):
                    self.free_cells.add((ix, iz))
        self.safe_spots: List[Vec] = [
            (-16, -15), (16, -15), (-16, 15), (16, 15),
            (-6, 0), (6, 0), (0, 0), (-16, 0), (16, 0),
            (0, -16), (0, 16), (-8, -16), (8, -16), (-8, 16), (8, 16),
        ]

    def point_in_rack(self, x: float, z: float) -> bool:
        for x0, z0, x1, z1 in self.rack_boxes:
            if x0 <= x <= x1 and z0 <= z <= z1:
                return True
        return False

    def is_free(self, x: float, z: float) -> bool:
        return abs(x) <= WORLD_LIMIT and abs(z) <= WORLD_LIMIT and not self.point_in_rack(x, z)

    def snap(self, x: float, z: float) -> Tuple[int, int]:
        return int(round(x / GRID_STEP)), int(round(z / GRID_STEP))

    def nearest_free(self, x: float, z: float) -> Vec:
        if self.is_free(x, z):
            return (x, z)
        cx, cz = self.snap(x, z)
        best, best_d = (0.0, 0.0), 1e9
        for r in range(0, 28):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if r and abs(dx) != r and abs(dz) != r:
                        continue
                    c = (cx + dx, cz + dz)
                    if c in self.free_cells:
                        fx, fz = float(c[0]), float(c[1])
                        d = (fx - x) ** 2 + (fz - z) ** 2
                        if d < best_d:
                            best_d, best = d, (fx, fz)
            if best_d < 1e8:
                return best
        return (0.0, 0.0)

    def segment_hits_rack(self, a: Vec, b: Vec) -> bool:
        dist = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(16, int(dist * 2) + 1)
        for i in range(n + 1):
            t = i / n
            x = a[0] + (b[0] - a[0]) * t
            z = a[1] + (b[1] - a[1]) * t
            if self.point_in_rack(x, z):
                return True
        return False

    def plan(self, start: Vec, goal: Vec, blocked: Optional[Set[Tuple[int, int]]] = None) -> List[Vec]:
        blocked = blocked or set()
        sx, sz = self.nearest_free(*start)
        gx, gz = self.nearest_free(*goal)
        sc, gc = self.snap(sx, sz), self.snap(gx, gz)

        def ok(c):
            return c in self.free_cells and c not in blocked

        if gc in blocked:
            blocked = set(blocked)
            blocked.discard(gc)
        if not ok(sc):
            sc = self.snap(*self.nearest_free(float(sc[0]), float(sc[1])))
        if not ok(gc):
            gc = self.snap(*self.nearest_free(float(gc[0]), float(gc[1])))
        if sc == gc:
            return [(gx, gz)]

        def h(c):
            return abs(c[0] - gc[0]) + abs(c[1] - gc[1])

        heap = [(h(sc), 0.0, sc)]
        came, gscore, closed = {}, {sc: 0.0}, set()
        nbrs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        found = False
        while heap:
            _, g, cur = heapq.heappop(heap)
            if cur in closed:
                continue
            closed.add(cur)
            if cur == gc:
                found = True
                break
            for dx, dz in nbrs:
                nxt = (cur[0] + dx, cur[1] + dz)
                if not ok(nxt) or nxt in closed:
                    continue
                if dx and dz and (not ok((cur[0] + dx, cur[1])) or not ok((cur[0], cur[1] + dz))):
                    continue
                ng = g + (1.414 if dx and dz else 1.0)
                if ng < gscore.get(nxt, 1e18):
                    gscore[nxt] = ng
                    came[nxt] = cur
                    heapq.heappush(heap, (ng + h(nxt), ng, nxt))
        if not found:
            # Fail soft: route via free centre aisle, never teleport to goal
            vias = [(0.0, -8.0), (0.0, 8.0), (-8.0, 0.0), (8.0, 0.0), (0.0, 0.0)]
            for v in vias:
                vc = self.snap(*v)
                if vc in self.free_cells and vc not in blocked:
                    return [v, (gx, gz)]
            return [(gx, gz)]

        cells = [gc]
        cur = gc
        while cur != sc:
            cur = came[cur]
            cells.append(cur)
        cells.reverse()
        pts = [(float(c[0]), float(c[1])) for c in cells]
        pts[-1] = (gx, gz)
        return self._simplify(pts)

    def _simplify(self, pts: List[Vec]) -> List[Vec]:
        if len(pts) <= 2:
            return pts
        out = [pts[0]]
        i = 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1 and self.segment_hits_rack(pts[i], pts[j]):
                j -= 1
            out.append(pts[j])
            i = j
        cleaned = [out[0]]
        for p in out[1:]:
            if math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 0.35:
                cleaned.append(p)
        return cleaned


NAV = NavigationMap()


# =============================================================================
# SPACE-TIME CORRIDOR HELPERS
# =============================================================================
def build_corridor(path: List[Vec], t0: float, speed: float = NOMINAL_SPEED, radius: float = CORRIDOR_RADIUS) -> List[CorridorPoint]:
    """Stamp a geometric path into a 4D envelope (x, z, t, radius)."""
    if not path:
        return []
    corridor: List[CorridorPoint] = [
        {"x": round(path[0][0], 2), "z": round(path[0][1], 2), "t": round(t0, 2), "radius": radius}
    ]
    prev = path[0]
    for nxt in path[1:]:
        dist = math.hypot(nxt[0] - prev[0], nxt[1] - prev[1])
        if dist < 1e-6:
            continue
        travel = dist / max(0.35, speed)
        steps = max(1, int(travel / TIME_SAMPLE))
        last_t = corridor[-1]["t"]
        for s in range(1, steps + 1):
            frac = s / steps
            x = prev[0] + (nxt[0] - prev[0]) * frac
            z = prev[1] + (nxt[1] - prev[1]) * frac
            tt = last_t + travel * frac
            corridor.append({"x": round(x, 2), "z": round(z, 2), "t": round(tt, 2), "radius": radius})
        prev = nxt
    return corridor


def shift_corridor_time(corridor: List[CorridorPoint], delay: float) -> List[CorridorPoint]:
    return [{**p, "t": round(p["t"] + delay, 2)} for p in corridor]


def corridors_conflict(
    a: List[CorridorPoint], b: List[CorridorPoint], time_slack: float = 0.85
) -> Optional[Tuple[CorridorPoint, CorridorPoint]]:
    """Conflict if envelopes are close in space at similar reserved times."""
    if not a or not b:
        return None
    # Index B by coarse time buckets for speed
    for pa in a:
        for pb in b:
            if abs(pa["t"] - pb["t"]) > time_slack:
                continue
            lim = pa.get("radius", CORRIDOR_RADIUS) + pb.get("radius", CORRIDOR_RADIUS)
            if math.hypot(pa["x"] - pb["x"], pa["z"] - pb["z"]) < lim:
                return pa, pb
    return None


def corridor_right_of_way(urgency_a: int, id_a: str, urgency_b: int, id_b: str) -> str:
    """Return id of robot that KEEPS the corridor (higher urgency wins; tie → lower id)."""
    if urgency_a != urgency_b:
        return id_a if urgency_a > urgency_b else id_b
    return id_a if id_a < id_b else id_b


# =============================================================================
# AMR NODE
# =============================================================================
class AMRNode:
    def __init__(self, agent_id: str, x: float, z: float, priority: int = 1, battery: float = 95.0):
        fx, fz = NAV.nearest_free(x, z)
        self.id = agent_id
        self.x, self.z, self.y = fx, fz, 0.0
        self.heading = 0.0
        self.vx, self.vz = 0.0, 0.0
        self.velocity = 0.0
        self.max_speed = NOMINAL_SPEED
        self.priority = priority
        self.base_priority = priority
        self.urgency = priority  # task urgency overlay
        self.state = "IDLE"
        self.battery = battery
        self.has_payload = False
        self.payload_weight = 0.0
        self.current_task: Optional[Dict] = None
        self.waypoints: List[Vec] = []
        self.corridor: List[CorridorPoint] = []
        self.corridor_delay = 0.0  # accumulated yield waits (space-time)
        self.wait_for: Optional[str] = None  # WFG edge
        self.yield_until = 0.0
        self.is_raft_leader = False
        self.lidar_angle = 0.0
        self.lidar_range = 5.5
        self.idle_timer = random.uniform(3.0, 8.0)
        self.target_x, self.target_z = fx, fz

    def effective_urgency(self) -> int:
        u = self.urgency + self.priority
        if self.has_payload:
            u += 3
        if self.current_task:
            u += int(self.current_task.get("urgency", 0))
        return u


# =============================================================================
# SWARM CONTROLLER
# =============================================================================
class SwarmMeshController:
    def __init__(self):
        self.nodes: Dict[str, AMRNode] = {
            "AMR-101": AMRNode("AMR-101", -14, 0, 3, 94),
            "AMR-102": AMRNode("AMR-102", 0, -14, 2, 88.5),
            "AMR-103": AMRNode("AMR-103", 14, 4, 1, 76.2),
            "AMR-104": AMRNode("AMR-104", -6, -14, 4, 98),
            "AMR-105": AMRNode("AMR-105", 6, -14, 2, 62),
        }
        self.dynamic_obstacles = [
            {"id": "OBS-1", "x": 0.0, "z": 6.0, "radius": 1.25, "label": "Warehouse Worker", "active": False}
        ]
        self.active_tasks: List[Dict] = []
        self.auction_history: List[Dict] = []
        self.event_log: List[Dict] = []
        self.emergency_stop = False
        self.raft_leader_id = "AMR-101"
        self.raft_term = 1
        self.nodes["AMR-101"].is_raft_leader = True
        self.sim_time = 0.0
        self._arb_cooldown: Dict[str, float] = {}
        self.setup_initial_patrol()
        self.log_event("SYSTEM", "EdgeNav online — CNP + Space-Time corridors + P2P/Raft/ORCA.")

    def log_event(self, category: str, message: str, level: str = "INFO"):
        self.event_log.insert(
            0,
            {
                "id": f"EVT-{int(time.time() * 1000) % 100000}",
                "timestamp": round(time.time(), 2),
                "category": category,
                "message": message,
                "level": level,
            },
        )
        if len(self.event_log) > 30:
            self.event_log.pop()

    def setup_initial_patrol(self):
        self.assign_corridor_route(self.nodes["AMR-101"], [(-16.0, 0.0)])
        self.assign_corridor_route(self.nodes["AMR-102"], [(0.0, -16.0)])
        self.assign_corridor_route(self.nodes["AMR-103"], [(16.0, 0.0)])

    # ----- Contract Net Protocol -----
    def marginal_cost(self, node: AMRNode, pickup: Vec, order_type: str, weight: float, urgency: int) -> float:
        dist = math.hypot(node.x - pickup[0], node.z - pickup[1])
        bat = max(0.0, (100.0 - node.battery) * 0.35)
        load = 40.0 if (node.has_payload or node.current_task) else 0.0
        busy = 22.0 if node.state in ("MOVING", "NEGOTIATING", "YIELDING", "AVOIDING") else 0.0
        wpen = weight * (0.18 if order_type == "HEAVY" else 0.05)
        if order_type == "EXPRESS":
            bat *= 0.4
            busy *= 0.35
        # lower cost wins; urgency of THIS order reduces cost for high-prio robots slightly
        urg_bonus = (node.priority + urgency) * (8.0 if order_type == "EXPRESS" else 3.5)
        return dist + bat + load + busy + wpen - urg_bonus

    def create_order(self, order_type="DELIVER", pickup_id="PICKUP-1", drop_id="DROP-1", urgency=2, weight=10.0):
        order_type = (order_type or "DELIVER").upper()
        urgency = max(1, min(5, int(urgency)))
        weight = max(1.0, min(80.0, float(weight)))

        if order_type == "CHARGE":
            charger = self._zone(drop_id) or self._zone("CHARGER-1") or (-6.0, 0.0)
            free = [n for n in self.nodes.values() if not n.current_task] or list(self.nodes.values())
            winner = min(free, key=lambda n: n.battery)
            task = self._make_task("CHARGE", "CURRENT", drop_id if str(drop_id).startswith("CHARGER") else "CHARGER-1",
                                   (winner.x, winner.z), charger, urgency, 0.0, winner.id, "TO_CHARGE")
            task["bids"] = {n.id: round(100 - n.battery, 1) for n in self.nodes.values()}
            task["winning_bid"] = task["bids"][winner.id]
            winner.current_task = task
            winner.urgency = urgency
            self.assign_corridor_route(winner, [charger])
            self._register_task(task)
            self.log_event("CNP_AUCTION", f"CHARGE awarded to {winner.id} (bat {winner.battery:.0f}%)")
            return task

        pickup = self._zone(pickup_id) or (-16.0, -15.0)
        drop = self._zone(drop_id) or (16.0, 15.0)
        bids = {n.id: round(self.marginal_cost(n, pickup, order_type, weight, urgency), 1) for n in self.nodes.values()}
        winner_id = min(bids, key=bids.get)
        winner = self.nodes[winner_id]
        task = self._make_task(order_type, pickup_id, drop_id, pickup, drop, urgency, weight, winner_id, "TO_PICKUP")
        task["bids"] = bids
        task["winning_bid"] = bids[winner_id]
        winner.current_task = task
        winner.urgency = urgency
        winner.priority = min(9, winner.base_priority + (2 if order_type == "EXPRESS" else 0) + (1 if urgency >= 4 else 0))
        winner.has_payload = False
        self.assign_corridor_route(winner, [pickup])
        self._register_task(task)
        self.log_event(
            "CNP_AUCTION",
            f"CNP {order_type} {task['id']}: {pickup_id}->{drop_id} self-assigned to {winner_id} (cost {bids[winner_id]})",
        )
        return task

    def auction_task(self):
        self.create_order("DELIVER", random.choice(["PICKUP-1", "PICKUP-2"]), random.choice(["DROP-1", "DROP-2"]), 2, 12)

    def _make_task(self, typ, pid, did, pickup, drop, urgency, weight, assigned, stage):
        return {
            "id": f"ORD-{int(time.time()) % 10000}",
            "type": typ,
            "pickup_id": pid,
            "drop_id": did,
            "pickup": [pickup[0], pickup[1]],
            "drop": [drop[0], drop[1]],
            "urgency": urgency,
            "weight": weight,
            "stage": stage,
            "status": "ASSIGNED",
            "assigned_to": assigned,
        }

    def _register_task(self, task: Dict):
        self.active_tasks = [t for t in self.active_tasks if t.get("status") == "ASSIGNED"]
        self.active_tasks.insert(0, task)
        self.auction_history.insert(
            0,
            {
                "task_id": task["id"],
                "bids": task.get("bids", {}),
                "winner": task["assigned_to"],
                "winning_bid": task.get("winning_bid", 0),
                "timestamp": time.time(),
            },
        )
        if len(self.auction_history) > 8:
            self.auction_history.pop()

    def _zone(self, zid: str) -> Optional[Vec]:
        for z in WAREHOUSE_CONFIG["zones"]:
            if z["id"] == zid:
                return NAV.nearest_free(float(z["x"]), float(z["z"]))
        return None

    # ----- Space-Time corridor assignment -----
    def assign_corridor_route(self, node: AMRNode, goals: List[Vec], time_offset: float = 0.0):
        path: List[Vec] = []
        cur = (node.x, node.z)
        blocked = self._occupancy_cells(node)
        for g in goals:
            seg = NAV.plan(cur, g, blocked)
            for p in seg:
                if not path or math.hypot(p[0] - path[-1][0], p[1] - path[-1][1]) > 0.4:
                    path.append(p)
            cur = g
        if not path:
            path = [NAV.nearest_free(*goals[-1])]
        node.waypoints = path[:]
        node.target_x, node.target_z = path[-1]
        node.corridor = build_corridor(path, self.sim_time + time_offset + node.corridor_delay, node.max_speed)
        node.state = "MOVING"
        node.wait_for = None
        # After reserving, immediately resolve space-time conflicts with peers
        self.resolve_space_time_conflicts(focus=node)

    def _occupancy_cells(self, node: AMRNode) -> Set[Tuple[int, int]]:
        """Only block peers' current footprints — temporal conflicts use corridors."""
        blocked: Set[Tuple[int, int]] = set()
        for o in self.nodes.values():
            if o.id == node.id:
                continue
            ix, iz = NAV.snap(o.x, o.z)
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    blocked.add((ix + dx, iz + dz))
        return blocked

    # ----- P2P space-time conflict resolution -----
    def resolve_space_time_conflicts(self, focus: Optional[AMRNode] = None):
        keys = list(self.nodes.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = self.nodes[keys[i]], self.nodes[keys[j]]
                if not a.corridor or not b.corridor:
                    continue
                if a.state == "IDLE" and b.state == "IDLE":
                    continue
                hit = corridors_conflict(a.corridor, b.corridor)
                if not hit:
                    if a.wait_for == b.id and self.sim_time >= a.yield_until:
                        a.wait_for = None
                        if a.state == "YIELDING":
                            a.state = "MOVING"
                    if b.wait_for == a.id and self.sim_time >= b.yield_until:
                        b.wait_for = None
                        if b.state == "YIELDING":
                            b.state = "MOVING"
                    continue

                pa, pb = hit
                keeper_id = corridor_right_of_way(
                    a.effective_urgency(), a.id, b.effective_urgency(), b.id
                )
                yielder = b if keeper_id == a.id else a
                keeper = a if keeper_id == a.id else b

                # Already yielding for this keeper — don't stack infinite delays every tick
                if yielder.wait_for == keeper.id and yielder.state == "YIELDING" and self.sim_time < yielder.yield_until:
                    continue

                delay = 2.2 + abs(pa["t"] - self.sim_time) * 0.05
                delay = max(1.8, min(4.5, delay))
                yielder.corridor_delay += delay
                yielder.corridor = shift_corridor_time(yielder.corridor, delay)
                yielder.wait_for = keeper.id
                yielder.yield_until = self.sim_time + min(2.5, delay)
                yielder.vx = yielder.vz = yielder.velocity = 0.0
                yielder.state = "YIELDING"

                if corridors_conflict(keeper.corridor, yielder.corridor):
                    yielder.corridor = shift_corridor_time(yielder.corridor, 2.0)
                    yielder.corridor_delay += 2.0
                    yielder.yield_until = self.sim_time + 2.5

                key = f"{yielder.id}>{keeper.id}"
                if self.sim_time - self._arb_cooldown.get(key, -99) > 1.5:
                    self._arb_cooldown[key] = self.sim_time
                    self.log_event(
                        "P2P_ARBITRATION",
                        f"Space-time conflict at ({pa['x']:.0f},{pa['z']:.0f}) t={pa['t']:.1f}s: "
                        f"{yielder.id} yields to {keeper.id} "
                        f"(urgency {yielder.effective_urgency()} < {keeper.effective_urgency()}); "
                        f"corridor +{delay:.1f}s",
                    )

    # ----- Wait-For-Graph deadlock + Raft -----
    def detect_and_clear_deadlocks(self):
        # Build WFG from wait_for edges
        wfg = {n.id: n.wait_for for n in self.nodes.values() if n.wait_for}

        def find_cycle() -> Optional[List[str]]:
            visited, stack = set(), []

            def dfs(u):
                if u in stack:
                    return stack[stack.index(u) :]
                if u in visited or u not in wfg:
                    return None
                visited.add(u)
                stack.append(u)
                v = wfg.get(u)
                if v:
                    cyc = dfs(v)
                    if cyc:
                        return cyc
                stack.pop()
                return None

            for n in list(wfg):
                cyc = dfs(n)
                if cyc and len(cyc) >= 2:
                    return cyc
            return None

        cycle = find_cycle()
        if not cycle:
            return

        # Raft: elect local leader among cycle (highest urgency, then id)
        members = [self.nodes[i] for i in cycle if i in self.nodes]
        if not members:
            return
        leader = max(members, key=lambda n: (n.effective_urgency(), n.id))
        self.raft_term += 1
        self.raft_leader_id = leader.id
        for n in self.nodes.values():
            n.is_raft_leader = n.id == leader.id

        subordinates = [n for n in members if n.id != leader.id]
        self.log_event(
            "RAFT_CONSENSUS",
            f"WFG deadlock {cycle}: Raft elects {leader.id} (term {self.raft_term}). Step-back ordered.",
            "WARNING",
        )

        for sub in subordinates:
            # Step back to nearest clear safe spot away from leader
            candidates = sorted(
                NAV.safe_spots,
                key=lambda p: math.hypot(p[0] - sub.x, p[1] - sub.z),
            )
            spot = None
            for p in candidates:
                if math.hypot(p[0] - leader.x, p[1] - leader.z) > MIN_SEP + 1.5:
                    if math.hypot(p[0] - sub.x, p[1] - sub.z) > 2.0:
                        spot = p
                        break
            spot = spot or NAV.nearest_free(sub.x - 3, sub.z - 3)
            sub.wait_for = None
            sub.corridor_delay = 0.0
            sub.state = "DEADLOCK_CLEARING"
            self.assign_corridor_route(sub, [spot], time_offset=0.2)
            sub.state = "DEADLOCK_CLEARING"

        leader.wait_for = None
        if leader.state == "YIELDING":
            leader.state = "MOVING"
            leader.yield_until = 0.0

    # ----- ORCA local avoidance (velocity-space, no global replan) -----
    def orca_adjust(self, node: AMRNode, prefer_vx: float, prefer_vz: float, dt: float) -> Tuple[float, float]:
        """Optimal Reciprocal Collision Avoidance — local motor vector tweak."""
        vx, vz = prefer_vx, prefer_vz
        # Dynamic human/obstacle
        for obs in self.dynamic_obstacles:
            if not obs.get("active"):
                continue
            dx, dz = node.x - obs["x"], node.z - obs["z"]
            dist = math.hypot(dx, dz) or 1e-6
            lim = obs["radius"] + ROBOT_RADIUS + 0.9
            if dist < lim * 1.8:
                # push velocity away from obstacle
                nx, nz = dx / dist, dz / dist
                # remove inbound component
                into = min(0.0, vx * (-nx) + vz * (-nz))
                vx += -into * (-nx) + nx * 0.55
                vz += -into * (-nz) + nz * 0.55
                node.state = "AVOIDING"
        # Nearby robots — reciprocal half-plane
        for o in self.nodes.values():
            if o.id == node.id:
                continue
            dx, dz = o.x - node.x, o.z - node.z
            dist = math.hypot(dx, dz) or 1e-6
            if dist > MIN_SEP * 1.7:
                continue
            # relative velocity
            rvx, rvz = vx - o.vx, vz - o.vz
            # if closing in, cancel approach component
            nx, nz = dx / dist, dz / dist
            closing = rvx * nx + rvz * nz
            if closing > 0 and dist < MIN_SEP * 1.35:
                # each takes half responsibility (ORCA reciprocal)
                vx -= 0.5 * closing * nx
                vz -= 0.5 * closing * nz
                if node.state == "MOVING":
                    node.state = "AVOIDING"
        # Clamp speed
        sp = math.hypot(vx, vz)
        if sp > node.max_speed:
            vx *= node.max_speed / sp
            vz *= node.max_speed / sp
        return vx, vz

    # ----- Scenarios -----
    def trigger_intersection_scenario(self):
        """Two reserved corridors cross at (0,0) at the SAME t — triggers P2P RoW."""
        a, b = self.nodes["AMR-101"], self.nodes["AMR-102"]
        # Equal path length to the junction ⇒ overlapping (x,z,t) envelopes
        a.x, a.z = NAV.nearest_free(-8.0, 0.0)
        b.x, b.z = NAV.nearest_free(0.0, -8.0)
        a.priority, b.priority = 3, 1
        a.urgency, b.urgency = 5, 1
        a.corridor_delay = b.corridor_delay = 0.0
        a.wait_for = b.wait_for = None
        a.yield_until = b.yield_until = 0.0
        self.assign_corridor_route(a, [(8.0, 0.0)])
        self.assign_corridor_route(b, [(0.0, 8.0)])
        self.log_event(
            "SCENARIO",
            "Intersection: equal ETA at (0,0) — AMR-101 (urgency 5) vs AMR-102 (urgency 1).",
        )

    def trigger_deadlock_scenario(self):
        a, c = self.nodes["AMR-101"], self.nodes["AMR-103"]
        a.x, a.z = NAV.nearest_free(-8, 0)
        c.x, c.z = NAV.nearest_free(8, 0)
        a.priority = c.priority = 2
        a.urgency = c.urgency = 2
        a.corridor_delay = c.corridor_delay = 0.0
        self.assign_corridor_route(a, [(8.0, 0.0)])
        self.assign_corridor_route(c, [(-8.0, 0.0)])
        # Force mutual wait to demonstrate WFG→Raft (head-on equal urgency)
        a.wait_for, c.wait_for = c.id, a.id
        a.state = c.state = "YIELDING"
        a.yield_until = c.yield_until = self.sim_time + 5.0
        self.log_event("SCENARIO", "Head-on equal-urgency deadlock seeded — Raft will clear WFG cycle.")

    def toggle_obstacle(self):
        obs = self.dynamic_obstacles[0]
        obs["active"] = not obs["active"]
        obs["x"], obs["z"] = NAV.nearest_free(obs["x"], obs["z"])
        self.log_event("HAZARD", f"Dynamic obstacle {'ACTIVE' if obs['active'] else 'cleared'} — ORCA local avoidance.")

    # ----- Motion integration -----
    def _advance_node(self, node: AMRNode, dt: float):
        node.lidar_angle = (node.lidar_angle + dt * 5) % (2 * math.pi)
        if node.state in ("MOVING", "AVOIDING", "DEADLOCK_CLEARING"):
            node.battery = max(8.0, node.battery - 0.012 * dt)
        elif node.state == "IDLE" and abs(node.x + 6) < 2 and abs(node.z) < 2:
            node.battery = min(100.0, node.battery + 0.8 * dt)

        # Yielding / negotiating: hold until yield_until (space-time delay)
        if node.state in ("YIELDING", "NEGOTIATING"):
            node.vx = node.vz = node.velocity = 0.0
            if self.sim_time >= node.yield_until:
                node.state = "MOVING"
                node.wait_for = None
            else:
                return

        if node.state not in ("MOVING", "AVOIDING", "DEADLOCK_CLEARING") or not node.waypoints:
            node.vx = node.vz = node.velocity = 0.0
            return

        # Pace to space-time schedule: don't arrive earlier than reserved t
        if node.corridor:
            # nearest corridor sample ahead of pose
            best = None
            best_d = 1e9
            for p in node.corridor:
                d = math.hypot(p["x"] - node.x, p["z"] - node.z)
                if d < best_d:
                    best_d = d
                    best = p
            if best and best_d < 2.5 and self.sim_time + 0.15 < best["t"]:
                # Hold — reservation slot not open yet
                node.vx = node.vz = node.velocity = 0.0
                if node.state == "MOVING":
                    node.state = "YIELDING"
                return
            if node.state == "YIELDING" and best and self.sim_time >= best["t"] - 0.05 and not node.wait_for:
                node.state = "MOVING"

        tx, tz = node.waypoints[0]
        dx, dz = tx - node.x, tz - node.z
        dist = math.hypot(dx, dz)
        if dist < 0.4:
            node.waypoints.pop(0)
            if not node.waypoints:
                self._on_route_complete(node)
            else:
                # refresh remaining corridor from current pose
                node.corridor = build_corridor(
                    [(node.x, node.z)] + node.waypoints,
                    self.sim_time + node.corridor_delay,
                    node.max_speed,
                )
            return

        prefer_vx = (dx / dist) * min(node.max_speed, max(0.25, dist))
        prefer_vz = (dz / dist) * min(node.max_speed, max(0.25, dist))
        vx, vz = self.orca_adjust(node, prefer_vx, prefer_vz, dt)

        nx = node.x + vx * dt
        nz = node.z + vz * dt
        if not NAV.is_free(nx, nz):
            # slide along free projection
            fx, fz = NAV.nearest_free(nx, nz)
            nx, nz = fx, fz
            vx = vz = 0.0

        # Soft physical separation (safety layer under ORCA)
        for o in self.nodes.values():
            if o.id == node.id:
                continue
            if math.hypot(nx - o.x, nz - o.z) < MIN_SEP:
                # stop; rely on space-time yield — don't tunnel
                node.vx = node.vz = node.velocity = 0.0
                if not node.wait_for:
                    node.state = "YIELDING"
                    node.wait_for = o.id
                    node.yield_until = max(node.yield_until, self.sim_time + 0.8)
                return

        node.x, node.z = nx, nz
        node.vx, node.vz = vx, vz
        node.velocity = math.hypot(vx, vz)
        if node.velocity > 0.05:
            node.heading = lerp_angle(node.heading, math.atan2(vx, vz), 8 * dt)
        if node.state == "AVOIDING" and not any(
            o.get("active") and math.hypot(node.x - o["x"], node.z - o["z"]) < o["radius"] + 2.2
            for o in self.dynamic_obstacles
        ):
            # clear avoiding if no near hazard and not squeezed
            near = any(
                math.hypot(node.x - o.x, node.z - o.z) < MIN_SEP * 1.3
                for o in self.nodes.values()
                if o.id != node.id
            )
            if not near:
                node.state = "MOVING"

    def _on_route_complete(self, node: AMRNode):
        node.corridor = []
        node.vx = node.vz = node.velocity = 0.0
        task = node.current_task
        if task and task.get("status") == "ASSIGNED":
            stage = task.get("stage")
            if stage == "TO_PICKUP":
                node.has_payload = True
                node.payload_weight = float(task.get("weight", 10))
                task["stage"] = "TO_DROP"
                drop = task["drop"]
                self.log_event("DISPATCH", f"{node.id} picked load — reserving corridor to {task.get('drop_id')}")
                self.assign_corridor_route(node, [(drop[0], drop[1])])
                return
            if stage == "TO_DROP":
                task["status"] = "COMPLETED"
                node.current_task = None
                node.has_payload = False
                node.payload_weight = 0.0
                node.urgency = node.base_priority
                node.priority = node.base_priority
                node.state = "IDLE"
                node.idle_timer = random.uniform(5, 12)
                self.log_event("DISPATCH", f"{node.id} completed {task['id']}")
                return
            if stage == "TO_CHARGE":
                node.battery = min(100.0, node.battery + 25)
                task["status"] = "COMPLETED"
                node.current_task = None
                node.state = "IDLE"
                node.idle_timer = random.uniform(6, 12)
                return
        node.state = "IDLE"
        node.idle_timer = random.uniform(4, 10)
        node.wait_for = None

    def step(self, dt: float):
        if self.emergency_stop:
            for n in self.nodes.values():
                n.vx = n.vz = n.velocity = 0.0
            return

        self.sim_time += dt

        # 1) Space-time corridor P2P arbitration
        self.resolve_space_time_conflicts()
        # 2) Deadlock WFG → Raft
        self.detect_and_clear_deadlocks()

        # 3) Idle autonomous light patrol (won't fight active orders)
        busy = any(n.current_task for n in self.nodes.values())
        for node in self.nodes.values():
            if node.state == "IDLE" and not node.current_task:
                node.idle_timer -= dt
                if node.idle_timer <= 0 and not busy:
                    tgt = random.choice(NAV.safe_spots)
                    if all(math.hypot(o.x - tgt[0], o.z - tgt[1]) > MIN_SEP for o in self.nodes.values() if o.id != node.id):
                        self.assign_corridor_route(node, [tgt])
                    node.idle_timer = random.uniform(14, 28)
                elif node.idle_timer <= 0:
                    node.idle_timer = random.uniform(8, 16)

            self._advance_node(node, dt)

        # Clamp out of racks
        for n in self.nodes.values():
            if not NAV.is_free(n.x, n.z):
                n.x, n.z = NAV.nearest_free(n.x, n.z)

        self.active_tasks = [t for t in self.active_tasks if t.get("status") == "ASSIGNED"]

    def get_zenoh_mesh_topology(self) -> List[Dict]:
        links = []
        keys = list(self.nodes)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                n1, n2 = self.nodes[keys[i]], self.nodes[keys[j]]
                d = math.hypot(n1.x - n2.x, n1.z - n2.z)
                if d < 20:
                    links.append(
                        {
                            "source": n1.id,
                            "target": n2.id,
                            "distance": round(d, 1),
                            "latency_ms": round(1.2 + d / 20 * 1.8, 2),
                            "rssi": round(-48 - d / 20 * 28, 1),
                            "topic": f"zenoh/amr/{n1.id}_{n2.id}",
                        }
                    )
        return links

    def get_telemetry_payload(self) -> Dict:
        return {
            "timestamp": time.time(),
            "sim_time": round(self.sim_time, 2),
            "fleet_status": "EMERGENCY_STOP" if self.emergency_stop else "NOMINAL",
            "raft_consensus": {"leader_id": self.raft_leader_id, "term": self.raft_term, "status": "CONVERGED"},
            "warehouse": WAREHOUSE_CONFIG,
            "obstacles": self.dynamic_obstacles,
            "zenoh_links": self.get_zenoh_mesh_topology(),
            "agents": {
                nid: {
                    "id": n.id,
                    "x": round(n.x, 3),
                    "y": round(n.y, 3),
                    "z": round(n.z, 3),
                    "heading": round(n.heading, 3),
                    "target_x": round(n.target_x, 3),
                    "target_z": round(n.target_z, 3),
                    "velocity": round(n.velocity, 2),
                    "state": n.state,
                    "priority": n.priority,
                    "battery": round(n.battery, 1),
                    "has_payload": n.has_payload,
                    "payload_weight": n.payload_weight,
                    "is_raft_leader": n.is_raft_leader,
                    "lidar_angle": round(n.lidar_angle, 3),
                    "lidar_range": n.lidar_range,
                    "corridor": n.corridor[:18],
                    "wait_for": n.wait_for,
                    "current_task": (
                        {
                            "id": n.current_task["id"],
                            "type": n.current_task.get("type"),
                            "stage": n.current_task.get("stage"),
                            "pickup_id": n.current_task.get("pickup_id"),
                            "drop_id": n.current_task.get("drop_id"),
                        }
                        if n.current_task
                        else None
                    ),
                }
                for nid, n in self.nodes.items()
            },
            "active_tasks": [
                {
                    "id": t["id"],
                    "type": t.get("type"),
                    "pickup_id": t.get("pickup_id"),
                    "drop_id": t.get("drop_id"),
                    "urgency": t.get("urgency"),
                    "weight": t.get("weight"),
                    "stage": t.get("stage"),
                    "status": t.get("status"),
                    "assigned_to": t.get("assigned_to"),
                    "winning_bid": t.get("winning_bid"),
                    "bids": t.get("bids", {}),
                }
                for t in self.active_tasks
                if t.get("status") == "ASSIGNED"
            ],
            "recent_auctions": self.auction_history[:5],
            "event_log": self.event_log[:18],
        }


swarm = SwarmMeshController()
CLIENTS: set = set()
_sim_task: Optional[asyncio.Task] = None


def handle_command(cmd: Dict):
    t = cmd.get("type")
    if t == "TRIGGER_INTERSECTION":
        swarm.trigger_intersection_scenario()
    elif t == "TRIGGER_DEADLOCK":
        swarm.trigger_deadlock_scenario()
    elif t == "SPAWN_OBSTACLE":
        swarm.toggle_obstacle()
    elif t == "AUCTION_TASK":
        swarm.auction_task()
    elif t == "CREATE_ORDER":
        swarm.create_order(
            cmd.get("order_type", "DELIVER"),
            cmd.get("pickup_id", "PICKUP-1"),
            cmd.get("drop_id", "DROP-1"),
            cmd.get("urgency", 2),
            cmd.get("weight", 10.0),
        )
    elif t == "TOGGLE_EMERGENCY_STOP":
        swarm.emergency_stop = not swarm.emergency_stop
    elif t == "RESET":
        swarm.__init__()
    elif t == "SET_GOAL":
        aid = cmd.get("agent_id")
        if aid in swarm.nodes:
            swarm.assign_corridor_route(swarm.nodes[aid], [(float(cmd.get("x", 0)), float(cmd.get("z", 0)))])


async def simulation_loop():
    last = time.time()
    while True:
        now = time.time()
        dt = min(0.05, max(0.01, now - last))
        last = now
        try:
            swarm.step(dt)
            if CLIENTS:
                payload = json.dumps(swarm.get_telemetry_payload())
                dead = []
                for ws in list(CLIENTS):
                    try:
                        await ws.send(payload)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    CLIENTS.discard(ws)
        except Exception as e:
            print("Sim loop error:", e)
        await asyncio.sleep(0.02)


async def ws_handler(websocket):
    global _sim_task
    CLIENTS.add(websocket)
    if _sim_task is None or _sim_task.done():
        _sim_task = asyncio.create_task(simulation_loop())
    swarm.log_event("CONNECTION", f"Visualizer connected ({len(CLIENTS)}).")
    try:
        async for raw in websocket:
            try:
                handle_command(json.loads(raw))
            except Exception as e:
                print("Command error:", e)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(websocket)


async def main():
    async with websockets.serve(ws_handler, "localhost", 8765):
        print("EdgeNav Swarm Engine ws://localhost:8765")
        print("Pipeline: CNP auction | Space-Time corridors | P2P RoW | Raft WFG | ORCA")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
