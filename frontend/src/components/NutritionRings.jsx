function Ring({ label, value, goal, color, testId }) {
  const pct = Math.min(100, goal > 0 ? (value / goal) * 100 : 0);
  const r = 42;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  return (
    <div className="flex flex-col items-center" data-testid={testId}>
      <div className="relative h-28 w-28">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <circle cx="50" cy="50" r={r} fill="none" stroke="#f1f5f9" strokeWidth="10" />
          <circle
            cx="50" cy="50" r={r}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${c - dash}`}
            style={{ transition: "stroke-dasharray 700ms ease" }}
          />
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center">
            <div className="font-display text-xl font-semibold leading-none">{Math.round(value)}</div>
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-widest mt-0.5">/ {goal}</div>
          </div>
        </div>
      </div>
      <div className="mt-2 font-semibold text-sm text-slate-700">{label}</div>
    </div>
  );
}

export default function NutritionRings({ summary }) {
  if (!summary) return null;
  const { totals, goals } = summary;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="nutrition-rings">
      <Ring testId="ring-calories" label="Calories" value={totals.calories} goal={goals.calories} color="#f97316" />
      <Ring testId="ring-protein" label="Protein (g)" value={totals.protein_g} goal={goals.protein_g} color="#10b981" />
      <Ring testId="ring-carbs" label="Carbs (g)" value={totals.carbs_g} goal={goals.carbs_g} color="#eab308" />
      <Ring testId="ring-fat" label="Fat (g)" value={totals.fat_g} goal={goals.fat_g} color="#0ea5e9" />
    </div>
  );
}
