// src/components/ProductCard.jsx
import { Link } from "react-router-dom";
import api from "../lib/api";
import { auth } from "../lib/auth";
import { useState, useMemo } from "react";

function formatINR(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(n);
  } catch {
    return `₹${n}`;
  }
}

export default function ProductCard({ p }) {
  const img =
    p?.primary_image?.image ||
    p?.image || // optional legacy field
    "";

  const alt = p?.primary_image?.alt_text || p?.name || "Product image";

  // Prefer min_price from search, fallback to price if present
  const price = useMemo(() => (p?.min_price ?? p?.price ?? null), [p]);

  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);
  const isAuthed = !!auth.access?.() ? auth.access() : false; // normalize older/newer auth helpers

  async function addToWishlist(e) {
    e.preventDefault();
    e.stopPropagation();
    if (!isAuthed) {
      alert("Please log in to use wishlist.");
      return;
    }
    if (adding || added) return;

    setAdding(true);
    try {
      // Product-level wish (variant chosen later on PDP)
      await api.post("/wishlist/", { product_id: p.id });
      setAdded(true);
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.non_field_errors?.[0] ||
        "Could not add to wishlist.";
      alert(msg);
    } finally {
      setAdding(false);
    }
  }

  return (
    <Link
      to={`/product/${p.slug}`}
      className="group relative block rounded-xl border bg-white overflow-hidden hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-indigo-500"
    >
      {/* Wishlist button */}
      <button
        onClick={addToWishlist}
        aria-label={added ? "Added to wishlist" : "Add to wishlist"}
        aria-pressed={added}
        title={added ? "Added to wishlist" : "Add to wishlist"}
        disabled={adding || added}
        className="absolute right-2 top-2 z-10 rounded-full bg-white/95 px-2 py-1 text-xs shadow-md hover:bg-white disabled:opacity-60"
      >
        <span aria-hidden="true">{added ? "♥" : "♡"}</span>
      </button>

      {/* Image */}
      <div className="aspect-[4/3] bg-gray-50">
        {img ? (
          <img
            src={img}
            alt={alt}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
            loading="lazy"
            decoding="async"
            onError={(e) => {
              e.currentTarget.src = "";
              e.currentTarget.alt = "Image unavailable";
            }}
          />
        ) : (
          <div className="h-full w-full flex items-center justify-center text-gray-400 text-sm">
            image
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="p-3">
        <div className="text-xs text-gray-500 truncate">{p.brand || "\u00A0"}</div>
        <div className="mt-0.5 font-medium line-clamp-2 min-h-[2.5rem]">{p.name}</div>

        <div className="mt-1 flex items-baseline gap-2">
          <span className="font-semibold">
            {price != null ? formatINR(price) : "—"}
          </span>
          {p?.price_mrp && Number(p.price_mrp) > Number(price ?? 0) ? (
            <span className="text-xs text-gray-500 line-through">
              {formatINR(p.price_mrp)}
            </span>
          ) : null}
        </div>
      </div>
    </Link>
  );
}
