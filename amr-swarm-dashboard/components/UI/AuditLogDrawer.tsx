"use client";

import { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { SwarmEvent } from "@/types/swarm";

interface Props {
  events: SwarmEvent[];
}

export function AuditLogDrawer({ events }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const recent = events.slice(0, 12);

  return (
    <div className="absolute bottom-4 right-4 z-10 w-80 rounded-xl bg-[#0f141c]/90 backdrop-blur-md border border-white/[0.06] shadow-xl overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-[12px] text-slate-300 hover:bg-white/[0.03]"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="flex items-center gap-2">
          <span className="text-slate-500">Events</span>
          <span className="text-slate-400 tabular-nums">{events.length}</span>
        </span>
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
        ) : (
          <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
        )}
      </button>

      {isOpen && (
        <div className="px-3 pb-3 max-h-48 overflow-y-auto flex flex-col gap-1.5 border-t border-white/[0.05]">
          {recent.length === 0 ? (
            <div className="text-center text-slate-600 py-4 text-[11px]">No events yet</div>
          ) : (
            recent.map((evt) => (
              <div key={evt.id} className="pt-2 first:pt-2">
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span className="text-[10px] uppercase tracking-wide text-slate-500">
                    {evt.category.replace(/_/g, " ").toLowerCase()}
                  </span>
                  <span className="text-[10px] text-slate-600 tabular-nums">
                    {new Date(evt.timestamp * 1000).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </span>
                </div>
                <div className="text-[11px] text-slate-300 leading-snug">{evt.message}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
