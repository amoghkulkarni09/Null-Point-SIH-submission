"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group } from "three";
import { AMRData } from "@/types/swarm";

interface Props {
  agents: Record<string, AMRData>;
  focusAgentId?: string | null;
}

export function LiDARFrustumLayer({ agents, focusAgentId }: Props) {
  const groupRef = useRef<Group>(null);

  useFrame((_, delta) => {
    groupRef.current?.children.forEach((child) => {
      const ray = child.children[0];
      if (ray) ray.rotation.y += delta * 4.0;
    });
  });

  const list = Object.values(agents).filter((a) => {
    if (focusAgentId) return a.id === focusAgentId;
    return a.state !== "IDLE";
  });

  return (
    <group ref={groupRef}>
      {list.map((amr) => {
        const range = amr.lidar_range ?? 5.5;
        return (
          <group key={`lidar-${amr.id}`} position={[amr.x, 0.45, amr.z]}>
            <mesh rotation={[0, amr.lidar_angle, 0]}>
              <cylinderGeometry args={[0.015, 0.015, range, 4]} />
              <meshBasicMaterial color="#0284c7" transparent opacity={0.45} />
            </mesh>
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.4, 0]}>
              <ringGeometry args={[range - 0.05, range, 36]} />
              <meshBasicMaterial color="#0284c7" transparent opacity={0.18} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}
