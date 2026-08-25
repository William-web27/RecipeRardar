import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Utensils, LogOut } from "lucide-react";
import { Button } from "./ui/button";

export default function AppNav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 bg-orange-50/80 backdrop-blur-xl border-b border-orange-100">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to={user ? "/dashboard" : "/"} className="flex items-center gap-2" data-testid="nav-brand">
          <div className="h-9 w-9 rounded-2xl bg-orange-500 text-white grid place-items-center shadow-sm">
            <Utensils className="h-5 w-5" strokeWidth={2.5} />
          </div>
          <div className="font-display font-semibold text-xl leading-none">
            Plate<span className="text-orange-600">Sense</span>
          </div>
        </Link>

        <nav className="flex items-center gap-3">
          {user ? (
            <>
              <div className="hidden sm:flex items-center gap-2 pr-2">
                {user.picture && (
                  <img src={user.picture} alt="" className="h-8 w-8 rounded-full ring-2 ring-orange-200" />
                )}
                <span className="text-sm font-semibold text-slate-700" data-testid="nav-user-name">{user.name}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                data-testid="nav-logout-btn"
                className="rounded-full text-slate-700 hover:bg-orange-100"
              >
                <LogOut className="h-4 w-4 mr-1.5" /> Logout
              </Button>
            </>
          ) : (
            <Button
              onClick={() => navigate("/login")}
              data-testid="nav-signin-btn"
              className="rounded-full bg-orange-500 hover:bg-orange-600 text-white shadow-sm"
            >
              Sign in
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}
