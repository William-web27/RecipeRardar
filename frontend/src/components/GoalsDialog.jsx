import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Target } from "lucide-react";

export default function GoalsDialog({ goals, onSaved }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(goals || {});
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (goals) setForm(goals); }, [goals]);

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        calories: Number(form.calories) || 2000,
        protein_g: Number(form.protein_g) || 120,
        carbs_g: Number(form.carbs_g) || 250,
        fat_g: Number(form.fat_g) || 65,
      };
      const { data } = await api.put("/goals", payload);
      onSaved?.(data);
      toast.success("Goals updated");
      setOpen(false);
    } catch (e) {
      toast.error("Save failed", { description: e.response?.data?.detail || e.message });
    } finally {
      setSaving(false);
    }
  };

  const fields = [
    ["calories", "Calories (kcal)"],
    ["protein_g", "Protein (g)"],
    ["carbs_g", "Carbs (g)"],
    ["fat_g", "Fat (g)"],
  ];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          data-testid="edit-goals-btn"
          className="rounded-full border-orange-200 hover:bg-orange-100 hover:border-orange-300"
        >
          <Target className="h-4 w-4 mr-1.5" /> Edit goals
        </Button>
      </DialogTrigger>
      <DialogContent className="rounded-3xl max-w-md" data-testid="goals-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">Daily goals</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4 mt-2">
          {fields.map(([k, label]) => (
            <div key={k}>
              <Label className="text-xs uppercase font-bold tracking-widest text-slate-500">{label}</Label>
              <Input
                type="number"
                data-testid={`goal-input-${k}`}
                value={form[k] ?? ""}
                onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                className="mt-1.5 rounded-2xl border-slate-200 focus-visible:ring-orange-500/30"
              />
            </div>
          ))}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setOpen(false)} className="rounded-full">Cancel</Button>
          <Button onClick={save} disabled={saving} data-testid="goals-save-btn" className="rounded-full bg-orange-500 hover:bg-orange-600 text-white">
            {saving ? "Saving…" : "Save goals"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
