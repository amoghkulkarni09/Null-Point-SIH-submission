# EdgeNav

EdgeNav is a proof-of-concept autonomous mobile robot (AMR) swarm platform for smart warehouses. It combines a Python simulation engine with a Next.js and React Three Fiber mission-control dashboard.

The project demonstrates how a fleet can coordinate at the edge instead of depending on a single central fleet manager. Simulated robots plan aisle-aware routes, reserve space-time corridors, negotiate right-of-way, clear deadlocks, avoid dynamic obstacles, and accept delivery or charging orders through a live WebSocket connection.

> This repository is a simulation and visualization prototype. It does not connect to physical robots, safety-rated hardware, or a production Zenoh deployment.

## What Is Included

### Swarm engine

[`swarm_engine.py`](swarm_engine.py) runs the current simulation backend:

- A 40 x 40 warehouse map with racks, pickup bays, drop-off docks, and charging pads.
- Five simulated AMR nodes with battery, payload, priority, task, pose, velocity, and state telemetry.
- A* route planning over free warehouse cells.
- Space-time corridor reservations with time and radius samples.
- Peer-to-peer right-of-way arbitration when corridors overlap.
- Wait-for-graph deadlock detection followed by local Raft-style leader coordination and step-back recovery.
- Local ORCA-style velocity adjustment around nearby robots and dynamic obstacles.
- Contract Net Protocol (CNP) task auctions based on marginal cost.
- JSON telemetry and command handling over a WebSocket server at `ws://localhost:8765`.

### Mission-control dashboard

[`amr-swarm-dashboard`](amr-swarm-dashboard) is the current operator interface. It renders the warehouse as an interactive 3D scene and exposes:

- Isometric, top-down, and selected-robot chase camera presets.
- Robot selection with live state, battery, payload, priority, and route details.
- Optional LiDAR, Zenoh mesh, space-time corridor, and Raft leader visual layers.
- Intersection conflict, head-on deadlock, and dynamic obstacle scenarios.
- Emergency stop and fleet reset controls.
- Delivery, express, heavy, restock, and charge order creation.
- Live task assignment and recent auction results.
- Event and audit log viewing.
- Offline local simulation fallback when the Python WebSocket engine is unavailable.

## Architecture

```text
                         JSON over WebSocket
    +------------------+       ws://localhost:8765       +----------------------+
    | Python simulator | <------------------------------> | Next.js cockpit      |
    | swarm_engine.py  |                                  | React Three Fiber   |
    |                  |                                  | operator controls   |
    +------------------+                                  +----------------------+
       | A* + corridors                                      | 3D telemetry view
       | CNP auctions                                         | scenarios and orders
       | RoW + deadlock                                        | event and fleet state
       | obstacle avoidance
```

The dashboard connects to the engine automatically. If the socket cannot be reached, it keeps the interface usable with seeded telemetry and local command handling, and retries the connection every 3.5 seconds.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer and npm
- A modern browser with WebGL support

The Python backend currently has no checked-in `requirements.txt`. Its runtime dependency is the [`websockets`](https://pypi.org/project/websockets/) package. The frontend dependencies are declared in [`amr-swarm-dashboard/package.json`](amr-swarm-dashboard/package.json) and installed with npm.

## Quick Start

Open two terminals from the repository root.

### 1. Start the swarm engine

Create and activate a virtual environment if desired, then install the backend dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install websockets
python swarm_engine.py
```

The engine listens on:

```text
ws://localhost:8765
```

On macOS or Linux, use `python3`, `source .venv/bin/activate`, and `python3 swarm_engine.py` as appropriate.

### 2. Start the dashboard

```powershell
cd amr-swarm-dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard should show a `CONNECTED` state once the Python engine is running. Starting only the dashboard is also supported; it will display its local offline simulation until the engine becomes available.

## Dashboard Controls

| Control | Behavior |
| --- | --- |
| Camera presets | Switch between isometric, top-down, and selected-agent chase views. |
| Visualization layers | Toggle LiDAR frustums, Zenoh links, space-time corridors, and Raft leader indicators. |
| Conflict | Seeds two robots with intersecting corridors to demonstrate priority arbitration. |
| Hazard | Toggles a dynamic obstacle and exercises local avoidance. |
| Deadlock | Seeds a head-on equal-priority corridor deadlock and starts the recovery protocol. |
| Stop / Resume | Toggles the simulated fleet emergency stop state. |
| Reset | Reinitializes the simulated swarm and telemetry state. |
| Create order | Submits a delivery, express, heavy, restock, or charge task for auction. |
| Robot goal | Select a robot and assign it a target point from the detail panel. |
| Audit log | Inspect recent system, dispatch, auction, hazard, scenario, safety, and consensus events. |

## WebSocket Protocol

The dashboard sends JSON commands with a `type` field. The backend accepts these command types:

```text
TRIGGER_INTERSECTION
TRIGGER_DEADLOCK
SPAWN_OBSTACLE
AUCTION_TASK
CREATE_ORDER
TOGGLE_EMERGENCY_STOP
RESET
SET_GOAL
```

`CREATE_ORDER` accepts `order_type`, `pickup_id`, `drop_id`, `urgency`, and `weight`. `SET_GOAL` accepts `agent_id`, `x`, and `z`. The engine continuously broadcasts a JSON telemetry payload containing warehouse geometry, obstacles, Zenoh-style link data, agents, active tasks, auction history, Raft status, and recent events.

## Project Layout

```text
.
├── swarm_engine.py                 # Current WebSocket swarm simulation backend
├── sim3d_interactive.py             # Older standalone FastAPI/Three.js demo
├── amr-swarm-dashboard/
│   ├── app/                         # Next.js application entry point and styles
│   ├── components/UI/               # Cockpit panels and operator controls
│   ├── components/Warehouse3D/       # React Three Fiber warehouse scene
│   ├── hooks/useSwarmWebSocket.ts    # Connection, fallback state, and commands
│   ├── types/swarm.ts                # Shared dashboard telemetry types
│   ├── package.json                  # Frontend scripts and dependencies
│   └── AGENTS.md                     # Local Next.js development guidance
└── README.md
```

## Alternate Standalone Demo

[`sim3d_interactive.py`](sim3d_interactive.py) is an earlier, self-contained FastAPI and Three.js simulation. It uses a different 24 x 24 grid model and serves its own browser page, so it is separate from the current Next.js dashboard and `swarm_engine.py` protocol.

To run it independently:

```powershell
python -m pip install fastapi uvicorn websockets
python sim3d_interactive.py
```

It serves its own legacy interface at [http://127.0.0.1:8000](http://127.0.0.1:8000). Do not run it as the backend for the Next.js dashboard; the dashboard expects `swarm_engine.py` on port `8765`.

## Frontend Development

From `amr-swarm-dashboard`:

```bash
npm run dev       # Start the development server
npm run lint      # Run ESLint
npm run build     # Create a production build
npm run start     # Serve the production build
```

The WebSocket URL is currently defined as `ws://localhost:8765` in [`useSwarmWebSocket.ts`](amr-swarm-dashboard/hooks/useSwarmWebSocket.ts). Change that constant if the engine runs on another host or port.

## Scope and Next Steps

This prototype is intended to make distributed coordination behavior observable and testable. A production system would still need hardware integration, authenticated transport, persistence, formal safety validation, real Zenoh or robotics middleware integration, deployment configuration, and automated backend/frontend tests.