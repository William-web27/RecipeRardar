import { useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Send, Loader2, Sparkles } from "lucide-react";
import { Textarea } from "./ui/textarea";
import { Button } from "./ui/button";

const EXAMPLES = [
  "2 scrambled eggs and a slice of whole wheat toast",
  "Chicken caesar salad with croutons",
  "Bowl of oatmeal with banana and peanut butter",
  "Large latte and a chocolate croissant",
];

export default function MealChat({ onMealCreated }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    const desc = text.trim();
    if (!desc || loading) return;
    setLoading(true);
    try {
      const { data } = await api.post("/meals", { description: desc });
      toast.success("Meal analyzed", { description: data.summary });
      setText("");
      onMealCreated?.(data);
    } catch (e) {
      toast.error("Couldn't analyze meal", { description: e.response?.data?.detail || e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-3xl bg-white border border-orange-100 shadow-[0_8px_30px_rgba(0,0,0,0.03)] p-6" data-testid="meal-chat">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-9 w-9 rounded-2xl bg-emerald-500 text-white grid place-items-center">
          <Sparkles className="h-4.5 w-4.5" strokeWidth={2.5} />
        </div>
        <div>
          <div className="font-display text-lg font-semibold leading-none">Tell me what you ate</div>
          <div className="text-xs text-slate-500 mt-1">Plain English works. Portions help but aren&apos;t required.</div>
        </div>
      </div>

      <Textarea
        data-testid="meal-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit();
        }}
        placeholder="e.g. Two eggs, half an avocado on sourdough, and a black coffee"
        className="min-h-[96px] resize-none rounded-2xl border-slate-200 focus-visible:ring-orange-500/30 text-base"
      />

      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setText(ex)}
            data-testid={`meal-example-${ex.slice(0, 10)}`}
            className="text-xs font-semibold px-3 py-1.5 rounded-full bg-orange-50 text-orange-700 border border-orange-100 hover:bg-orange-100 transition-colors"
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="mt-4 flex justify-end">
        <Button
          onClick={submit}
          disabled={loading || !text.trim()}
          data-testid="meal-analyze-btn"
          className="rounded-full bg-orange-500 hover:bg-orange-600 text-white h-11 px-6 active:scale-95 transition-transform"
        >
          {loading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Analyzing…</> : <><Send className="h-4 w-4 mr-2" /> Analyze meal</>}
        </Button>
      </div>
    </div>
  );
}
