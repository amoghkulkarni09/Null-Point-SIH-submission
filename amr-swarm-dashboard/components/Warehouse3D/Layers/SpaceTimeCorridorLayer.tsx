"use client";

import { useMemo } from "react";
import * as THREE from "three";
import { AMRData } from "@/types/swarm";

interface Props {
  agents: Record<string, AMRData>;
  focusAgentId?: string | null;
}

const ROBOT_COLORS: Record<string, string> = {
  "AMR-101": "#0ea5e9",
  "AMR-102": "#22c55e",
  "AMR-103": "#a855f7",
  "AMR-104": "#f59e0b",
  "AMR-105": "#ef4444",
};

/**
 * L3 Space-Time Corridors — tube height encodes time (t) so overlapping
 * space at different times reads as stacked 4D envelopes, not flat collisions.
 */
export function SpaceTimeCorridorLayer({ agents, focusAgentId }: Props) {
  const corridors = useMemo(() => {
    return Object.values(agents)
      .filter((a) => a.corridor && a.corridor.length > 1)
      .filter((a) => {
        if (focusAgentId) return a.id === focusAgentId;
        return a.state !== "IDLE";
      })
      .map((amr) => {
        const t0 = amr.corridor[0].t;
        const pts = amr.corridor.map((pt) => {
          const y = 0.15 + Math.min(2.8, Math.max(0, (pt.t - t0) * 0.22));
          return new THREE.Vector3(pt.x, y, pt.z);
        });
        // prepend current pose at ground
        pts.unshift(new THREE.Vector3(amr.x, 0.12, amr.z));
        const curve = new THREE.CatmullRomCurve3(pts);
        const color = ROBOT_COLORS[amr.id] ?? "#38bdf8";
        const radius = Math.max(0.18, (amr.corridor[0].radius ?? 1.1) * 0.22);
        return {
          id: amr.id,
          curve,
          color,
          radius,
          end: pts[pts.length - 1],
          negotiating: amr.state === "NEGOTIATING" || amr.state === "YIELDING",
        };
      });
  }, [agents, focusAgentId]);

  if (corridors.length === 0) return null;

  return (
    <group>
      {corridors.map((c) => (
        <group key={`corr-${c.id}`}>
          <mesh>
            <tubeGeometry args={[c.curve, Math.max(12, Math.floor(c.curve.getLength() * 2)), c.radius, 6, false]} />
            <meshBasicMaterial
              color={c.color}
              transparent
              opacity={c.negotiating ? 0.18 : 0.32}
              depthWrite={false}
            />
          </mesh>
          <mesh position={[c.end.x, c.end.y, c.end.z]}>
            <sphereGeometry args={[0.22, 10, 10]} />
            <meshBasicMaterial color={c.color} transparent opacity={0.7} />
          </mesh>
        </group>
      ))}
    </group>
  );
}
