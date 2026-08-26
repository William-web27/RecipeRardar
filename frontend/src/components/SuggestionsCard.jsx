import { useState } from "react";
import { Button } from "./ui/button";
import { Loader2, Lightbulb } from "lucide-react";
import { toast } from "sonner";
import { callAiApi } from "../lib/aiClient";

export default function SuggestionsCard() {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);

  const fetchSuggestions = async () => {
    setLoading(true);
    try {
      const data = await callAiApi("post", "/suggestions");
      setItems(data.suggestions || []);
    } catch (e) {
      toast.error("Suggestion failed", { description: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-3xl bg-gradient-to-br from-emerald-500 to-emerald-600 text-white p-6 shadow-[0_8px_30px_rgba(16,185,129,0.25)]" data-testid="suggestions-card">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-2xl bg-white/20 grid place-items-center backdrop-blur-sm">
            <Lightbulb className="h-5 w-5" strokeWidth={2.5} />
          </div>
          <div>
            <div className="font-display text-lg font-semibold leading-none">What should I eat next?</div>
            <div className="text-xs text-emerald-50 mt-1">AI ideas based on your remaining budget</div>
          </div>
        </div>
        <Button
          onClick={fetchSuggestions}
          disabled={loading}
          data-testid="suggestions-refresh-btn"
          className="rounded-full bg-white text-emerald-700 hover:bg-emerald-50 active:scale-95 transition-transform"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : items.length ? "Refresh" : "Suggest"}
        </Button>
      </div>

      {items.length > 0 && (
        <div className="mt-4 space-y-2">
          {items.map((s, i) => (
            <div key={i} className="rounded-2xl bg-white/10 backdrop-blur-sm border border-white/15 p-3" data-testid={`suggestion-${i}`}>
              <div className="flex items-baseline justify-between gap-3">
                <div className="font-semibold">{s.title}</div>
                <div className="text-xs font-mono opacity-80 whitespace-nowrap">
                  {Math.round(s.approx_calories || 0)} kcal · {Math.round(s.approx_protein_g || 0)}p
                </div>
              </div>
              {s.why && <div className="text-xs text-emerald-50/90 mt-1 leading-relaxed">{s.why}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
