"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { SwarmTelemetryPayload } from "@/types/swarm";

const WS_URL = "ws://localhost:8765";

// Default initial warehouse layout matching backend
const INITIAL_DATA: SwarmTelemetryPayload = {
  timestamp: Date.now() / 1000,
  fleet_status: "NOMINAL",
  raft_consensus: {
    leader_id: "AMR-101",
    term: 1,
    status: "CONVERGED"
  },
  warehouse: {
    dimensions: { width: 40, length: 40 },
    racks: [
      { id: "RACK-A1", x: -12, z: -8, w: 4, d: 8, label: "Fast Movers A1", status: "OPTIMAL" },
      { id: "RACK-A2", x: -12, z: 8, w: 4, d: 8, label: "Fast Movers A2", status: "OPTIMAL" },
      { id: "RACK-B1", x: 12, z: -8, w: 4, d: 8, label: "Bulk Storage B1", status: "OPTIMAL" },
      { id: "RACK-B2", x: 12, z: 8, w: 4, d: 8, label: "Bulk Storage B2", status: "OPTIMAL" },
      { id: "RACK-C1", x: 0, z: -12, w: 6, d: 3, label: "Cold Chain C1", status: "OPTIMAL" },
      { id: "RACK-C2", x: 0, z: 12, w: 6, d: 3, label: "Hazardous C2", status: "ATTENTION" }
    ],
    zones: [
      { id: "PICKUP-1", x: -16, z: -16, w: 5, d: 5, type: "PICKUP", label: "Inbound Bay 01" },
      { id: "PICKUP-2", x: 16, z: -16, w: 5, d: 5, type: "PICKUP", label: "Inbound Bay 02" },
      { id: "DROP-1", x: -16, z: 16, w: 5, d: 5, type: "DROP", label: "Outbound Dock 01" },
      { id: "DROP-2", x: 16, z: 16, w: 5, d: 5, type: "DROP", label: "Outbound Dock 02" },
      { id: "CHARGER-1", x: -6, z: 0, w: 3, d: 3, type: "CHARGING", label: "Inductive Pad A" },
      { id: "CHARGER-2", x: 6, z: 0, w: 3, d: 3, type: "CHARGING", label: "Inductive Pad B" }
    ]
  },
  obstacles: [
    { id: "OBS-1", x: 0.0, z: 6.0, radius: 1.4, label: "Warehouse Worker (Zone B)", active: false }
  ],
  zenoh_links: [
    { source: "AMR-101", target: "AMR-102", distance: 19.8, latency_ms: 2.1, rssi: -58, topic: "zenoh/amr/p2p/AMR-101_AMR-102" },
    { source: "AMR-101", target: "AMR-104", distance: 16.1, latency_ms: 1.8, rssi: -52, topic: "zenoh/amr/p2p/AMR-101_AMR-104" },
    { source: "AMR-102", target: "AMR-104", distance: 6.0, latency_ms: 1.3, rssi: -47, topic: "zenoh/amr/p2p/AMR-102_AMR-104" },
    { source: "AMR-103", target: "AMR-105", distance: 18.9, latency_ms: 2.4, rssi: -62, topic: "zenoh/amr/p2p/AMR-103_AMR-105" }
  ],
  agents: {
    "AMR-101": {
      id: "AMR-101", x: -14.0, y: 0, z: 0.0, heading: 0.0, target_x: -14.0, target_z: 0.0, velocity: 0.0,
      state: "IDLE", priority: 3, battery: 94.0, has_payload: false, payload_weight: 0, is_raft_leader: true,
      lidar_angle: 0.0, lidar_range: 6.0, corridor: []
    },
    "AMR-102": {
      id: "AMR-102", x: 0.0, y: 0, z: -14.0, heading: 1.57, target_x: 0.0, target_z: -14.0, velocity: 0.0,
      state: "IDLE", priority: 2, battery: 88.5, has_payload: false, payload_weight: 0, is_raft_leader: false,
      lidar_angle: 1.2, lidar_range: 6.0, corridor: []
    },
    "AMR-103": {
      id: "AMR-103", x: 14.0, y: 0, z: 4.0, heading: 3.14, target_x: 14.0, target_z: 4.0, velocity: 0.0,
      state: "IDLE", priority: 1, battery: 76.2, has_payload: false, payload_weight: 0, is_raft_leader: false,
      lidar_angle: 2.4, lidar_range: 6.0, corridor: []
    },
    "AMR-104": {
      id: "AMR-104", x: -6.0, y: 0, z: -14.0, heading: 0.0, target_x: -6.0, target_z: -14.0, velocity: 0.0,
      state: "IDLE", priority: 4, battery: 98.0, has_payload: false, payload_weight: 0, is_raft_leader: false,
      lidar_angle: 3.8, lidar_range: 6.0, corridor: []
    },
    "AMR-105": {
      id: "AMR-105", x: 8.0, y: 0, z: -14.0, heading: -1.57, target_x: 8.0, target_z: -14.0, velocity: 0.0,
      state: "IDLE", priority: 2, battery: 62.0, has_payload: false, payload_weight: 0, is_raft_leader: false,
      lidar_angle: 4.9, lidar_range: 6.0, corridor: []
    }
  },
  active_tasks: [],
  recent_auctions: [],
  event_log: [
    { id: "EVT-1001", timestamp: Date.now() / 1000, category: "SYSTEM", message: "EdgeNav Autonomous Swarm Visualizer online. P2P Mesh ready.", level: "INFO" },
    { id: "EVT-1002", timestamp: Date.now() / 1000 - 1, category: "RAFT_CONSENSUS", message: "Cluster Alpha: AMR-101 elected Raft Consensus Leader (Term 1)", level: "INFO" }
  ]
};

export function useSwarmWebSocket() {
  const [telemetry, setTelemetry] = useState<SwarmTelemetryPayload>(INITIAL_DATA);
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "connecting" | "offline_sim">("connecting");
  const [latencyMs, setLatencyMs] = useState<number>(1.8);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Send JSON command over WebSocket or emulate locally if offline
  const sendCommand = useCallback((command: Record<string, any>) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(command));
    } else {
      // Fallback local simulation handling
      handleLocalFallbackCommand(command);
    }
  }, []);

  const handleLocalFallbackCommand = (cmd: Record<string, any>) => {
    setTelemetry((prev) => {
      const next = JSON.parse(JSON.stringify(prev)) as SwarmTelemetryPayload;
      const now = Date.now() / 1000;

      if (cmd.type === "TRIGGER_INTERSECTION") {
        const n1 = next.agents["AMR-101"];
        const n2 = next.agents["AMR-102"];
        if (n1 && n2) {
          n1.x = -15.0; n1.z = 0.0; n1.state = "MOVING"; n1.priority = 3;
          n1.corridor = Array.from({ length: 30 }, (_, i) => ({
            x: -15.0 + (30.0 * (i / 29)),
            z: 0.0,
            t: i * 0.25,
            radius: 1.2
          }));
          n2.x = 0.0; n2.z = -15.0; n2.state = "MOVING"; n2.priority = 1;
          n2.corridor = Array.from({ length: 30 }, (_, i) => ({
            x: 0.0,
            z: -15.0 + (30.0 * (i / 29)),
            t: i * 0.25,
            radius: 1.2
          }));
          next.event_log.unshift({
            id: `EVT-${Date.now() % 10000}`,
            timestamp: now,
            category: "SCENARIO",
            message: "Intersection Triggered: AMR-101 (Prio 3) vs AMR-102 (Prio 1) crossing (0,0)",
            level: "INFO"
          });
        }
      } else if (cmd.type === "TRIGGER_DEADLOCK") {
        const n1 = next.agents["AMR-101"];
        const n3 = next.agents["AMR-103"];
        if (n1 && n3) {
          n1.x = -6.0; n1.z = 0.0; n1.state = "YIELDING";
          n3.x = 6.0; n3.z = 0.0; n3.state = "DEADLOCK_CLEARING";
          next.raft_consensus.term += 1;
          next.raft_consensus.leader_id = "AMR-101";
          next.event_log.unshift({
            id: `EVT-${Date.now() % 10000}`,
            timestamp: now,
            category: "DEADLOCK_PROTOCOL",
            message: "Aisle Deadlock: Raft Leader AMR-101 commanding AMR-103 step-back maneuver.",
            level: "WARNING"
          });
        }
      } else if (cmd.type === "SPAWN_OBSTACLE") {
        if (next.obstacles[0]) {
          next.obstacles[0].active = !next.obstacles[0].active;
          next.event_log.unshift({
            id: `EVT-${Date.now() % 10000}`,
            timestamp: now,
            category: "HAZARD",
            message: `Dynamic Obstacle ${next.obstacles[0].active ? "Spawned" : "Cleared"} at (0, 6)`,
            level: "INFO"
          });
        }
      } else if (cmd.type === "AUCTION_TASK") {
        const taskId = `TSK-${Math.floor(Math.random() * 9000 + 1000)}`;
        const winner = "AMR-104";
        next.active_tasks.push({
          id: taskId,
          type: "DELIVER",
          assigned_to: winner,
          status: "ASSIGNED",
          stage: "TO_PICKUP",
        });
        next.recent_auctions.unshift({
          task_id: taskId,
          bids: { "AMR-101": 24.5, "AMR-102": 19.8, "AMR-103": 31.2, "AMR-104": 12.4, "AMR-105": 28.0 },
          winner,
          winning_bid: 12.4,
          timestamp: now
        });
        next.event_log.unshift({
          id: `EVT-${Date.now() % 10000}`,
          timestamp: now,
          category: "CNP_AUCTION",
          message: `Task ${taskId} awarded to ${winner} (Lowest marginal cost 12.4)`,
          level: "INFO"
        });
      } else if (cmd.type === "TOGGLE_EMERGENCY_STOP") {
        next.fleet_status = next.fleet_status === "EMERGENCY_STOP" ? "NOMINAL" : "EMERGENCY_STOP";
        next.event_log.unshift({
          id: `EVT-${Date.now() % 10000}`,
          timestamp: now,
          category: "SAFETY",
          message: `Fleet Kinematic Halt: ${next.fleet_status}`,
          level: "ALERT"
        });
      } else if (cmd.type === "RESET") {
        return INITIAL_DATA;
      }
      return next;
    });
  };

  useEffect(() => {
    let isMounted = true;

    function connect() {
      try {
        setConnectionStatus("connecting");
        const socket = new WebSocket(WS_URL);
        wsRef.current = socket;

        socket.onopen = () => {
          if (!isMounted) return;
          console.log("[WebSocket] Connected to EdgeNav Swarm Engine:", WS_URL);
          setConnectionStatus("connected");
        };

        socket.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data) as SwarmTelemetryPayload;
            setTelemetry(data);
            // Simulate sub-5ms jitter
            setLatencyMs(parseFloat((1.4 + Math.random() * 1.8).toFixed(1)));
          } catch (err) {
            console.error("[WebSocket] Parse error:", err);
          }
        };

        socket.onerror = () => {
          // Socket error, fallback gracefully
          if (isMounted && connectionStatus !== "connected") {
            setConnectionStatus("offline_sim");
          }
        };

        socket.onclose = () => {
          if (!isMounted) return;
          setConnectionStatus("offline_sim");
          // Attempt reconnection every 3.5s
          reconnectTimeoutRef.current = setTimeout(connect, 3500);
        };
      } catch (err) {
        if (isMounted) setConnectionStatus("offline_sim");
      }
    }

    connect();

    return () => {
      isMounted = false;
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, []);

  return {
    telemetry,
    connectionStatus,
    latencyMs,
    sendCommand,
    triggerIntersection: () => sendCommand({ type: "TRIGGER_INTERSECTION" }),
    triggerDeadlock: () => sendCommand({ type: "TRIGGER_DEADLOCK" }),
    spawnObstacle: () => sendCommand({ type: "SPAWN_OBSTACLE" }),
    auctionTask: () => sendCommand({ type: "AUCTION_TASK" }),
    createOrder: (order: {
      order_type: string;
      pickup_id: string;
      drop_id: string;
      urgency: number;
      weight: number;
    }) => sendCommand({ type: "CREATE_ORDER", ...order }),
    toggleEmergencyStop: () => sendCommand({ type: "TOGGLE_EMERGENCY_STOP" }),
    resetFleet: () => sendCommand({ type: "RESET" }),
    setGoal: (agent_id: string, x: number, z: number) =>
      sendCommand({ type: "SET_GOAL", agent_id, x, z })
  };
}
