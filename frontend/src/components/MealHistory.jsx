import { api } from "../lib/api";
import { toast } from "sonner";
import { Trash2, Clock, Bookmark } from "lucide-react";

function timeAgo(iso) {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}

export default function MealHistory({ meals, onChange, onFavorited, savedMealIds }) {
  const del = async (id) => {
    try {
      await api.delete(`/meals/${id}`);
      toast.success("Meal deleted");
      onChange?.();
    } catch (e) {
      toast.error("Delete failed", { description: e.response?.data?.detail || e.message });
    }
  };

  const save = async (m) => {
    if (savedMealIds?.has(m.id)) {
      toast.info("Already in favorites");
      return;
    }
    try {
      await api.post("/favorites", { meal_id: m.id });
      toast.success("Saved as favorite", { description: "One-tap re-log next time." });
      onFavorited?.();
    } catch (e) {
      toast.error("Save failed", { description: e.response?.data?.detail || e.message });
    }
  };

  if (!meals?.length) {
    return (
      <div className="rounded-3xl bg-white border border-orange-100 p-10 text-center" data-testid="meal-history-empty">
        <div className="mx-auto h-14 w-14 rounded-2xl bg-orange-100 text-orange-500 grid place-items-center">
          <Clock className="h-7 w-7" strokeWidth={2.5} />
        </div>
        <div className="mt-4 font-display text-lg font-semibold">No meals yet today</div>
        <div className="text-sm text-slate-500 mt-1">Log your first meal above to see it appear here.</div>
      </div>
    );
  }

  return (
    <div className="space-y-3 stagger" data-testid="meal-history">
      {meals.map((m) => {
        const isSaved = savedMealIds?.has(m.id);
        return (
        <div key={m.id} className="rounded-3xl bg-white border border-orange-100 p-5 shadow-[0_4px_20px_rgba(0,0,0,0.02)] hover:-translate-y-0.5 transition-transform duration-300" data-testid={`meal-card-${m.id}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="text-xs uppercase font-bold tracking-widest text-slate-400 flex items-center gap-1.5">
                <Clock className="h-3 w-3" /> {timeAgo(m.created_at)}
              </div>
              <div className="mt-1 font-semibold text-slate-800 leading-snug">{m.description}</div>
              {m.summary && <div className="mt-2 text-sm text-slate-600 leading-relaxed">{m.summary}</div>}
              <div className="mt-3 flex flex-wrap gap-2">
                {(m.tags || []).map((t) => (
                  <span key={t} className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-orange-50 text-orange-700 border border-orange-100">{t}</span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => save(m)}
                data-testid={`meal-save-${m.id}`}
                aria-pressed={isSaved}
                className={`p-2 rounded-full transition-colors ${isSaved ? "text-yellow-600 bg-yellow-50" : "text-slate-400 hover:bg-yellow-50 hover:text-yellow-600"}`}
                aria-label={isSaved ? "Already saved" : "Save as favorite"}
                title={isSaved ? "Already in favorites" : "Save as favorite"}
              >
                <Bookmark className="h-4 w-4" fill={isSaved ? "currentColor" : "none"} />
              </button>
              <button
                onClick={() => del(m.id)}
                data-testid={`meal-delete-${m.id}`}
                className="p-2 rounded-full text-slate-400 hover:bg-red-50 hover:text-red-500 transition-colors"
                aria-label="Delete meal"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-4 gap-2">
            {[
              ["Cal", Math.round(m.nutrients.calories), "bg-orange-50 text-orange-700"],
              ["Prot", `${Math.round(m.nutrients.protein_g)}g`, "bg-emerald-50 text-emerald-700"],
              ["Carb", `${Math.round(m.nutrients.carbs_g)}g`, "bg-yellow-50 text-yellow-800"],
              ["Fat", `${Math.round(m.nutrients.fat_g)}g`, "bg-sky-50 text-sky-700"],
            ].map(([l, v, c]) => (
              <div key={l} className={`rounded-xl px-3 py-2 ${c}`}>
                <div className="text-[10px] uppercase font-bold tracking-widest opacity-70">{l}</div>
                <div className="font-display text-base font-semibold">{v}</div>
              </div>
            ))}
          </div>
        </div>
        );
      })}
    </div>
  );
}
