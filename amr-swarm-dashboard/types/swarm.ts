export type AMRState =
  | "IDLE"
  | "MOVING"
  | "NEGOTIATING"
  | "YIELDING"
  | "AVOIDING"
  | "DEADLOCK_CLEARING";

export interface SpaceTimeWaypoint {
  x: number;
  z: number;
  t: number;
  radius: number;
}

export interface AMRData {
  id: string;
  x: number;
  y: number;
  z: number;
  heading: number;
  target_x: number;
  target_z: number;
  velocity: number;
  state: AMRState;
  priority: number;
  battery: number;
  has_payload: boolean;
  payload_weight: number;
  is_raft_leader: boolean;
  lidar_angle: number;
  lidar_range: number;
  corridor: SpaceTimeWaypoint[];
  current_task?: {
    id: string;
    type?: string;
    stage?: string;
    pickup_id?: string;
    drop_id?: string;
  } | null;
}

export interface ZenohLink {
  source: string;
  target: string;
  distance: number;
  latency_ms: number;
  rssi: number;
  topic: string;
}

export interface DynamicObstacle {
  id: string;
  x: number;
  z: number;
  radius: number;
  label: string;
  active: boolean;
}

export interface WarehouseRack {
  id: string;
  x: number;
  z: number;
  w: number;
  d: number;
  label: string;
  status: "OPTIMAL" | "ATTENTION" | "FULL";
}

export interface WarehouseZone {
  id: string;
  x: number;
  z: number;
  w: number;
  d: number;
  type: "PICKUP" | "DROP" | "CHARGING";
  label: string;
}

export interface ActiveTask {
  id: string;
  type: string;
  pickup_id?: string;
  drop_id?: string;
  urgency?: number;
  weight?: number;
  stage?: string;
  status: string;
  assigned_to: string;
  winning_bid?: number;
  bids?: Record<string, number>;
}

export type OrderType = "DELIVER" | "EXPRESS" | "HEAVY" | "RESTOCK" | "CHARGE";

export interface CreateOrderPayload {
  order_type: OrderType;
  pickup_id: string;
  drop_id: string;
  urgency: number;
  weight: number;
}

export interface TaskAuction {
  task_id: string;
  bids: Record<string, number>;
  winner: string;
  winning_bid: number;
  timestamp: number;
}

export interface SwarmEvent {
  id: string;
  timestamp: number;
  category: "SYSTEM" | "P2P_ARBITRATION" | "RAFT_CONSENSUS" | "CNP_AUCTION" | "HAZARD" | "SCENARIO" | "SAFETY" | "CONNECTION" | "DISPATCH" | "DEADLOCK_PROTOCOL";
  message: string;
  level: "INFO" | "WARNING" | "ALERT";
}

export interface SwarmTelemetryPayload {
  timestamp: number;
  fleet_status: "NOMINAL" | "EMERGENCY_STOP" | "DEGRADED";
  raft_consensus: {
    leader_id: string;
    term: number;
    status: string;
  };
  warehouse: {
    dimensions: { width: number; length: number };
    racks: WarehouseRack[];
    zones: WarehouseZone[];
  };
  obstacles: DynamicObstacle[];
  zenoh_links: ZenohLink[];
  agents: Record<string, AMRData>;
  active_tasks: ActiveTask[];
  recent_auctions: TaskAuction[];
  event_log: SwarmEvent[];
}

export interface VisualLayers {
  l1LiDARFrustum: boolean;
  l2ZenohMesh: boolean;
  l3SpaceTimeCorridors: boolean;
  l4RaftCrown: boolean;
}

export type CameraPreset = "isometric" | "topdown" | "chase";
