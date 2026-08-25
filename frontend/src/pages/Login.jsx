import AppNav from "../components/AppNav";
import { Button } from "../components/ui/button";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function Login() {
  const startLogin = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href =
      "https://auth.emergentagent.com/?redirect=" + encodeURIComponent(redirectUrl);
  };

  return (
    <div className="min-h-screen bg-orange-50/50 relative overflow-hidden">
      <div className="blob" style={{ background: "#fdba74", width: 380, height: 380, top: -80, left: -60 }} />
      <div className="blob" style={{ background: "#a7f3d0", width: 380, height: 380, bottom: -100, right: -80 }} />
      <div className="relative z-10">
        <AppNav />
        <div className="max-w-md mx-auto px-6 pt-24">
          <div className="rounded-3xl bg-white border border-orange-100 shadow-[0_20px_60px_rgba(249,115,22,0.12)] p-8 text-center">
            <div className="mx-auto h-14 w-14 rounded-2xl bg-orange-500 text-white grid place-items-center text-2xl font-display font-bold">
              P
            </div>
            <h1 className="mt-5 font-display text-3xl font-semibold">Welcome back</h1>
            <p className="mt-2 text-slate-600">Sign in with Google to keep tracking your meals.</p>
            <Button
              onClick={startLogin}
              data-testid="login-google-btn"
              className="mt-6 w-full h-12 rounded-full bg-orange-500 hover:bg-orange-600 text-white text-base shadow-lg shadow-orange-500/20 active:scale-95 transition-transform"
            >
              Continue with Google
            </Button>
            <p className="mt-6 text-xs text-slate-500">
              By continuing, you agree to keep eating things that at least partially resemble food.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
