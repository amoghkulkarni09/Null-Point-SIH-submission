"use client";

import { Html } from "@react-three/drei";
import { WarehouseRack } from "@/types/swarm";

interface Props {
  racks: WarehouseRack[];
}

/** Pallet / carton colors for filled shelves */
const CARGO = ["#b45309", "#92400e", "#a16207", "#78716c", "#57534e", "#1d4ed8"];

export function WarehouseRacks({ racks }: Props) {
  return (
    <group>
      {racks.map((rack) => {
        const shelves = [0.55, 1.35, 2.15, 2.95];
        return (
          <group key={rack.id} position={[rack.x, 0, rack.z]}>
            {/* Back panel */}
            <mesh position={[0, 1.7, -rack.d / 2 + 0.06]} castShadow receiveShadow>
              <boxGeometry args={[rack.w - 0.15, 3.4, 0.08]} />
              <meshStandardMaterial color="#3f4754" metalness={0.35} roughness={0.55} />
            </mesh>

            {/* Safety-orange uprights */}
            {(
              [
                [-rack.w / 2 + 0.12, -rack.d / 2 + 0.12],
                [rack.w / 2 - 0.12, -rack.d / 2 + 0.12],
                [-rack.w / 2 + 0.12, rack.d / 2 - 0.12],
                [rack.w / 2 - 0.12, rack.d / 2 - 0.12],
              ] as [number, number][]
            ).map(([bx, bz], i) => (
              <mesh key={i} position={[bx, 1.75, bz]} castShadow>
                <boxGeometry args={[0.14, 3.5, 0.14]} />
                <meshStandardMaterial color="#ea580c" roughness={0.45} metalness={0.2} />
              </mesh>
            ))}

            {/* Shelf decks + cargo */}
            {shelves.map((y, si) => (
              <group key={si}>
                <mesh position={[0, y, 0]} receiveShadow>
                  <boxGeometry args={[rack.w - 0.2, 0.08, rack.d - 0.15]} />
                  <meshStandardMaterial color="#6b7280" metalness={0.4} roughness={0.5} />
                </mesh>
                {/* Cartons / totes on each shelf */}
                {Array.from({ length: Math.max(2, Math.floor(rack.w)) }).map((_, ci) => {
                  const spacing = (rack.w - 0.6) / Math.max(1, Math.floor(rack.w) - 1 || 1);
                  const cx = -rack.w / 2 + 0.35 + ci * spacing;
                  const depth = rack.d * 0.35;
                  return (
                    <mesh
                      key={ci}
                      position={[cx, y + 0.28, -rack.d / 2 + 0.35 + (ci % 2) * 0.15]}
                      castShadow
                    >
                      <boxGeometry args={[0.55, 0.45, depth]} />
                      <meshStandardMaterial
                        color={CARGO[(si + ci) % CARGO.length]}
                        roughness={0.85}
                      />
                    </mesh>
                  );
                })}
              </group>
            ))}

            {/* Top beam */}
            <mesh position={[0, 3.45, 0]}>
              <boxGeometry args={[rack.w, 0.1, rack.d]} />
              <meshStandardMaterial color="#374151" metalness={0.3} roughness={0.5} />
            </mesh>

            {/* Status beacon */}
            <mesh position={[0, 3.65, 0]}>
              <sphereGeometry args={[0.1, 12, 12]} />
              <meshBasicMaterial
                color={rack.status === "OPTIMAL" ? "#22c55e" : "#f59e0b"}
              />
            </mesh>

            {/* Bay label */}
            <Html position={[0, 3.95, 0]} center distanceFactor={28} style={{ pointerEvents: "none" }}>
              <div className="px-2 py-1 rounded bg-slate-900/90 border border-orange-500/40 text-[10px] font-semibold text-white whitespace-nowrap shadow-lg select-none">
                <div className="text-orange-300 tracking-wide">{rack.id}</div>
                <div className="text-slate-300 font-normal text-[9px] max-w-[9rem] truncate">
                  {rack.label}
                </div>
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}
