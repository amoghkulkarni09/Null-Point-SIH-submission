"use client";

import { useState } from "react";
import { Package, X, Send } from "lucide-react";
import { CreateOrderPayload, OrderType, ActiveTask } from "@/types/swarm";

interface Props {
  activeTasks: ActiveTask[];
  onCreateOrder: (order: CreateOrderPayload) => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const ORDER_TYPES: { id: OrderType; label: string; blurb: string }[] = [
  { id: "DELIVER", label: "Deliver", blurb: "Pick up → drop off. Closest free robot usually wins." },
  { id: "EXPRESS", label: "Express", blurb: "Urgent. Prefers nearby robots; bumps their priority." },
  { id: "HEAVY", label: "Heavy", blurb: "Weight matters. High-battery robots score better." },
  { id: "RESTOCK", label: "Restock", blurb: "Bay → dock haul. Balanced scoring." },
  { id: "CHARGE", label: "Charge", blurb: "Sends the lowest-battery robot to a charger." },
];

const PICKUPS = [
  { id: "PICKUP-1", label: "Inbound Bay 1" },
  { id: "PICKUP-2", label: "Inbound Bay 2" },
];

const DROPS = [
  { id: "DROP-1", label: "Outbound Dock 1" },
  { id: "DROP-2", label: "Outbound Dock 2" },
];

const CHARGERS = [
  { id: "CHARGER-1", label: "Charger A" },
  { id: "CHARGER-2", label: "Charger B" },
];

const STAGE_LABEL: Record<string, string> = {
  TO_PICKUP: "going to pickup",
  TO_DROP: "delivering",
  TO_CHARGE: "charging",
};

export function OrderComposer({ activeTasks, onCreateOrder, open, onOpenChange }: Props) {
  const [orderType, setOrderType] = useState<OrderType>("DELIVER");
  const [pickupId, setPickupId] = useState("PICKUP-1");
  const [dropId, setDropId] = useState("DROP-1");
  const [urgency, setUrgency] = useState(2);
  const [weight, setWeight] = useState(12);

  const isCharge = orderType === "CHARGE";

  const submit = () => {
    onCreateOrder({
      order_type: orderType,
      pickup_id: isCharge ? "PICKUP-1" : pickupId,
      drop_id: isCharge ? (dropId.startsWith("CHARGER") ? dropId : "CHARGER-1") : dropId,
      urgency,
      weight: isCharge ? 0 : weight,
    });
  };

  if (!open) {
    return (
      <button
        onClick={() => onOpenChange(true)}
        className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0f141c]/90 backdrop-blur-md border border-white/[0.08] text-slate-100 text-[13px] font-medium shadow-lg hover:bg-[#151b26] transition-colors"
      >
        <Package className="w-4 h-4 text-sky-400" />
        New order
        {activeTasks.length > 0 && (
          <span className="ml-1 px-1.5 py-0.5 rounded-md bg-sky-500/20 text-sky-300 text-[11px]">
            {activeTasks.length} live
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 w-[min(100vw-2rem,26rem)] rounded-xl bg-[#0f141c]/95 backdrop-blur-md border border-white/[0.08] shadow-2xl p-3.5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-100 text-sm font-semibold">
          <Package className="w-4 h-4 text-sky-400" />
          Create order
        </div>
        <button
          onClick={() => onOpenChange(false)}
          className="p-1 rounded-md text-slate-500 hover:text-slate-200 hover:bg-white/[0.06]"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-5 gap-1">
        {ORDER_TYPES.map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setOrderType(t.id);
              if (t.id === "CHARGE") setDropId("CHARGER-1");
              else if (dropId.startsWith("CHARGER")) setDropId("DROP-1");
            }}
            className={`py-1.5 rounded-md text-[11px] font-medium transition-colors ${
              orderType === t.id
                ? "bg-sky-500/25 text-sky-200"
                : "text-slate-500 hover:bg-white/[0.05] hover:text-slate-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <p className="text-[11px] text-slate-500 leading-snug -mt-1">
        {ORDER_TYPES.find((t) => t.id === orderType)?.blurb}
      </p>

      {!isCharge && (
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
            Pickup
            <select
              value={pickupId}
              onChange={(e) => setPickupId(e.target.value)}
              className="bg-[#1a2230] border border-white/10 rounded-md px-2 py-1.5 text-[12px] text-slate-200 outline-none"
            >
              {PICKUPS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
            Drop-off
            <select
              value={dropId}
              onChange={(e) => setDropId(e.target.value)}
              className="bg-[#1a2230] border border-white/10 rounded-md px-2 py-1.5 text-[12px] text-slate-200 outline-none"
            >
              {DROPS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {isCharge && (
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
          Charger pad
          <select
            value={dropId.startsWith("CHARGER") ? dropId : "CHARGER-1"}
            onChange={(e) => setDropId(e.target.value)}
            className="bg-[#1a2230] border border-white/10 rounded-md px-2 py-1.5 text-[12px] text-slate-200 outline-none"
          >
            {CHARGERS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
      )}

      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
          Urgency {urgency}/5
          <input
            type="range"
            min={1}
            max={5}
            value={urgency}
            onChange={(e) => setUrgency(Number(e.target.value))}
            className="accent-sky-400"
          />
        </label>
        {!isCharge && (
          <label className="flex flex-col gap-1 text-[10px] uppercase tracking-wider text-slate-500">
            Weight {weight} kg
            <input
              type="range"
              min={5}
              max={60}
              step={5}
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
              className="accent-amber-400"
            />
          </label>
        )}
      </div>

      <button
        onClick={submit}
        className="flex items-center justify-center gap-2 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 text-[#0f141c] text-[13px] font-semibold transition-colors"
      >
        <Send className="w-3.5 h-3.5" />
        Dispatch to fleet
      </button>

      {activeTasks.length > 0 && (
        <div className="border-t border-white/[0.06] pt-2 flex flex-col gap-1.5 max-h-28 overflow-y-auto">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">Live orders</div>
          {activeTasks.map((t) => (
            <div
              key={t.id}
              className="flex items-center justify-between text-[11px] text-slate-300 bg-white/[0.03] rounded-md px-2 py-1.5"
            >
              <span>
                <span className="text-sky-300 font-medium">{t.assigned_to.replace("AMR-", "")}</span>
                <span className="text-slate-500 mx-1">·</span>
                {t.type}
                <span className="text-slate-500 mx-1">·</span>
                {STAGE_LABEL[t.stage || ""] || t.stage}
              </span>
              <span className="text-slate-500 tabular-nums">
                {t.pickup_id?.replace(/PICKUP-|DROP-|CHARGER-/g, "")}
                {t.type !== "CHARGE" ? `→${t.drop_id?.replace(/PICKUP-|DROP-|CHARGER-/g, "")}` : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
