"use client";

import {
  Zap,
  AlertOctagon,
  RefreshCw,
  Power,
  RotateCcw,
} from "lucide-react";
import { SwarmTelemetryPayload } from "@/types/swarm";

interface Props {
  telemetry: SwarmTelemetryPayload;
  onTriggerIntersection: () => void;
  onTriggerDeadlock: () => void;
  onSpawnObstacle: () => void;
  onToggleEmergencyStop: () => void;
  onReset: () => void;
}

export function ActionDeck({
  telemetry,
  onTriggerIntersection,
  onTriggerDeadlock,
  onSpawnObstacle,
  onToggleEmergencyStop,
  onReset,
}: Props) {
  const isObstacleActive = telemetry.obstacles.some((o) => o.active);
  const isEmergencyHalt = telemetry.fleet_status === "EMERGENCY_STOP";

  const btn =
    "flex items-center gap-1.5 px-3 py-2 rounded-md text-[12px] font-medium transition-colors active:scale-[0.98]";

  return (
    <div className="absolute bottom-4 left-4 z-10 flex flex-wrap items-center gap-1.5 p-1.5 rounded-xl bg-[#0f141c]/85 backdrop-blur-md border border-white/[0.06] shadow-lg max-w-[min(100vw-2rem,28rem)]">
      <button
        onClick={onTriggerIntersection}
        className={`${btn} text-slate-300 hover:bg-white/[0.06]`}
        title="Two robots cross the same junction"
      >
        <Zap className="w-3.5 h-3.5 text-[#5b9fd4]" />
        Conflict
      </button>

      <button
        onClick={onSpawnObstacle}
        className={`${btn} ${
          isObstacleActive
            ? "text-rose-300 bg-rose-500/10 hover:bg-rose-500/15"
            : "text-slate-300 hover:bg-white/[0.06]"
        }`}
        title="Toggle a dynamic obstacle"
      >
        <AlertOctagon className="w-3.5 h-3.5" />
        {isObstacleActive ? "Clear hazard" : "Hazard"}
      </button>

      <button
        onClick={onTriggerDeadlock}
        className={`${btn} text-slate-300 hover:bg-white/[0.06]`}
        title="Head-on aisle deadlock"
      >
        <RefreshCw className="w-3.5 h-3.5 text-amber-400/80" />
        Deadlock
      </button>

      <div className="w-px h-5 bg-white/10 mx-0.5" />

      <button
        onClick={onToggleEmergencyStop}
        className={`${btn} ${
          isEmergencyHalt
            ? "bg-rose-500/90 text-white hover:bg-rose-500"
            : "text-rose-300/90 hover:bg-rose-500/10"
        }`}
        title="Emergency stop / resume"
      >
        <Power className="w-3.5 h-3.5" />
        {isEmergencyHalt ? "Resume" : "Stop"}
      </button>

      <button
        onClick={onReset}
        className={`${btn} text-slate-500 hover:text-slate-300 hover:bg-white/[0.06]`}
        title="Reset fleet"
      >
        <RotateCcw className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
