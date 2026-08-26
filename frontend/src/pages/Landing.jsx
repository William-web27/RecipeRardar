import { useNavigate } from "react-router-dom";
import { Sparkles, Salad, ChartLine, Target, ArrowRight } from "lucide-react";
import AppNav from "../components/AppNav";
import { Button } from "../components/ui/button";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
function startLogin() {
  const redirectUrl = window.location.origin + "/dashboard";
  window.location.href =
    "https://auth.emergentagent.com/?redirect=" + encodeURIComponent(redirectUrl);
}

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen relative overflow-hidden grain bg-orange-50/50">
      <div className="blob" style={{ background: "#fdba74", width: 380, height: 380, top: -80, left: -60 }} />
      <div className="blob" style={{ background: "#a7f3d0", width: 420, height: 420, top: 220, right: -140 }} />
      <div className="blob" style={{ background: "#fde68a", width: 260, height: 260, bottom: -100, left: "40%" }} />

      <div className="relative z-10">
        <AppNav />

        <section className="max-w-6xl mx-auto px-6 pt-14 pb-24 grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-orange-100 text-xs uppercase tracking-[0.15em] font-bold text-orange-600">
              <Sparkles className="h-3.5 w-3.5" /> Powered by Claude Sonnet 5
            </div>
            <h1 className="mt-6 font-display font-semibold text-5xl sm:text-6xl lg:text-7xl leading-[1.02] tracking-tight text-slate-900">
              Just say what you ate.<br />
              <span className="text-orange-600">We do the math.</span>
            </h1>
            <p className="mt-6 text-lg text-slate-600 leading-relaxed max-w-xl">
              Type any meal in plain English — &ldquo;2 eggs, toast and half an avocado&rdquo; — and RecipeRadar
              breaks down calories, protein, carbs, fat and more. Track your day, hit your goals, get
              smart suggestions for the next bite.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button
                onClick={startLogin}
                data-testid="hero-get-started-btn"
                className="rounded-full bg-orange-500 hover:bg-orange-600 text-white text-base h-12 px-7 shadow-lg shadow-orange-500/20 active:scale-95 transition-transform"
              >
                Get started free <ArrowRight className="ml-1.5 h-4 w-4" />
              </Button>
              <button
                onClick={() => navigate("/login")}
                data-testid="hero-signin-link"
                className="text-slate-700 hover:text-orange-600 font-semibold underline underline-offset-4 decoration-orange-300"
              >
                I have an account
              </button>
            </div>

            <div className="mt-10 flex items-center gap-5 text-sm text-slate-500">
              <div className="flex -space-x-2">
                <div className="h-8 w-8 rounded-full bg-orange-300 ring-2 ring-white" />
                <div className="h-8 w-8 rounded-full bg-emerald-300 ring-2 ring-white" />
                <div className="h-8 w-8 rounded-full bg-yellow-300 ring-2 ring-white" />
              </div>
              <span>No calorie counting. No barcodes. Just talk about your food.</span>
            </div>
          </div>

          <div className="lg:col-span-5 relative">
            <div className="floaty absolute -top-6 -left-6 h-24 w-24 rounded-3xl bg-emerald-400 shadow-xl grid place-items-center">
              <Salad className="h-10 w-10 text-white" strokeWidth={2.5} />
            </div>
            <div className="rounded-[2rem] bg-white shadow-[0_20px_60px_rgba(249,115,22,0.15)] border border-orange-100 p-6 relative">
              <div className="text-xs font-bold uppercase tracking-[0.15em] text-slate-400">Today</div>
              <div className="mt-1 font-display text-2xl font-semibold">Lunch bowl 🍜 — analyzed</div>
              <div className="mt-5 grid grid-cols-4 gap-3">
                {[
                  ["Cal", "540", "bg-orange-100 text-orange-700"],
                  ["Protein", "32g", "bg-emerald-100 text-emerald-700"],
                  ["Carbs", "48g", "bg-yellow-100 text-yellow-800"],
                  ["Fat", "22g", "bg-sky-100 text-sky-700"],
                ].map(([l, v, c]) => (
                  <div key={l} className={`rounded-2xl p-3 ${c}`}>
                    <div className="text-[10px] uppercase font-bold tracking-widest opacity-70">{l}</div>
                    <div className="font-display text-xl font-semibold mt-1">{v}</div>
                  </div>
                ))}
              </div>
              <div className="mt-5 rounded-2xl bg-slate-50 border border-slate-100 p-4 text-sm text-slate-700 leading-relaxed">
                Solid protein hit and balanced carbs — great pre-workout fuel. Consider a small side
                of greens for extra fiber.
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {["high-protein", "balanced", "warm"].map((t) => (
                  <span key={t} className="text-xs font-bold px-3 py-1 rounded-full bg-orange-50 text-orange-700 border border-orange-100">
                    {t}
                  </span>
                ))}
              </div>
            </div>
            <div className="floaty absolute -bottom-6 -right-4 h-20 w-20 rounded-2xl bg-yellow-300 shadow-xl grid place-items-center" style={{ animationDelay: "-3s" }}>
              <Target className="h-9 w-9 text-yellow-900" strokeWidth={2.5} />
            </div>
          </div>
        </section>

        <section className="max-w-6xl mx-auto px-6 pb-24 grid md:grid-cols-3 gap-6 stagger">
          {[
            { icon: Salad, title: "Talk, don't tap", body: "Describe meals in plain English. No dropdowns, no databases to search." },
            { icon: ChartLine, title: "Daily rings", body: "Watch your calories, protein, carbs and fat fill up as the day goes on." },
            { icon: Target, title: "Smart suggestions", body: "Get 3 meal ideas any time — tailored to what's left in your daily budget." },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-3xl bg-white border border-orange-100 p-7 shadow-[0_8px_30px_rgba(0,0,0,0.03)] hover:-translate-y-1 hover:shadow-[0_16px_40px_rgba(249,115,22,0.15)] transition-transform duration-300">
              <div className="h-11 w-11 rounded-2xl bg-orange-100 text-orange-600 grid place-items-center">
                <Icon className="h-5 w-5" strokeWidth={2.5} />
              </div>
              <div className="mt-4 font-display text-xl font-semibold">{title}</div>
              <p className="mt-2 text-slate-600 leading-relaxed">{body}</p>
            </div>
          ))}
        </section>

        <footer className="border-t border-orange-100 py-8 text-center text-sm text-slate-500">
          Made with 🥑 &nbsp;·&nbsp; RecipeRadar
        </footer>
      </div>
    </div>
  );
}
