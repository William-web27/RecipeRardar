import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import AppNav from "../components/AppNav";
import MealChat from "../components/MealChat";
import MealHistory from "../components/MealHistory";
import NutritionRings from "../components/NutritionRings";
import GoalsDialog from "../components/GoalsDialog";
import SuggestionsCard from "../components/SuggestionsCard";
import StreakBanner from "../components/StreakBanner";
import WeeklyTrends from "../components/WeeklyTrends";

export default function Dashboard() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [meals, setMeals] = useState([]);
  const [summary, setSummary] = useState(null);
  const [goals, setGoals] = useState(null);
  const [streak, setStreak] = useState(null);
  const [trends, setTrends] = useState(null);

  useEffect(() => {
    if (!loading && !user) navigate("/login", { replace: true });
  }, [loading, user, navigate]);

  const refresh = useCallback(async () => {
    try {
      const [m, s, g, st, tr] = await Promise.all([
        api.get("/meals"),
        api.get("/nutrition/summary"),
        api.get("/goals"),
        api.get("/streak"),
        api.get("/trends/weekly"),
      ]);
      setMeals(m.data);
      setSummary(s.data);
      setGoals(g.data);
      setStreak(st.data);
      setTrends(tr.data);
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => { if (user) refresh(); }, [user, refresh]);

  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  if (loading || !user) {
    return (
      <div className="min-h-screen grid place-items-center bg-orange-50">
        <div className="h-10 w-10 rounded-full border-4 border-orange-300 border-t-orange-600 animate-spin" />
      </div>
    );
  }

  const todaysMeals = (meals || []).filter((m) => {
    const d = new Date(m.created_at);
    const now = new Date();
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  });

  return (
    <div className="min-h-screen bg-orange-50/50 relative overflow-hidden grain">
      <div className="blob" style={{ background: "#fdba74", width: 320, height: 320, top: -100, right: -80 }} />
      <div className="blob" style={{ background: "#a7f3d0", width: 360, height: 360, top: 400, left: -120 }} />

      <div className="relative z-10">
        <AppNav />
        <main className="max-w-6xl mx-auto px-6 py-8" data-testid="dashboard">
          <div className="flex items-end justify-between flex-wrap gap-4 mb-6">
            <div>
              <div className="text-xs uppercase font-bold tracking-[0.15em] text-orange-600">{today}</div>
              <h1 className="mt-1 font-display text-4xl sm:text-5xl font-semibold tracking-tight">
                Hey {user.name.split(" ")[0]}, <span className="text-orange-600">what&apos;s on the plate?</span>
              </h1>
            </div>
            <GoalsDialog goals={goals} onSaved={(g) => { setGoals(g); refresh(); }} />
          </div>

          <section className="rounded-3xl bg-white border border-orange-100 p-6 shadow-[0_8px_30px_rgba(0,0,0,0.03)] mb-6" data-testid="daily-summary">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="font-display text-xl font-semibold">Today&apos;s rings</div>
                <div className="text-sm text-slate-500">{summary?.meal_count ?? 0} meal{(summary?.meal_count ?? 0) === 1 ? "" : "s"} logged</div>
              </div>
            </div>
            <NutritionRings summary={summary} />
          </section>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <StreakBanner streak={streak} />
            <SuggestionsCard />
          </div>

          <div className="mb-6">
            <WeeklyTrends trends={trends} />
          </div>

          <div className="grid lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7 space-y-6">
              <MealChat onMealCreated={refresh} />
              <div>
                <div className="font-display text-xl font-semibold mb-3">Today&apos;s meals</div>
                <MealHistory meals={todaysMeals} onChange={refresh} />
              </div>
            </div>
            <div className="lg:col-span-5 space-y-6">
              {meals.length > todaysMeals.length && (
                <div>
                  <div className="font-display text-xl font-semibold mb-3">Earlier</div>
                  <MealHistory meals={meals.filter((m) => !todaysMeals.find((t) => t.id === m.id)).slice(0, 20)} onChange={refresh} />
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
