// src/admin/AdminGuard.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import { auth } from "../lib/auth";

export default function AdminGuard({ children }) {
  const nav = useNavigate();
  const [ok, setOk] = useState(null);

  useEffect(() => {
    (async () => {
      if (!auth.access?.()) {
        nav("/login", { replace: true, state: { from: "/admin" } });
        return;
      }
      try {
        const r = await api.get("/backoffice/me");
        if (r.data?.is_staff) setOk(true);
        else {
          setOk(false);
          nav("/", { replace: true });
        }
      } catch {
        setOk(false);
        nav("/", { replace: true });
      }
    })();
  }, [nav]);

  if (ok === null) return <div className="p-4 text-sm text-gray-600">Checking access…</div>;
  if (!ok) return null;
  return children;
}
