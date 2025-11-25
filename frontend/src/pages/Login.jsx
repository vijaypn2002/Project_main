// src/pages/Login.jsx
import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import api from "../lib/api";
import { auth } from "../lib/auth";

export default function Login() {
  const nav = useNavigate();
  const loc = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (busy) return;

    const uname = username.trim();
    const pw = password;

    if (!uname || !pw) {
      setErr("Please enter username and password.");
      return;
    }

    setErr("");
    setBusy(true);
    try {
      // JWT login (core/urls.py → /api/v1/auth/token/)
      const r = await api.post("/auth/token/", { username: uname, password: pw });
      auth.set(r.data); // expects { access, refresh }
      nav(loc.state?.from || "/my-orders", { replace: true });
    } catch (ex) {
      const data = ex?.response?.data || {};
      const msg =
        data.detail ||
        (Array.isArray(data.non_field_errors) && data.non_field_errors[0]) ||
        data.message ||
        "Invalid credentials";
      setErr(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-4 text-2xl font-bold">Login</h1>

      <form onSubmit={submit} className="space-y-3" noValidate>
        <div>
          <label htmlFor="username" className="mb-1 block text-sm text-gray-700">
            Username
          </label>
          <input
            id="username"
            className="w-full rounded border px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="yourusername"
            autoComplete="username"
            required
            disabled={busy}
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-1 block text-sm text-gray-700">
            Password
          </label>
          <div className="flex items-stretch">
            <input
              id="password"
              className="w-full rounded-l border px-3 py-2"
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              disabled={busy}
            />
            <button
              type="button"
              onClick={() => setShowPw((s) => !s)}
              className="rounded-r border border-l-0 px-3 text-sm text-gray-600"
              aria-pressed={showPw}
              aria-label={showPw ? "Hide password" : "Show password"}
              disabled={busy}
            >
              {showPw ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        {err && (
          <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {err}
          </div>
        )}

        <button
          className="w-full rounded bg-black px-4 py-2 text-white disabled:opacity-60"
          disabled={busy || !username || !password}
          type="submit"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <div className="flex items-center justify-between text-sm text-gray-600">
          <Link to="/register" className="hover:underline">
            Create account
          </Link>
          <Link to="/forgot-password" className="hover:underline">
            Forgot password?
          </Link>
        </div>
      </form>
    </div>
  );
}
