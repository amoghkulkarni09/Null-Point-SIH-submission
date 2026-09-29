"use client";

import { Html } from "@react-three/drei";

/** Perimeter walls, loading-dock openings, and aisle wayfinding signs. */
export function WarehouseStructure() {
  const wallH = 5.2;
  const wallT = 0.35;
  const extent = 22.5;
  const wallColor = "#8b9099";
  const trim = "#5c6370";

  return (
    <group>
      {/* Four walls with dock cutouts on -Z and +Z */}
      {/* North wall (+Z) */}
      <mesh position={[-11, wallH / 2, extent]} castShadow receiveShadow>
        <boxGeometry args={[20, wallH, wallT]} />
        <meshStandardMaterial color={wallColor} roughness={0.9} />
      </mesh>
      <mesh position={[11, wallH / 2, extent]} castShadow receiveShadow>
        <boxGeometry args={[20, wallH, wallT]} />
        <meshStandardMaterial color={wallColor} roughness={0.9} />
      </mesh>
      {/* Dock header bar */}
      <mesh position={[0, wallH - 0.4, extent]} castShadow>
        <boxGeometry args={[8, 0.8, wallT + 0.1]} />
        <meshStandardMaterial color={trim} roughness={0.7} />
      </mesh>

      {/* South wall (-Z) */}
      <mesh position={[-11, wallH / 2, -extent]} castShadow receiveShadow>
        <boxGeometry args={[20, wallH, wallT]} />
        <meshStandardMaterial color={wallColor} roughness={0.9} />
      </mesh>
      <mesh position={[11, wallH / 2, -extent]} castShadow receiveShadow>
        <boxGeometry args={[20, wallH, wallT]} />
        <meshStandardMaterial color={wallColor} roughness={0.9} />
      </mesh>
      <mesh position={[0, wallH - 0.4, -extent]} castShadow>
        <boxGeometry args={[8, 0.8, wallT + 0.1]} />
        <meshStandardMaterial color={trim} roughness={0.7} />
      </mesh>

      {/* East / West solid walls */}
      <mesh position={[extent, wallH / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[wallT, wallH, extent * 2]} />
        <meshStandardMaterial color={wallColor} roughness={0.9} />
      </mesh>
      <mesh position={[-extent, wallH / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[wallT, wallH, extent * 2]} />
        <meshStandardMaterial color={wallColor} roughness={0.9} />
      </mesh>

      {/* Column posts at corners */}
      {(
        [
          [extent - 0.5, extent - 0.5],
          [-extent + 0.5, extent - 0.5],
          [extent - 0.5, -extent + 0.5],
          [-extent + 0.5, -extent + 0.5],
        ] as [number, number][]
      ).map(([x, z], i) => (
        <mesh key={i} position={[x, wallH / 2, z]} castShadow>
          <boxGeometry args={[0.55, wallH, 0.55]} />
          <meshStandardMaterial color="#4b5563" metalness={0.3} roughness={0.6} />
        </mesh>
      ))}

      {/* Overhead aisle signs */}
      <AisleSign position={[0, 4.2, 0]} label="CROSS AISLE" sub="MAIN JUNCTION" />
      <AisleSign position={[-12, 4.0, 0]} label="AISLE A" sub="WEST RACKS" />
      <AisleSign position={[12, 4.0, 0]} label="AISLE B" sub="EAST RACKS" />
      <AisleSign position={[0, 4.0, -12]} label="AISLE C" sub="COLD CHAIN" />
      <AisleSign position={[0, 4.0, 12]} label="AISLE D" sub="HAZMAT" />

      {/* Dock door signs */}
      <Html position={[0, 3.2, -extent + 0.4]} center distanceFactor={30} style={{ pointerEvents: "none" }}>
        <div className="px-3 py-1 rounded bg-blue-700 text-white text-[10px] font-bold tracking-widest shadow select-none">
          INBOUND DOCKS
        </div>
      </Html>
      <Html position={[0, 3.2, extent - 0.4]} center distanceFactor={30} style={{ pointerEvents: "none" }}>
        <div className="px-3 py-1 rounded bg-violet-700 text-white text-[10px] font-bold tracking-widest shadow select-none">
          OUTBOUND DOCKS
        </div>
      </Html>
    </group>
  );
}

function AisleSign({
  position,
  label,
  sub,
}: {
  position: [number, number, number];
  label: string;
  sub: string;
}) {
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[3.2, 0.55, 0.12]} />
        <meshStandardMaterial color="#1e293b" roughness={0.5} />
      </mesh>
      <Html position={[0, 0, 0.1]} center distanceFactor={32} style={{ pointerEvents: "none" }}>
        <div className="text-center select-none whitespace-nowrap">
          <div className="text-[11px] font-bold text-amber-300 tracking-wider">{label}</div>
          <div className="text-[8px] text-slate-300">{sub}</div>
        </div>
      </Html>
    </group>
  );
}
