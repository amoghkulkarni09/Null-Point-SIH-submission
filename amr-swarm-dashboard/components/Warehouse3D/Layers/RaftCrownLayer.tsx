"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { AMRData } from "@/types/swarm";

interface Props {
  agents: Record<string, AMRData>;
  leaderId?: string;
  term?: number;
}

export function RaftCrownLayer({ agents, leaderId = "AMR-101" }: Props) {
  const floatRef = useRef<THREE.Group>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const leader = agents[leaderId];

  useFrame((_, delta) => {
    if (!leader || !floatRef.current) return;
    const targetY = (leader.y ?? 0) + 2.2;
    floatRef.current.position.x = THREE.MathUtils.lerp(
      floatRef.current.position.x,
      leader.x,
      delta * 8
    );
    floatRef.current.position.z = THREE.MathUtils.lerp(
      floatRef.current.position.z,
      leader.z,
      delta * 8
    );
    floatRef.current.position.y = THREE.MathUtils.lerp(
      floatRef.current.position.y,
      targetY,
      delta * 4
    );
    if (ringRef.current) ringRef.current.rotation.y += delta * 0.8;
  });

  if (!leader) return null;

  return (
    <group ref={floatRef} position={[leader.x, 2.2, leader.z]}>
      <mesh ref={ringRef}>
        <torusGeometry args={[0.4, 0.03, 10, 6]} />
        <meshStandardMaterial
          color="#d4a84b"
          emissive="#a67c2a"
          emissiveIntensity={0.4}
          metalness={0.6}
          roughness={0.35}
        />
      </mesh>
      <mesh position={[0, -0.7, 0]}>
        <cylinderGeometry args={[0.01, 0.01, 1.3, 6]} />
        <meshBasicMaterial color="#d4a84b" transparent opacity={0.25} />
      </mesh>
    </group>
  );
}
