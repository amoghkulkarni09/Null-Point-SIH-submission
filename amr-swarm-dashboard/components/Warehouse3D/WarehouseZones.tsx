"use client";

import * as THREE from "three";
import { Html } from "@react-three/drei";
import { WarehouseZone } from "@/types/swarm";

const ZONE_STYLE: Record<
  WarehouseZone["type"],
  { color: string; title: string; badge: string }
> = {
  PICKUP: { color: "#2563eb", title: "INBOUND", badge: "PICKUP" },
  DROP: { color: "#7c3aed", title: "OUTBOUND", badge: "DROP" },
  CHARGING: { color: "#059669", title: "CHARGE", badge: "PAD" },
};

export function WarehouseZones({ zones }: { zones: WarehouseZone[] }) {
  return (
    <group>
      {zones.map((zone) => {
        const style = ZONE_STYLE[zone.type];
        const color = style.color;
        return (
          <group key={zone.id} position={[zone.x, 0, zone.z]}>
            {/* Painted bay pad */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]} receiveShadow>
              <planeGeometry args={[zone.w, zone.d]} />
              <meshStandardMaterial
                color={color}
                transparent
                opacity={0.22}
                roughness={1}
              />
            </mesh>

            {/* Hatch stripes */}
            {Array.from({ length: 5 }).map((_, i) => (
              <mesh
                key={i}
                rotation={[-Math.PI / 2, 0, Math.PI / 4]}
                position={[
                  -zone.w / 2 + 0.5 + i * ((zone.w - 1) / 4),
                  0.018,
                  0,
                ]}
              >
                <planeGeometry args={[0.18, zone.d * 0.85]} />
                <meshBasicMaterial color={color} transparent opacity={0.35} />
              </mesh>
            ))}

            <lineSegments rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0]}>
              <edgesGeometry args={[new THREE.PlaneGeometry(zone.w, zone.d)]} />
              <lineBasicMaterial color={color} transparent opacity={0.85} />
            </lineSegments>

            {/* Corner ticks */}
            {(
              [
                [-zone.w / 2, -zone.d / 2],
                [zone.w / 2, -zone.d / 2],
                [-zone.w / 2, zone.d / 2],
                [zone.w / 2, zone.d / 2],
              ] as [number, number][]
            ).map(([cx, cz], i) => (
              <mesh key={i} position={[cx, 0.35, cz]}>
                <boxGeometry args={[0.12, 0.7, 0.12]} />
                <meshStandardMaterial color={color} roughness={0.4} />
              </mesh>
            ))}

            {zone.type === "CHARGING" && (
              <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.04, 0]}>
                <ringGeometry args={[0.55, 0.85, 28]} />
                <meshBasicMaterial color={color} transparent opacity={0.65} />
              </mesh>
            )}

            {/* Always-visible zone sign */}
            <Html position={[0, 1.35, 0]} center distanceFactor={26} style={{ pointerEvents: "none" }}>
              <div
                className="flex flex-col items-center select-none shadow-lg"
                style={{ minWidth: 88 }}
              >
                <div
                  className="px-2 py-0.5 text-[9px] font-bold tracking-widest text-white rounded-t"
                  style={{ backgroundColor: color }}
                >
                  {style.badge}
                </div>
                <div className="px-2.5 py-1 rounded-b bg-white/95 border border-slate-200 text-center">
                  <div className="text-[11px] font-semibold text-slate-800 leading-tight">
                    {zone.label}
                  </div>
                  <div className="text-[9px] text-slate-500">{style.title}</div>
                </div>
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}
