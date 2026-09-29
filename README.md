# EdgeNav // FleetGuard-AI

> **Decentralized Multi-Agent Swarm Navigation & 3D Industrial Digital Twin**  
> Developed for **Smart India Hackathon (SIH 2026)**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black?style=flat&logo=three.js&logoColor=white)](https://threejs.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📌 Overview

**EdgeNav (FleetGuard-AI)** is an edge-centric, decentralized multi-agent pathfinding (MAPF) and fleet coordination framework[cite: 1, 2]. Designed for high-density industrial intralogistics, it eliminates central server single-points-of-failure by executing distributed spatial-temporal trajectory planning, dynamic right-of-way conflict resolution, and battery-aware dispatch directly at the edge[cite: 1, 2].

The repository includes a full-featured **3D Digital Twin & Mission Control Dashboard** built with **FastAPI WebSockets** and **Three.js**, supporting real-time 25Hz telemetry streams, dynamic hazard placement, aisle deadlock scenario injection, and interactive camera tracking.

---

## 🚀 Key Features & Capabilities

- **Decentralized Swarm Intelligence**: Eliminates central dispatch bottlenecks with peer-to-peer spatial deconfliction, priority-weighted corridor negotiations, and autonomous state transitions (`PICKUP` ➔ `LOADING` ➔ `TRANSIT` ➔ `UNLOADING` ➔ `CHARGING`)[cite: 1, 2].
- **Dynamic Replanning & A\* Pathfinding**: Real-time 2D grid heuristic search with dynamic obstacle expansion, rerouting autonomous mobile robots (AMRs) immediately when blocked by active hazards or peer units.
- **Interactive 3D Digital Twin (Three.js)**:
  - **Perspective Modes**: Isometric industrial view, Top-Down 2D floor projection, and 3rd-Person Chase Cam tracking selected units.
  - **Live Trajectory Projections**: Visualizes forward waypoint paths, dynamic LiDAR safety halos, and motion trails in 3D space.
  - **Occupancy Heatmap**: Real-time traffic density matrix tracking warehouse aisle bottlenecks.
  - **Interactive Obstacle Placement**: Raycast-driven click-to-deploy safety barriers directly onto warehouse aisles.
- **Mission Control Deck**:
  - Fleet-wide emergency stop (E-STOP) toggle.
  - Head-on collision benchmark scenario trigger.
  - Incident terminal stream with timestamped conflict audits[cite: 1].
  - CSV export for fleet audit logs and incident reporting[cite: 1].

---

## 🏗️ Architecture & Concepts

EdgeNav combines global corridor routing with local decentralized conflict mitigation[cite: 1, 2]:
