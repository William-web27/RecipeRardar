import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

export default function WeeklyTrends({ trends }) {
  if (!trends?.days?.length) return null;
  const data = trends.days.map((d) => ({
    label: d.label,
    Calories: Math.round(d.calories),
    Protein: Math.round(d.protein_g),
  }));

  return (
    <div className="rounded-3xl bg-white border border-orange-100 p-6 shadow-[0_8px_30px_rgba(0,0,0,0.03)]" data-testid="weekly-trends">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="font-display text-xl font-semibold">Last 7 days</div>
          <div className="text-sm text-slate-500">Calories & protein at a glance</div>
        </div>
        <div className="flex items-center gap-3 text-xs font-semibold">
          <span className="flex items-center gap-1.5 text-orange-600"><span className="h-2.5 w-2.5 rounded-full bg-orange-500" /> Cal</span>
          <span className="flex items-center gap-1.5 text-emerald-600"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Protein</span>
        </div>
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <LineChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid stroke="#fef3e2" vertical={false} />
            <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis yAxisId="cal" stroke="#f97316" tickLine={false} axisLine={false} fontSize={11} width={52} />
            <YAxis yAxisId="pro" orientation="right" stroke="#10b981" tickLine={false} axisLine={false} fontSize={11} width={36} />
            <Tooltip
              contentStyle={{ borderRadius: 12, border: "1px solid #fed7aa", fontFamily: "Nunito", fontSize: 12 }}
              cursor={{ stroke: "#fdba74", strokeDasharray: "4 4" }}
            />
            <ReferenceLine yAxisId="cal" y={trends.goals?.calories} stroke="#fdba74" strokeDasharray="4 4" />
            <Line yAxisId="cal" type="monotone" dataKey="Calories" stroke="#f97316" strokeWidth={2.5} dot={{ r: 4, fill: "#f97316" }} activeDot={{ r: 6 }} />
            <Line yAxisId="pro" type="monotone" dataKey="Protein" stroke="#10b981" strokeWidth={2.5} dot={{ r: 4, fill: "#10b981" }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
