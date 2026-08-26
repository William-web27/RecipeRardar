import { useEffect, useState } from "react";
import { Flame } from "lucide-react";

function Confetti() {
  const pieces = Array.from({ length: 24 });
  const colors = ["#f97316", "#10b981", "#eab308", "#0ea5e9", "#ec4899"];
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {pieces.map((_, i) => (
        <span
          key={i}
          className="absolute block rounded-sm"
          style={{
            left: `${(i * 4.2) % 100}%`,
            top: "-10%",
            width: 6 + (i % 4),
            height: 10 + (i % 5),
            background: colors[i % colors.length],
            transform: `rotate(${i * 17}deg)`,
            animation: `fall 1.4s ${i * 0.03}s ease-in forwards`,
            opacity: 0.9,
          }}
        />
      ))}
      <style>{`@keyframes fall { to { transform: translateY(180px) rotate(540deg); opacity: 0; } }`}</style>
    </div>
  );
}

export default function StreakBanner({ streak }) {
  const [pop, setPop] = useState(false);
  useEffect(() => {
    if (streak?.milestone) {
      setPop(true);
      const t = setTimeout(() => setPop(false), 1600);
      return () => clearTimeout(t);
    }
  }, [streak?.streak, streak?.milestone]);

  if (!streak) return null;
  const count = streak.streak || 0;
  const hitToday = streak.hit_today;

  const bg = count >= 3
    ? "bg-gradient-to-br from-orange-500 via-amber-500 to-rose-500 text-white"
    : "bg-white border border-orange-100 text-slate-800";

  return (
    <div className={`relative overflow-hidden rounded-3xl p-5 shadow-[0_8px_30px_rgba(0,0,0,0.05)] ${bg}`} data-testid="streak-banner">
      {pop && <Confetti />}
      <div className="relative flex items-center gap-4">
        <div className={`h-14 w-14 rounded-2xl grid place-items-center ${count >= 3 ? "bg-white/20 backdrop-blur-sm" : "bg-orange-100"}`}>
          <Flame className={`h-7 w-7 ${count >= 3 ? "text-white" : "text-orange-600"}`} strokeWidth={2.5} />
        </div>
        <div className="flex-1">
          <div className={`text-xs uppercase font-bold tracking-[0.15em] ${count >= 3 ? "text-white/80" : "text-orange-600"}`}>
            Protein streak
          </div>
          <div className="font-display text-3xl font-semibold leading-tight mt-0.5" data-testid="streak-count">
            {count} day{count === 1 ? "" : "s"} {count >= 3 && "🔥"}
          </div>
          <div className={`text-sm mt-1 ${count >= 3 ? "text-white/90" : "text-slate-500"}`}>
            {count === 0 && "Hit your protein goal today to start a streak."}
            {count > 0 && !hitToday && `Log more protein today to keep the ${count}-day streak alive.`}
            {count > 0 && hitToday && count < 3 && "Nice — keep it rolling."}
            {count >= 3 && hitToday && "Locked in. You're crushing it."}
          </div>
        </div>
      </div>
    </div>
  );
}
