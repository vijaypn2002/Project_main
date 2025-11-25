// src/pages/Wishlist.jsx
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";

/**
 * Wishlist page
 * - Requires auth (shows a login prompt on 401)
 * - Hydrates product data (image/price) using catalog endpoints
 * - Uses backend DELETE route: /wishlist/items/<item_id>/
 */
function useApiOrigin() {
  // Strip trailing /api/v1 so we can prefix media paths to absolute URLs
  return useMemo(
    () => import.meta.env.VITE_API_BASE?.replace(/\/api\/v1\/?$/, "") || "",
    []
  );
}

function whenText(dt) {
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return "";
  }
}

export default function Wishlist() {
  const origin = useApiOrigin();
  const nav = useNavigate();

  const [rows, setRows] = useState(null); // raw wishlist rows from API
  const [items, setItems] = useState([]); // hydrated render items
  const [needAuth, setNeedAuth] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function fetchAndHydrate() {
      setErr("");
      setNeedAuth(false);
      setRows(null);
      setItems([]);

      try {
        const r = await api.get("/wishlist/"); // auth required by backend
        const data = Array.isArray(r.data) ? r.data : [];
        if (cancelled) return;

        setRows(data);

        // If backend already expanded product field, hydrate immediately
        const haveProduct = data.some((w) => !!w.product);
        if (haveProduct) {
          const hydrated = data.map((w) => normalizeRow(w, origin));
          if (!cancelled) setItems(hydrated);
          return;
        }

        // Otherwise, fetch product details by ids (prefer batch)
        const ids = Array.from(
          new Set(
            data.map((w) => w.product_id || w.product?.id).filter(Boolean)
          )
        );

        if (ids.length === 0) {
          if (!cancelled) setItems([]);
          return;
        }

        let products = [];
        try {
          // Preferred: batch endpoint ?ids=1,2,3&_public=1 (if your backend supports it)
          const pr = await api.get("/catalog/products/", {
            params: { ids: ids.join(","), _public: 1 },
          });
          products = (pr.data?.results || pr.data || []).map((p) =>
            normalizeProduct(p, origin)
          );
        } catch {
          // Fallback chain (best-effort):
          // 1) /catalog/products/by-id/<id>/ (if you add this helper)
          // 2) /catalog/products/<id>/ (if your backend accepts numeric id there)
          const fetched = await Promise.all(
            ids.map(async (id) => {
              try {
                const a = await api.get(`/catalog/products/by-id/${id}/`, {
                  params: { _public: 1 },
                });
                return normalizeProduct(a.data, origin);
              } catch {
                try {
                  const b = await api.get(`/catalog/products/${id}/`, {
                    params: { _public: 1 },
                  });
                  return normalizeProduct(b.data, origin);
                } catch {
                  return null;
                }
              }
            })
          );
          products = fetched.filter(Boolean);
        }

        const pmap = new Map(products.map((p) => [p.id, p]));
        const hydrated = data.map((w) => {
          const pid = w.product_id || w.product?.id;
          const p = pid ? pmap.get(pid) : null;
          return normalizeRow({ ...w, product: p || w.product || null }, origin);
        });

        if (!cancelled) setItems(hydrated);
      } catch (e) {
        if (cancelled) return;
        const status = e?.response?.status;
        if (status === 401) {
          setNeedAuth(true);
        } else {
          setErr("Could not load wishlist.");
        }
        setRows([]);
        setItems([]);
      }
    }

    fetchAndHydrate();

    return () => {
      cancelled = true;
    };
  }, [origin]);

  async function removeItem(row) {
    try {
      // Backend route from wishlist/urls.py:
      // DELETE /wishlist/items/<item_id>/
      if (row._wid) {
        await api.delete(`/wishlist/items/${row._wid}/`);
      } else if (row.pid) {
        // Optional: if you add query-based deletion later
        await api.delete(`/wishlist/`, { params: { product_id: row.pid } });
      }

      // Optimistic UI
      setItems((prev) => prev.filter((x) => x._wid !== row._wid));

      // Refresh base list and re-hydrate to keep IDs in sync
      const r = await api.get("/wishlist/");
      const data = Array.isArray(r.data) ? r.data : [];
      setRows(data);

      // Rebuild hydrated list (simple path: if product already embedded)
      if (data.some((w) => !!w.product)) {
        setItems(data.map((w) => normalizeRow(w, origin)));
      } else {
        // Minimal re-hydrate: drop any items we can’t resolve immediately
        setItems((prev) =>
          prev.filter((x) =>
            data.some((w) => (w.id === x._wid) || (w.product_id === x.pid))
          )
        );
      }
    } catch {
      alert("Failed to remove item.");
    }
  }

  if (rows === null && !needAuth) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-xl font-semibold mb-4">My wishlist</h1>

      {needAuth && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          You need to be logged in to view your wishlist.
          <div className="mt-2">
            <button
              onClick={() => nav("/login")}
              className="px-3 py-1 rounded border hover:bg-gray-50"
            >
              Go to Login
            </button>
          </div>
        </div>
      )}

      {err && <div className="mb-3 text-sm text-red-600">{err}</div>}

      {!needAuth && items.length === 0 && (
        <div className="rounded-xl border bg-white p-6 text-sm text-gray-600">
          Your wishlist is empty.
        </div>
      )}

      {!needAuth && items.length > 0 && (
        <ul className="rounded-xl border bg-white divide-y">
          {items.map((p) => (
            <li key={`${p._wid || p.pid}`} className="p-3 sm:p-4">
              <div className="flex items-start gap-3 sm:gap-4">
                <Link to={p.slug ? `/product/${p.slug}` : "#"} className="block shrink-0">
                  <div className="h-20 w-20 sm:h-24 sm:w-24 rounded-lg border bg-gray-50 overflow-hidden flex items-center justify-center">
                    {p.image ? (
                      <img
                        src={p.image}
                        alt={p.alt}
                        className="h-full w-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <span className="text-gray-400 text-xs">image</span>
                    )}
                  </div>
                </Link>

                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      {p.brand && (
                        <div className="text-xs text-gray-500 truncate">{p.brand}</div>
                      )}
                      <Link
                        to={p.slug ? `/product/${p.slug}` : "#"}
                        className="font-medium hover:underline block truncate"
                        title={p.name}
                      >
                        {p.name}
                      </Link>
                      <div className="mt-1 text-sm">
                        {p.price != null ? (
                          <span className="font-semibold">₹{p.price}</span>
                        ) : (
                          <span className="text-gray-500">Price: Not available</span>
                        )}
                        {p.unavailable && (
                          <span className="ml-2 text-xs text-rose-600">• Currently unavailable</span>
                        )}
                      </div>
                      {p.added_at && (
                        <div className="mt-1 text-xs text-gray-500">
                          Added {whenText(p.added_at)}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col gap-2">
                      <button
                        onClick={() => (p.slug ? nav(`/product/${p.slug}`) : null)}
                        className="px-3 py-1 rounded border hover:bg-gray-50 text-sm"
                      >
                        View
                      </button>
                      <button
                        onClick={() => removeItem(p)}
                        className="px-3 py-1 rounded border text-rose-600 hover:bg-rose-50 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ---------- helpers ---------- */

// Normalize a product object coming from catalog/search APIs
function normalizeProduct(p, origin) {
  if (!p) return null;
  // Support both your search serializer and catalog detail:
  // search: { primary_image: { image, alt_text }, min_price }
  // catalog: { image | primary_image.image, price_* }
  const raw =
    p?.primary_image?.image ||
    p?.image ||
    (Array.isArray(p?.images) && p.images[0]?.image) ||
    "";

  const image = raw?.startsWith("http") ? raw : raw ? `${origin}${raw}` : "";

  const price =
    p?.min_price ??
    p?.price ??
    p?.price_sale ??
    p?.price_mrp ??
    null;

  return {
    id: p.id,
    slug: p.slug,
    name: p.name || "Product",
    brand: p.brand || "",
    price,
    image,
    alt: p?.primary_image?.alt_text || p?.alt || p?.name || "product",
    unavailable:
      p.is_active === false || p.available === false || p.status === "inactive",
  };
}

// Normalize a wishlist row into render item
function normalizeRow(w, origin) {
  const p = w.product ? normalizeProduct(w.product, origin) : null;
  return {
    _wid: w.id || null, // wishlist item id (needed for DELETE)
    pid: w.product_id || w.product?.id || p?.id || null,
    added_at: w.created_at || null,
    // product fields (fallbacks)
    slug: p?.slug || w.product?.slug || "",
    name: p?.name || w.product?.name || "Product",
    brand: p?.brand || w.product?.brand || "",
    price: p?.price ?? null,
    image: p?.image || "",
    alt: p?.alt || "product",
    unavailable: !!p?.unavailable,
  };
}
