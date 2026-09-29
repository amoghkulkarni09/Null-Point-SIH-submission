"use client";

import { Eye, Camera } from "lucide-react";
import { VisualLayers, CameraPreset } from "@/types/swarm";

interface Props {
  layers: VisualLayers;
  onToggleLayer: (layerKey: keyof VisualLayers) => void;
  cameraPreset: CameraPreset;
  onSelectCamera: (preset: CameraPreset) => void;
}

const LAYER_ITEMS: { key: keyof VisualLayers; label: string; hint: string }[] = [
  { key: "l1LiDARFrustum", label: "LiDAR", hint: "Selected / moving only" },
  { key: "l2ZenohMesh", label: "Mesh", hint: "Links for focus robot" },
  { key: "l3SpaceTimeCorridors", label: "Paths", hint: "One robot at a time" },
  { key: "l4RaftCrown", label: "Leader", hint: "Raft leader marker" },
];

const CAMERAS: { id: CameraPreset; label: string }[] = [
  { id: "isometric", label: "3D" },
  { id: "topdown", label: "Top" },
  { id: "chase", label: "Follow" },
];

const ROBOT_LEGEND = [
  { id: "101", color: "#0ea5e9" },
  { id: "102", color: "#22c55e" },
  { id: "103", color: "#a855f7" },
  { id: "104", color: "#f59e0b" },
  { id: "105", color: "#ef4444" },
];

export function LayerControlPanel({
  layers,
  onToggleLayer,
  cameraPreset,
  onSelectCamera,
}: Props) {
  return (
    <div className="absolute top-[60px] left-4 z-10 flex flex-col gap-2 w-48">
      <div className="rounded-lg bg-[#0f141c]/85 backdrop-blur-md border border-white/[0.06] p-2.5 shadow-lg">
        <div className="flex items-center gap-1.5 mb-2 text-[10px] font-medium uppercase tracking-wider text-slate-500">
          <Eye className="w-3 h-3" />
          Overlays
        </div>
        <div className="flex flex-col gap-0.5">
          {LAYER_ITEMS.map(({ key, label, hint }) => {
            const on = layers[key];
            return (
              <button
                key={key}
                onClick={() => onToggleLayer(key)}
                title={hint}
                className={`flex items-center justify-between px-2 py-1.5 rounded-md text-[12px] transition-colors ${
                  on
                    ? "bg-white/[0.08] text-slate-100"
                    : "text-slate-500 hover:text-slate-300 hover:bg-white/[0.04]"
                }`}
              >
                {label}
                <span
                  className={`w-1.5 h-1.5 rounded-full ${on ? "bg-[#5b9fd4]" : "bg-slate-700"}`}
                />
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-[10px] text-slate-600 leading-snug">
          Click a robot to focus. Overlays follow the selection.
        </p>
      </div>

      <div className="rounded-lg bg-[#0f141c]/85 backdrop-blur-md border border-white/[0.06] p-2.5 shadow-lg">
        <div className="flex items-center gap-1.5 mb-2 text-[10px] font-medium uppercase tracking-wider text-slate-500">
          <Camera className="w-3 h-3" />
          View
        </div>
        <div className="grid grid-cols-3 gap-1">
          {CAMERAS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => onSelectCamera(id)}
              className={`py-1.5 rounded-md text-[11px] transition-colors ${
                cameraPreset === id
                  ? "bg-[#5b9fd4]/25 text-[#9ec9eb]"
                  : "text-slate-500 hover:text-slate-300 hover:bg-white/[0.04]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-lg bg-[#0f141c]/85 backdrop-blur-md border border-white/[0.06] px-2.5 py-2 shadow-lg">
        <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500 mb-1.5">
          Zones
        </div>
        <div className="flex flex-col gap-1 text-[11px] text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-blue-500" /> Inbound pickup
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-violet-500" /> Outbound drop
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm bg-emerald-500" /> Charge pads
          </div>
        </div>
      </div>

      <div className="rounded-lg bg-[#0f141c]/85 backdrop-blur-md border border-white/[0.06] px-2.5 py-2 shadow-lg">
        <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500 mb-1.5">
          Robots
        </div>
        <div className="flex flex-wrap gap-1.5">
          {ROBOT_LEGEND.map(({ id, color }) => (
            <div key={id} className="flex items-center gap-1 text-[11px] text-slate-300">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
              {id}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
