"use client";

import { useEffect, useState } from "react";
import { Battery, X } from "lucide-react";
import { AMRData } from "@/types/swarm";

interface Props {
  agents: Record<string, AMRData>;
  selectedAgentId: string | null;
  onSelectAgent: (id: string | null) => void;
  onSetGoal: (agentId: string, x: number, z: number) => void;
}

export function AMRDetailSidebar({
  agents,
  selectedAgentId,
  onSelectAgent,
  onSetGoal,
}: Props) {
  const [open, setOpen] = useState(false);
  const agentList = Object.values(agents);
  const active = selectedAgentId ? agents[selectedAgentId] : null;

  useEffect(() => {
    if (selectedAgentId) setOpen(true);
  }, [selectedAgentId]);

  if (!open || !active) return null;

  return (
    <div className="absolute top-[60px] right-4 z-10 w-64 rounded-xl bg-[#0f141c]/90 backdrop-blur-md border border-white/[0.06] shadow-xl p-3 flex flex-col gap-3 text-[12px]">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-100">{active.id}</div>
          <div className="text-[11px] text-slate-500 capitalize">
            {active.state.toLowerCase().replace("_", " ")}
            {active.is_raft_leader ? " · leader" : ""}
          </div>
        </div>
        <button
          onClick={() => {
            setOpen(false);
            onSelectAgent(null);
          }}
          className="p-1 rounded-md text-slate-500 hover:text-slate-200 hover:bg-white/[0.06]"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex gap-1 flex-wrap">
        {agentList.map((a) => (
          <button
            key={a.id}
            onClick={() => onSelectAgent(a.id)}
            className={`px-2 py-1 rounded-md text-[11px] ${
              active.id === a.id
                ? "bg-[#5b9fd4]/25 text-[#9ec9eb]"
                : "text-slate-500 hover:bg-white/[0.05]"
            }`}
          >
            {a.id.replace("AMR-", "")}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-2 text-slate-400">
        <div>
          Position
          <div className="text-slate-200 mt-0.5">
            {active.x.toFixed(1)}, {active.z.toFixed(1)}
          </div>
        </div>
        <div>
          Speed
          <div className="text-slate-200 mt-0.5">{active.velocity.toFixed(2)} m/s</div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="flex items-center gap-1">
            <Battery className="w-3 h-3" /> Battery
          </span>
          <span className="text-emerald-400/90">{active.battery.toFixed(0)}%</span>
        </div>
        <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
          <div
            className="h-full rounded-full bg-emerald-500/80 transition-all"
            style={{ width: `${active.battery}%` }}
          />
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1.5">
          Send to
        </div>
        <div className="grid grid-cols-2 gap-1">
          {(
            [
              ["Inbound", -16, -16],
              ["Outbound", 16, 16],
              ["Charger", -6, 0],
              ["Center", 0, 0],
            ] as const
          ).map(([label, x, z]) => (
            <button
              key={label}
              onClick={() => onSetGoal(active.id, x, z)}
              className="px-2 py-1.5 rounded-md bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-[11px] transition-colors"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
