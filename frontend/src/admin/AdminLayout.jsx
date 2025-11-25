// src/admin/AdminLayout.jsx
import { Link, Outlet, useLocation } from "react-router-dom";

function NavLink({ to, children }) {
  const loc = useLocation();
  const active = loc.pathname === to;
  return (
    <Link
      to={to}
      className={`px-3 py-2 rounded ${active ? "bg-black text-white" : "border hover:bg-gray-50"}`}
    >
      {children}
    </Link>
  );
}

export default function AdminLayout() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Backoffice</h1>
        <Link to="/" className="text-sm text-indigo-600 hover:underline">← Public site</Link>
      </div>

      <div className="flex gap-2 mb-6">
        <NavLink to="/admin">Dashboard</NavLink>
        <NavLink to="/admin/banners">Banners</NavLink>
        <NavLink to="/admin/coupons">Coupons</NavLink>
      </div>

      <div className="bg-white border rounded-xl p-4">
        <Outlet />
      </div>
    </div>
  );
}
