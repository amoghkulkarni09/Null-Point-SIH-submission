"use client";

import { useState } from "react";
import { useSwarmWebSocket } from "@/hooks/useSwarmWebSocket";
import { VisualLayers, CameraPreset } from "@/types/swarm";
import { WarehouseCanvas } from "@/components/Warehouse3D/WarehouseCanvas";
import { CockpitHeader } from "@/components/UI/CockpitHeader";
import { LayerControlPanel } from "@/components/UI/LayerControlPanel";
import { ActionDeck } from "@/components/UI/ActionDeck";
import { AuditLogDrawer } from "@/components/UI/AuditLogDrawer";
import { AMRDetailSidebar } from "@/components/UI/AMRDetailSidebar";
import { OrderComposer } from "@/components/UI/OrderComposer";

export default function MissionControlDashboard() {
  const {
    telemetry,
    connectionStatus,
    latencyMs,
    triggerIntersection,
    triggerDeadlock,
    spawnObstacle,
    createOrder,
    toggleEmergencyStop,
    resetFleet,
    setGoal,
  } = useSwarmWebSocket();

  const [layers, setLayers] = useState<VisualLayers>({
    l1LiDARFrustum: false,
    l2ZenohMesh: false,
    l3SpaceTimeCorridors: true,
    l4RaftCrown: false,
  });

  const [cameraPreset, setCameraPreset] = useState<CameraPreset>("isometric");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [orderOpen, setOrderOpen] = useState(true);

  const handleToggleLayer = (layerKey: keyof VisualLayers) => {
    setLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#9aa0a8] select-none">
      <WarehouseCanvas
        telemetry={telemetry}
        layers={layers}
        cameraPreset={cameraPreset}
        selectedAgentId={selectedAgentId}
        onSelectAgent={setSelectedAgentId}
      />

      <CockpitHeader
        telemetry={telemetry}
        connectionStatus={connectionStatus}
        latencyMs={latencyMs}
      />

      <LayerControlPanel
        layers={layers}
        onToggleLayer={handleToggleLayer}
        cameraPreset={cameraPreset}
        onSelectCamera={setCameraPreset}
      />

      <ActionDeck
        telemetry={telemetry}
        onTriggerIntersection={triggerIntersection}
        onTriggerDeadlock={triggerDeadlock}
        onSpawnObstacle={spawnObstacle}
        onToggleEmergencyStop={toggleEmergencyStop}
        onReset={resetFleet}
      />

      <OrderComposer
        open={orderOpen}
        onOpenChange={setOrderOpen}
        activeTasks={telemetry.active_tasks || []}
        onCreateOrder={createOrder}
      />

      <AMRDetailSidebar
        agents={telemetry.agents}
        selectedAgentId={selectedAgentId}
        onSelectAgent={setSelectedAgentId}
        onSetGoal={setGoal}
      />

      <AuditLogDrawer events={telemetry.event_log} />
    </main>
  );
}
