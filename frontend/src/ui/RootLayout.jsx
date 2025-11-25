// src/ui/RootLayout.jsx
import { Link, Outlet, useNavigate } from "react-router-dom";
import { ShoppingCart, List } from "lucide-react";

import { auth } from "../lib/auth";
import Footer from "./Footer";
import SearchBar from "../components/SearchBar";

export default function RootLayout() {
  const nav = useNavigate();

  function logout() {
    auth.clear?.();
    nav("/", { replace: true });
  }

  const isAuthed = !!(auth.access?.() && auth.access());

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b bg-white/85 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 h-16 grid grid-cols-12 gap-3 items-center">
          {/* Logo */}
          <div className="col-span-3 md:col-span-2 flex items-center">
            <Link
              to="/"
              className="font-bold text-2xl tracking-tight text-indigo-600"
            >
              MyShop
            </Link>
          </div>

          {/* Search */}
          <div className="col-span-7 md:col-span-7 flex justify-center">
            <SearchBar />
          </div>

          {/* Right menu */}
          <nav className="col-span-2 md:col-span-3 flex items-center justify-end gap-3 text-sm">
            {/* Desktop links */}
            <Link
              to="/cart"
              className="hidden md:flex items-center gap-1 hover:text-indigo-600"
            >
              <ShoppingCart size={18} /> Cart
            </Link>
            <Link
              to="/orders"
              className="hidden md:block hover:text-indigo-600"
            >
              Orders
            </Link>
            <Link
              to="/returns"
              className="hidden md:block hover:text-indigo-600"
            >
              Returns
            </Link>
            <Link
              to="/wishlist"
              className="hidden md:block hover:text-indigo-600"
            >
              Wishlist
            </Link>

            {isAuthed ? (
              <button
                onClick={logout}
                className="border px-3 py-1 rounded hover:bg-gray-50"
              >
                Logout
              </button>
            ) : (
              <Link
                to="/login"
                className="border px-3 py-1 rounded hover:bg-gray-50"
              >
                Login
              </Link>
            )}

            {/* Mobile quick actions */}
            <Link
              to="/cart"
              className="md:hidden border px-2 py-1 rounded"
              aria-label="Cart"
            >
              <ShoppingCart size={18} />
            </Link>
            {/* Placeholder mobile menu icon (wired up later if you add a drawer) */}
            <button
              type="button"
              className="md:hidden border px-2 py-1 rounded"
              aria-label="Menu"
            >
              <List size={18} />
            </button>
          </nav>
        </div>
      </header>

      {/* Body */}
      <main className="max-w-6xl mx-auto px-4 py-6 w-full flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
