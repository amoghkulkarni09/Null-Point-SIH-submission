"use client";

import { useMemo } from "react";
import * as THREE from "three";
import { AMRData, ZenohLink } from "@/types/swarm";

interface Props {
  links: ZenohLink[];
  agents: Record<string, AMRData>;
  focusAgentId?: string | null;
}

export function ZenohMeshLayer({ links, agents, focusAgentId }: Props) {
  const geom = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    links.forEach((link) => {
      if (
        focusAgentId &&
        link.source !== focusAgentId &&
        link.target !== focusAgentId
      ) {
        return;
      }
      const s = agents[link.source];
      const t = agents[link.target];
      if (s && t) {
        pts.push(new THREE.Vector3(s.x, 0.55, s.z));
        pts.push(new THREE.Vector3(t.x, 0.55, t.z));
      }
    });
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [links, agents, focusAgentId]);

  if (geom.getAttribute("position")?.count === 0) return null;

  return (
    <lineSegments geometry={geom}>
      <lineBasicMaterial color="#475569" transparent opacity={0.55} />
    </lineSegments>
  );
}
