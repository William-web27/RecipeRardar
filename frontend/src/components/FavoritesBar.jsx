import { useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Bookmark, Plus, X, Loader2 } from "lucide-react";
import { Button } from "./ui/button";

export default function FavoritesBar({ favorites, onLogged, onChanged }) {
  const [loggingId, setLoggingId] = useState(null);

  const logIt = async (f) => {
    setLoggingId(f.id);
    try {
      await api.post(`/favorites/${f.id}/log`);
      toast.success("Logged", { description: f.name });
      onLogged?.();
    } catch (e) {
      toast.error("Couldn't log", { description: e.response?.data?.detail || e.message });
    } finally {
      setLoggingId(null);
    }
  };

  const remove = async (f, ev) => {
    ev.stopPropagation();
    try {
      await api.delete(`/favorites/${f.id}`);
      onChanged?.();
    } catch (e) {
      toast.error("Delete failed", { description: e.response?.data?.detail || e.message });
    }
  };

  if (!favorites?.length) return null;

  return (
    <div className="rounded-3xl bg-white border border-orange-100 p-5 shadow-[0_8px_30px_rgba(0,0,0,0.03)]" data-testid="favorites-bar">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-8 w-8 rounded-xl bg-yellow-100 text-yellow-700 grid place-items-center">
          <Bookmark className="h-4 w-4" strokeWidth={2.5} />
        </div>
        <div>
          <div className="font-display text-lg font-semibold leading-none">Quick log</div>
          <div className="text-xs text-slate-500 mt-1">Tap to re-log a saved meal — no AI call needed.</div>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 stagger">
        {favorites.map((f) => (
          <div
            key={f.id}
            className="group relative flex items-center gap-2 rounded-full bg-orange-50 border border-orange-100 pl-1 pr-1 py-1 hover:bg-orange-100 transition-colors"
            data-testid={`favorite-${f.id}`}
          >
            <Button
              type="button"
              onClick={() => logIt(f)}
              disabled={loggingId === f.id}
              data-testid={`favorite-log-${f.id}`}
              className="rounded-full bg-white hover:bg-white text-orange-700 border-0 h-9 pl-3 pr-4 shadow-sm active:scale-95 transition-transform"
            >
              {loggingId === f.id ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Plus className="h-3.5 w-3.5 mr-1.5" />}
              <span className="font-semibold text-sm max-w-[180px] truncate">{f.name}</span>
              <span className="text-[10px] font-mono opacity-70 ml-2">{Math.round(f.nutrients?.calories || 0)}c</span>
            </Button>
            <button
              onClick={(e) => remove(f, e)}
              data-testid={`favorite-remove-${f.id}`}
              className="p-1 rounded-full text-slate-400 hover:text-red-500 focus:text-red-500 transition-colors"
              aria-label="Remove favorite"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
