"use client";

import { DynamicObstacle } from "@/types/swarm";

export function ObstacleEntity({ obstacle }: { obstacle: DynamicObstacle }) {
  if (!obstacle.active) return null;

  return (
    <group position={[obstacle.x, 0, obstacle.z]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <circleGeometry args={[obstacle.radius, 32]} />
        <meshBasicMaterial color="#dc2626" transparent opacity={0.12} />
      </mesh>

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0]}>
        <ringGeometry args={[obstacle.radius - 0.1, obstacle.radius, 32]} />
        <meshBasicMaterial color="#dc2626" transparent opacity={0.75} />
      </mesh>

      <mesh position={[0, 0.5, 0]}>
        <coneGeometry args={[0.22, 0.9, 12]} />
        <meshStandardMaterial color="#f97316" roughness={0.45} />
      </mesh>
      <mesh position={[0, 0.22, 0]}>
        <cylinderGeometry args={[0.18, 0.19, 0.1, 12]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
    </group>
  );
}
