# EdgeNav

### SIH Problem Statement: Edge-AI Based Distributed Fleet Coordination for Autonomous Mobile Robots (AMRs) in Smart Warehouses (ID: 26123)

EdgeNav is an industrial-grade, edge-centric multi-agent coordination platform engineered to eliminate single points of failure, communication latency bottlenecks, and traffic deadlocks in high-throughput warehouse logistics. The system replaces legacy monolithic fleet management servers with decentralized peer-to-peer (P2P) swarm intelligence, running distributed space-time corridor navigation directly onboard edge compute hardware such as the NVIDIA Jetson Orin Nano. It is architected not simply to compute shortest paths statically, but to dynamically arbitrate multi-agent right-of-way, clear aisle blockages via consensus, and execute autonomous task lifecycles in real time without cloud round-trip delays.

This repository implements a full-stack proof-of-concept and 3D digital twin prototype for the problem domain addressed in SIH 26123. The platform spans an onboard multi-agent pathfinding (MAPF) and reactive conflict resolution engine, asynchronous WebSocket telemetry broadcasting at 25 Hz, and an operator-facing interactive 3D WebGL mission control interface supporting live hazard placement, camera tracking, and telemetry audits.

---

### 1. Problem Definition

Modern automated fulfillment centers rely heavily on centralized fleet management software (FMS) architectures to coordinate dozens or hundreds of Autonomous Mobile Robots (AMRs) navigating narrow aisles and dense junction corridors.

Traditional centralized fleet controls introduce severe operational risks, such as:

* Is the central dispatch server and Wi-Fi access point bandwidth saturated?


* Does a central controller crash or network outage halt the entire warehouse floor?


* Can cloud or centralized planners respond within sub-millisecond safety windows when human workers or obstacles suddenly block a transit aisle?



However, resilient swarm navigation in practice requires answering a more complete question:

> How can autonomous robots negotiate dynamic spatial-temporal corridors peer-to-peer at the edge, guarantee continuous operation even if individual nodes or central networks disconnect, and resolve aisle deadlocks autonomously without centralized arbitration?
> 
> 

EdgeNav addresses this by modeling fleet coordination as a fully distributed, edge-native swarm system rather than relying on a brittle client-server dispatch loop.

---

### 2. Proposed Solution & Architecture

EdgeNav implements a dual-horizon spatial-temporal routing architecture that splits global path planning from decentralized local deconfliction:

* **Edge-Centric Swarm Architecture**: Full autonomy, state machines, and path calculations run on-device, targeting platforms like the Jetson Orin Nano to eliminate central infrastructure reliance.


* **Brokerless P2P Swarm Mesh**: Utilizes high-speed peer-to-peer communication (such as the Zenoh protocol) to share trajectory intents directly between neighboring robots, replacing high-overhead centralized ROS/DDS messaging.


* **Space-Time Corridor MAPF & Dynamic A***: Combines heuristic grid search with dynamic obstacle avoidance, recalculating route corridors the moment a planned path is obstructed by hazards or peer units.


* **Decentralized Right-of-Way Arbitration**: Units resolve aisle contention locally using priority metrics calculated from payload state (loaded vs. empty), task urgency, and remaining battery levels.


* **Autonomous Task & Power Lifecycle**: AMRs autonomously transition through operational states (`PICKUP` -> `LOADING` -> `TRANSIT_DELIVERY` -> `UNLOADING` -> `CHARGING`), monitoring power draw and rerouting to inductive docks when reserves deplete below safety margins.



```
+--------------------------------------------------------------------------+
|                        EdgeNav Edge Architecture                         |
|                                                                          |
|   +------------------------------------------------------------------+   |
|   | Global Spatial Corridors: Space-Time A* Reservation Vectors      |   |
|   +------------------------------------------------------------------+   |
|                                     |                                    |
|   +------------------------------------------------------------------+   |
|   | P2P Mesh Collision Avoidance: Priority Yielding & Wait Timing     |   |
|   | (Prio = Cargo Status + Low-Battery Urgency - Unit Tiebreak)      |   |
|   +------------------------------------------------------------------+   |
|                                     |                                    |
|   +------------------------------------------------------------------+   |
|   | Dynamic Replanning: Onboard Obstacle Expansion & Corridor Shift  |   |
|   +------------------------------------------------------------------+   |
+--------------------------------------------------------------------------+

```

---

### 3. Innovation & Uniqueness

Compared to conventional centralized warehouse management systems, EdgeNav delivers distinct architectural advantages:

| Feature | Legacy Centralized FMS | EdgeNav Distributed Swarm |
| --- | --- | --- |
| **System Architecture** | Central server / Master-worker dispatch

 | Serverless P2P swarm mesh

 |
| **Failure Tolerance** | Single point of failure (server failure stops fleet)

 | Zero fleet downtime; graceful node degradation

 |
| **Decision Latency** | High Wi-Fi / cloud round-trip delay

 | Sub-millisecond edge inference onboard Jetson Nano

 |
| **Deadlock Mitigation** | Centralized stop commands or manual operator clearing

 | Decentralized corridor clearance and priority yielding

 |
| **Scalability** | Network bandwidth saturates as fleet count scales

 | Scalable P2P localized communication

 |

---

### 4. Interactive 3D Digital Twin & Mission Control

The included digital twin provides a high-fidelity WebGL operational cockpit built with Three.js and FastAPI WebSockets, streaming state at 25 Hz:

* **Perspective Modes**: Supports Isometric industrial view, Top-Down 2D floor projection, and 3rd-Person Chase Cam tracking selected units.


* **Live Spatial Telemetry**: Real-time rendering of forward waypoint lines, LiDAR boundary rings, vehicle orientations, and historical breadcrumb trails.


* **Interactive Safety Injection**: Raycast click-to-place functionality enabling operators to spawn or remove dynamic safety barriers across any aisle in real time.


* **Head-On Deadlock Scenario**: Dedicated trigger that places opposing AMRs into a single-lane aisle conflict to benchmark dynamic yielding and alternate corridor recalculation.


* **Occupancy Heatmap**: Dynamic floor-level traffic density mapping showing congestion hot spots over time.


* **Audit Logging & Incident Export**: Real-time terminal tracking fleet events with direct CSV export capabilities for safety reporting and analytics.



---

### 5. Repository Structure

```
.
├── sim3d_interactive.py   # FastAPI server, A* planner, simulation loop & Three.js dashboard
└── README.md              # Project documentation and problem statement brief

```

---

### 6. Getting Started

#### Prerequisites

* Python 3.10+
* Git
* pip package manager

#### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/EdgeNav.git
cd EdgeNav

```

#### 2. Set up virtual environment

For Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate

```

For Windows users:

```powershell
python -m venv venv
.\venv\Scripts\activate

```

#### 3. Install required dependencies

Install all runtime libraries required for the edge simulation engine, pathfinding logic, and WebSocket communication layer:

```bash
pip install fastapi uvicorn websockets numpy

```

#### 4. Launch the simulation platform

Execute the main simulation engine to initialize the multi-agent environment and start the 25Hz broadcast loop:

```bash
python sim3d_interactive.py

```

This starts the unified backend server and serves the 3D WebGL dashboard.

#### 5. Open the mission control dashboard

Open your web browser and navigate to:

```
http://127.0.0.1:8000

```

---

### 7. Controls & Operations Guide

| Action | Control / Interaction | Description |
| --- | --- | --- |
| **Rotate View** | Left-Click + Drag | Orbits the 3D warehouse perspective

 |
| **Pan Scene** | Right-Click + Drag | Shifts the camera target horizontally and vertically

 |
| **Zoom** | Mouse Scroll | Adjusts field distance to inspection level

 |
| **Camera Viewports** | Top-Left Toolbar | Switches between Isometric, Top-Down 2D, and Bot Chase Cam

 |
| **Dynamic Hazard** | Button Toggle + Left-Click | Enables raycaster to spawn/clear safety barriers on grid cells

 |
| **Head-On Scenario** | Action Deck Button | Forces AMR-A1 and AMR-B2 into a single-lane contention test

 |
| **Heatmap View** | Action Deck Button | Overlays alpha-blended grid cells reflecting path traffic density

 |
| **Export CSV** | Action Deck Button | Downloads real-time event audit logs formatted for incident reviews

 |
| **Emergency Stop** | Red Action Button | Broadcasts immediate kinematics halt across all active fleet units

 |

---

### 8. License

This project is released under the MIT License. See the `LICENSE` file for details.
