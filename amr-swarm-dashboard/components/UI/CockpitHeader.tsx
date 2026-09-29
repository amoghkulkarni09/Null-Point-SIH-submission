"use client";

import { Wifi } from "lucide-react";
import { SwarmTelemetryPayload } from "@/types/swarm";

interface Props {
  telemetry: SwarmTelemetryPayload;
  connectionStatus: "connected" | "connecting" | "offline_sim";
  latencyMs: number;
}

export function CockpitHeader({ telemetry, connectionStatus, latencyMs }: Props) {
  const agents = Object.values(telemetry.agents);
  const moving = agents.filter((a) => a.state === "MOVING").length;
  const isHalt = telemetry.fleet_status === "EMERGENCY_STOP";

  return (
    <header className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between gap-4 px-5 py-3 bg-[#0f141c]/75 backdrop-blur-md border-b border-white/[0.06]">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-8 h-8 rounded-md bg-[#1a2230] border border-white/10 flex items-center justify-center shrink-0">
          <div className="w-2.5 h-2.5 rounded-full bg-[#5b9fd4]" />
        </div>
        <div className="min-w-0">
          <h1 className="text-sm font-semibold tracking-tight text-slate-100">
            EdgeNav
          </h1>
          <p className="text-[11px] text-slate-500 truncate">AMR swarm simulation</p>
        </div>
      </div>

      <div className="hidden sm:flex items-center gap-5 text-[12px] text-slate-400">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${isHalt ? "bg-rose-400" : "bg-emerald-400"}`}
          />
          <span className={isHalt ? "text-rose-300 font-medium" : "text-slate-300"}>
            {isHalt ? "Halted" : "Nominal"}
          </span>
        </div>
        <span>
          <span className="text-slate-200 font-medium">{agents.length}</span> robots
          {moving > 0 && (
            <span className="text-slate-500"> · {moving} moving</span>
          )}
        </span>
        <span className="text-slate-500">
          Leader{" "}
          <span className="text-slate-300">
            {telemetry.raft_consensus.leader_id.replace("AMR-", "")}
          </span>
        </span>
      </div>

      <div className="flex items-center gap-2 text-[11px] text-slate-400 shrink-0">
        <Wifi
          className={`w-3.5 h-3.5 ${
            connectionStatus === "connected" ? "text-emerald-400" : "text-amber-400/80"
          }`}
        />
        <span className={connectionStatus === "connected" ? "text-emerald-400/90" : "text-amber-300"}>
          {connectionStatus === "connected"
            ? `Live · ${latencyMs}ms`
            : connectionStatus === "connecting"
            ? "Connecting…"
            : "Offline (logic disabled)"}
        </span>
      </div>
    </header>
  );
}
