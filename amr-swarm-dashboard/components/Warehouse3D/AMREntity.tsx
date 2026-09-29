"use client";

import { useRef, useEffect, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { AMRData, AMRState } from "@/types/swarm";

interface Props {
  amr: AMRData;
  isSelected?: boolean;
  isDimmed?: boolean;
  onSelect?: (id: string) => void;
}

const ROBOT_COLORS: Record<string, string> = {
  "AMR-101": "#0ea5e9",
  "AMR-102": "#22c55e",
  "AMR-103": "#a855f7",
  "AMR-104": "#f59e0b",
  "AMR-105": "#ef4444",
};

const STATE_COLORS: Record<AMRState, string> = {
  IDLE: "#22c55e",           // Green
  MOVING: "#0ea5e9",         // Blue
  NEGOTIATING: "#f97316",    // Orange — P2P arbitration
  YIELDING: "#eab308",       // Yellow — corridor yield / wait
  AVOIDING: "#ef4444",       // Red — ORCA
  DEADLOCK_CLEARING: "#ec4899",
};

export function AMREntity({ amr, isSelected, isDimmed, onSelect }: Props) {
  const groupRef = useRef<THREE.Group>(null);
  const [isHovered, setIsHovered] = useState(false);
  const initializedRef = useRef(false);
  const accent = ROBOT_COLORS[amr.id] ?? "#0ea5e9";
  const stateColor = STATE_COLORS[amr.state] || STATE_COLORS.IDLE;
  const shortId = amr.id.replace("AMR-", "");
  const showDetail = isSelected || isHovered;
  const bodyColor = isDimmed ? "#c8cdd4" : "#f4f6f8";

  useEffect(() => {
    if (groupRef.current && !initializedRef.current) {
      groupRef.current.position.set(amr.x, 0, amr.z);
      groupRef.current.rotation.y = amr.heading;
      initializedRef.current = true;
    }
  }, [amr.x, amr.z, amr.heading]);

  useFrame((_, delta) => {
    if (!groupRef.current) return;

    const posDamp = Math.min(1.0, delta * 9.0);
    groupRef.current.position.x = THREE.MathUtils.lerp(groupRef.current.position.x, amr.x, posDamp);
    groupRef.current.position.z = THREE.MathUtils.lerp(groupRef.current.position.z, amr.z, posDamp);
    groupRef.current.position.y = THREE.MathUtils.lerp(groupRef.current.position.y, amr.y || 0.0, posDamp);

    let targetRot = amr.heading;
    const curRot = groupRef.current.rotation.y;
    let diff = (targetRot - curRot) % (Math.PI * 2);
    if (diff < -Math.PI) diff += Math.PI * 2;
    if (diff > Math.PI) diff -= Math.PI * 2;
    groupRef.current.rotation.y = curRot + diff * Math.min(1.0, delta * 8.0);
  });

  return (
    <group
      ref={groupRef}
      onClick={(e) => {
        e.stopPropagation();
        onSelect?.(amr.id);
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        setIsHovered(true);
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        setIsHovered(false);
        document.body.style.cursor = "auto";
      }}
    >
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.025, 0]}>
        <ringGeometry args={[0.85, 1.15, 32]} />
        <meshBasicMaterial
          color={stateColor}
          transparent
          opacity={isDimmed ? 0.2 : isSelected ? 0.9 : 0.75}
          side={THREE.DoubleSide}
        />
      </mesh>

      <group position={[0, 0.32, 0]}>
        {/* White chassis pops on concrete; accent stripe IDs the robot */}
        <mesh castShadow receiveShadow>
          <boxGeometry args={[1.2, 0.4, 1.45]} />
          <meshStandardMaterial color={bodyColor} metalness={0.15} roughness={0.45} />
        </mesh>

        <mesh position={[-0.61, 0, 0]}>
          <boxGeometry args={[0.04, 0.28, 1.3]} />
          <meshStandardMaterial color={isDimmed ? "#94a3b8" : accent} roughness={0.4} />
        </mesh>
        <mesh position={[0.61, 0, 0]}>
          <boxGeometry args={[0.04, 0.28, 1.3]} />
          <meshStandardMaterial color={isDimmed ? "#94a3b8" : accent} roughness={0.4} />
        </mesh>

        <mesh position={[0, 0.22, 0]}>
          <boxGeometry args={[1.05, 0.04, 1.25]} />
          <meshStandardMaterial color={isDimmed ? "#b0b8c4" : "#e2e8f0"} roughness={0.5} />
        </mesh>

        <mesh position={[0, 0.05, 0.74]}>
          <boxGeometry args={[0.75, 0.06, 0.03]} />
          <meshBasicMaterial color={isDimmed ? "#cbd5e1" : "#fef08a"} />
        </mesh>

        {[-0.6, 0.6].map((wx, idx) => (
          <mesh
            key={idx}
            position={[wx, -0.12, 0]}
            rotation={[0, 0, Math.PI / 2]}
            castShadow
          >
            <cylinderGeometry args={[0.17, 0.17, 0.12, 14]} />
            <meshStandardMaterial color="#1e293b" roughness={0.9} />
          </mesh>
        ))}

        <mesh position={[0, 0.32, 0.1]}>
          <sphereGeometry args={[0.16, 16, 12]} />
          <meshStandardMaterial
            color={isDimmed ? "#94a3b8" : accent}
            emissive={isDimmed ? "#000000" : accent}
            emissiveIntensity={isDimmed ? 0 : 0.35}
            roughness={0.3}
          />
        </mesh>

        {amr.has_payload && (
          <mesh position={[0, 0.42, -0.15]} castShadow>
            <boxGeometry args={[0.7, 0.35, 0.7]} />
            <meshStandardMaterial color="#92400e" roughness={0.75} />
          </mesh>
        )}
      </group>

      {/* Labels only when focused — cuts label clutter when many robots move */}
      {!isDimmed && (
        <Html position={[0, 1.25, 0]} center distanceFactor={26} style={{ pointerEvents: "none" }}>
          <div className="flex flex-col items-center select-none">
            {showDetail && (
              <div className="mb-1 px-2 py-1 rounded-md bg-white/95 border border-slate-200 text-[10px] font-medium text-slate-700 whitespace-nowrap shadow-md">
                <span style={{ color: stateColor }} className="font-semibold">
                  {amr.state}
                </span>
                <span className="text-slate-400 mx-1">·</span>
                <span>{amr.battery.toFixed(0)}%</span>
              </div>
            )}
            <div
              className={`px-2 py-0.5 rounded-md text-[11px] font-bold tracking-wide shadow-sm border ${
                isSelected
                  ? "text-white border-transparent"
                  : "bg-white text-slate-800 border-slate-200"
              }`}
              style={isSelected ? { backgroundColor: accent, borderColor: accent } : undefined}
            >
              {shortId}
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}
