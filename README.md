# EdgeNav 
### Problem Statement ID – 26123
### Problem Statement Title - Edge-AI Based Distributed Fleet Coordination for Autonomous Mobile Robots (AMRs) in Smart Warehouses


> Decentralized Multi-Agent Swarm Navigation & 3D Industrial Digital Twin  
> Developed for Smart India Hackathon (SIH 2026)

---

## Overview

EdgeNav (FleetGuard-AI) is an edge-centric, decentralized multi-agent pathfinding (MAPF) and fleet coordination framework[cite: 1, 2]. Designed for high-density industrial intralogistics, it eliminates central server single-points-of-failure by executing distributed trajectory planning, dynamic right-of-way conflict resolution, and battery-aware dispatch directly at the edge[cite: 1, 2].

The repository provides a complete 3D Digital Twin and Mission Control Dashboard built with FastAPI WebSockets and Three.js. It features real-time 25Hz telemetry streams, dynamic hazard placement, aisle deadlock scenario injection, and interactive camera tracking.

---

## Key Features

- Decentralized Swarm Coordination: Eliminates central bottlenecks using peer-to-peer spatial deconfliction, priority-weighted corridor negotiations, and autonomous state machines covering pickup, loading, transit, unloading, and charging.
- Dynamic Replanning and A* Search: Real-time 2D grid heuristic routing with dynamic obstacle consideration, immediately rerouting autonomous mobile robots (AMRs) when blocked by active hazards or peer units.
- Interactive 3D Digital Twin:
  - Three perspective modes: Isometric industrial perspective, Top-Down 2D floor view, and Chase Cam following selected AMRs.
  - Real-time trajectory visualization: Renders planned waypoint lines, dynamic LiDAR safety rings, and history trails.
  - Traffic Density Heatmap: Alpha-blended matrix tracking cumulative grid occupancy to highlight aisle bottlenecks.
  - Interactive Hazard Spawning: Raycast-driven click-to-deploy safety cones directly on warehouse aisle cells.
- Mission Control Capabilities:
  - Fleet-wide emergency stop (E-STOP) override.
  - Benchmark scenario button forcing a direct head-on aisle encounter.
  - Live incident audit feed logging state changes and conflict yields.
  - CSV export functionality for all captured telemetry and audit events.


