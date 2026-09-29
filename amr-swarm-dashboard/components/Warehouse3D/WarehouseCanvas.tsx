"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import * as THREE from "three";
import { useEffect, useRef } from "react";
import { SwarmTelemetryPayload, VisualLayers, CameraPreset } from "@/types/swarm";
import { WarehouseGridFloor } from "./WarehouseGridFloor";
import { WarehouseRacks } from "./WarehouseRacks";
import { WarehouseZones } from "./WarehouseZones";
import { WarehouseStructure } from "./WarehouseStructure";
import { AMREntity } from "./AMREntity";
import { ObstacleEntity } from "./ObstacleEntity";
import { LiDARFrustumLayer } from "./Layers/LiDARFrustumLayer";
import { ZenohMeshLayer } from "./Layers/ZenohMeshLayer";
import { SpaceTimeCorridorLayer } from "./Layers/SpaceTimeCorridorLayer";
import { RaftCrownLayer } from "./Layers/RaftCrownLayer";

interface Props {
  telemetry: SwarmTelemetryPayload;
  layers: VisualLayers;
  cameraPreset: CameraPreset;
  selectedAgentId: string | null;
  onSelectAgent: (id: string | null) => void;
}

function CameraRig({
  preset,
  selectedAgentId,
  telemetry,
}: {
  preset: CameraPreset;
  selectedAgentId: string | null;
  telemetry: SwarmTelemetryPayload;
}) {
  const controlsRef = useRef<any>(null);
  const settlingRef = useRef(true);

  // Only auto-frame when the preset changes — then free orbit for the user
  useEffect(() => {
    settlingRef.current = true;
  }, [preset]);

  useFrame((state, delta) => {
    if (!controlsRef.current) return;

    if (preset === "chase") {
      const id = selectedAgentId ?? telemetry.raft_consensus.leader_id ?? "AMR-101";
      const amr = telemetry.agents[id];
      if (amr) {
        const offset = new THREE.Vector3(
          amr.x - Math.sin(amr.heading) * 8,
          amr.y + 5,
          amr.z - Math.cos(amr.heading) * 8
        );
        state.camera.position.lerp(offset, Math.min(1.0, delta * 3.5));
        controlsRef.current.target.lerp(
          new THREE.Vector3(amr.x, 0.4, amr.z),
          Math.min(1.0, delta * 3.5)
        );
      }
      controlsRef.current.update();
      return;
    }

    if (!settlingRef.current) {
      controlsRef.current.update();
      return;
    }

    const damp = Math.min(1.0, delta * 2.2);
    const targetPos =
      preset === "topdown"
        ? new THREE.Vector3(0, 52, 0.05)
        : new THREE.Vector3(32, 28, 32);
    state.camera.position.lerp(targetPos, damp);
    controlsRef.current.target.lerp(new THREE.Vector3(0, 0, 0), damp);
    controlsRef.current.update();

    if (state.camera.position.distanceTo(targetPos) < 0.35) {
      settlingRef.current = false;
    }
  });

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enableDamping
      dampingFactor={0.12}
      enablePan
      screenSpacePanning
      panSpeed={1.1}
      rotateSpeed={0.75}
      zoomSpeed={1.05}
      minPolarAngle={0.15}
      maxPolarAngle={Math.PI / 2.15}
      minDistance={8}
      maxDistance={90}
      target={[0, 0, 0]}
    />
  );
}

export function WarehouseCanvas({
  telemetry,
  layers,
  cameraPreset,
  selectedAgentId,
  onSelectAgent,
}: Props) {
  const hasFocus = Boolean(selectedAgentId);

  return (
    <div className="w-full h-full relative" onClick={() => onSelectAgent(null)}>
      <Canvas
        shadows
        gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
        dpr={[1, 1.75]}
        frameloop="always"
        style={{ background: "#9aa0a8" }}
      >
        <PerspectiveCamera makeDefault position={[32, 28, 32]} fov={40} near={0.4} far={220} />
        <CameraRig
          preset={cameraPreset}
          selectedAgentId={selectedAgentId}
          telemetry={telemetry}
        />

        <color attach="background" args={["#9aa0a8"]} />
        <fog attach="fog" args={["#9aa0a8", 55, 110]} />

        <ambientLight intensity={0.55} />
        <hemisphereLight args={["#e8eef6", "#8a857c", 0.45]} />
        <directionalLight
          position={[22, 40, 14]}
          intensity={1.15}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-camera-far={90}
          shadow-camera-left={-35}
          shadow-camera-right={35}
          shadow-camera-top={35}
          shadow-camera-bottom={-35}
        />
        <directionalLight position={[-18, 20, -10]} intensity={0.35} color="#c7d2fe" />

        <WarehouseGridFloor />
        <WarehouseStructure />
        <WarehouseRacks racks={telemetry.warehouse.racks} />
        <WarehouseZones zones={telemetry.warehouse.zones} />

        {telemetry.obstacles.map((obs) => (
          <ObstacleEntity key={obs.id} obstacle={obs} />
        ))}

        {layers.l1LiDARFrustum && (
          <LiDARFrustumLayer agents={telemetry.agents} focusAgentId={selectedAgentId} />
        )}
        {layers.l2ZenohMesh && (
          <ZenohMeshLayer
            links={telemetry.zenoh_links}
            agents={telemetry.agents}
            focusAgentId={selectedAgentId}
          />
        )}
        {layers.l3SpaceTimeCorridors && (
          <SpaceTimeCorridorLayer
            agents={telemetry.agents}
            focusAgentId={selectedAgentId}
          />
        )}
        {layers.l4RaftCrown && (
          <RaftCrownLayer
            agents={telemetry.agents}
            leaderId={telemetry.raft_consensus.leader_id}
            term={telemetry.raft_consensus.term}
          />
        )}

        {Object.values(telemetry.agents).map((amr) => (
          <AMREntity
            key={amr.id}
            amr={amr}
            isSelected={selectedAgentId === amr.id}
            isDimmed={hasFocus && selectedAgentId !== amr.id}
            onSelect={onSelectAgent}
          />
        ))}
      </Canvas>

      {/* Navigation hint — keep clear of order panel */}
      <div className="pointer-events-none absolute top-[60px] right-4 z-10 max-w-[11rem] px-2.5 py-2 rounded-lg bg-[#0f141c]/75 text-[10px] text-slate-400 backdrop-blur-sm border border-white/10 leading-relaxed">
        <div className="text-slate-200 font-medium mb-1">Camera</div>
        Drag orbit · Right-drag pan · Scroll zoom · View presets re-frame once
      </div>
    </div>
  );
}
