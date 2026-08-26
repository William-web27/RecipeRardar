import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

const METRICS = {
  calories: { label: "Calories",   short: "Cal",   color: "#f97316", axisWidth: 52, unit: "" },
  protein_g: { label: "Protein",    short: "Prot",  color: "#10b981", axisWidth: 36, unit: "g" },
  carbs_g:   { label: "Carbs",      short: "Carb",  color: "#eab308", axisWidth: 36, unit: "g" },
  fat_g:     { label: "Fat",        short: "Fat",   color: "#0ea5e9", axisWidth: 36, unit: "g" },
};
const KEYS = ["calories", "protein_g", "carbs_g", "fat_g"];
const STORE_KEY = "rr_trends_metrics_v1";

export default function WeeklyTrends({ trends }) {
  const [left, setLeft] = useState("calories");
  const [right, setRight] = useState("protein_g");

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        const { l, r } = JSON.parse(raw);
        if (KEYS.includes(l)) setLeft(l);
        if (KEYS.includes(r)) setRight(r);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    try { localStorage.setItem(STORE_KEY, JSON.stringify({ l: left, r: right })); } catch { /* ignore */ }
  }, [left, right]);

  if (!trends?.days?.length) return null;

  const pick = (k) => (k === right && left === k ? KEYS.find((x) => x !== k) : k);
  const leftKey = left;
  const rightKey = right === left ? pick(right) : right;

  const L = METRICS[leftKey];
  const R = METRICS[rightKey];

  const data = trends.days.map((d) => ({
    label: d.label,
    [L.label]: Math.round(d[leftKey] || 0),
    [R.label]: Math.round(d[rightKey] || 0),
  }));

  const leftGoal = trends.goals?.[leftKey];

  return (
    <div className="rounded-3xl bg-white border border-orange-100 p-6 shadow-[0_8px_30px_rgba(0,0,0,0.03)]" data-testid="weekly-trends">
      <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
        <div>
          <div className="font-display text-xl font-semibold">Last 7 days</div>
          <div className="text-sm text-slate-500">Pick any two metrics to compare</div>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold">
          <span className="flex items-center gap-1.5" style={{ color: L.color }}><span className="h-2.5 w-2.5 rounded-full" style={{ background: L.color }} /> {L.short}</span>
          <span className="flex items-center gap-1.5" style={{ color: R.color }}><span className="h-2.5 w-2.5 rounded-full" style={{ background: R.color }} /> {R.short}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-4 mb-3" data-testid="trends-metric-pickers">
        <MetricPicker
          testId="trends-left-picker"
          label="Left axis"
          value={leftKey}
          onChange={(v) => { setLeft(v); if (v === right) setRight(KEYS.find((x) => x !== v)); }}
          disabledKey={null}
        />
        <MetricPicker
          testId="trends-right-picker"
          label="Right axis"
          value={rightKey}
          onChange={setRight}
          disabledKey={leftKey}
        />
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <LineChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="#fef3e2" vertical={false} />
            <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis yAxisId="l" stroke={L.color} tickLine={false} axisLine={false} fontSize={11} width={L.axisWidth} />
            <YAxis yAxisId="r" orientation="right" stroke={R.color} tickLine={false} axisLine={false} fontSize={11} width={R.axisWidth} />
            <Tooltip
              contentStyle={{ borderRadius: 12, border: "1px solid #fed7aa", fontFamily: "Nunito", fontSize: 12 }}
              cursor={{ stroke: "#fdba74", strokeDasharray: "4 4" }}
            />
            {leftGoal ? <ReferenceLine yAxisId="l" y={leftGoal} stroke={L.color} strokeOpacity={0.35} strokeDasharray="4 4" /> : null}
            <Line yAxisId="l" type="monotone" dataKey={L.label} stroke={L.color} strokeWidth={2.5} dot={{ r: 4, fill: L.color }} activeDot={{ r: 6 }} />
            <Line yAxisId="r" type="monotone" dataKey={R.label} stroke={R.color} strokeWidth={2.5} dot={{ r: 4, fill: R.color }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function MetricPicker({ label, value, onChange, disabledKey, testId }) {
  return (
    <div>
      <div className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-400 mb-1.5">{label}</div>
      <div className="flex flex-wrap gap-1.5" data-testid={testId} role="radiogroup" aria-label={label}>
        {KEYS.map((k) => {
          const m = METRICS[k];
          const active = k === value;
          const disabled = k === disabledKey;
          return (
            <button
              key={k}
              type="button"
              onClick={() => !disabled && onChange(k)}
              disabled={disabled}
              role="radio"
              aria-checked={active}
              data-testid={`${testId}-${k}`}
              className={
                "px-3 py-1.5 rounded-full text-xs font-bold border transition-colors " +
                (active
                  ? "text-white shadow-sm"
                  : disabled
                  ? "bg-slate-50 text-slate-300 border-slate-100 cursor-not-allowed"
                  : "bg-white text-slate-600 border-slate-200 hover:border-orange-300 hover:text-orange-600")
              }
              style={active ? { backgroundColor: m.color, borderColor: m.color } : undefined}
            >
              {m.label}{m.unit ? ` (${m.unit})` : ""}
            </button>
          );
        })}
      </div>
    </div>
  );
}
