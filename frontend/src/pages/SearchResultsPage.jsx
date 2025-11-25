// src/pages/SearchResultsPage.jsx
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../lib/api";
import ProductCard from "../components/ProductCard";
import Filters from "../components/Filters";

const PAGE_SIZE = 20;

function ResultSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="h-48 rounded-xl bg-gray-100 animate-pulse" />
      ))}
    </div>
  );
}

export default function SearchResultsPage() {
  const [sp, setSp] = useSearchParams();

  const q = sp.get("q") || "";
  const category = sp.get("category") || "";
  const brand = sp.get("brand") || "";
  const priceMin = sp.get("price_min") || "";
  const priceMax = sp.get("price_max") || "";
  const page = Math.max(1, parseInt(sp.get("page") || "1", 10) || 1);

  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const queryKey = useMemo(
    () => JSON.stringify({ q, category, brand, priceMin, priceMax, page }),
    [q, category, brand, priceMin, priceMax, page]
  );

  useEffect(() => {
    (async () => {
      setLoading(true);
      setErr("");
      try {
        const offset = (page - 1) * PAGE_SIZE;
        const params = {
          _public: 1,
          limit: PAGE_SIZE,
          offset,
        };
        if (q) params.q = q;
        if (category) params.category = category; // slug
        if (brand) params.brand = brand;
        if (priceMin) params.price_min = priceMin;
        if (priceMax) params.price_max = priceMax;

        const r = await api.get("/search", { params });
        const data = r.data || {};
        setItems(Array.isArray(data.results) ? data.results : []);
        setCount(Number(data.count || 0));
      } catch (e) {
        setErr(e?.response?.data?.detail || "Could not load results.");
        setItems([]);
        setCount(0);
      } finally {
        setLoading(false);
      }
    })();
  }, [queryKey]);

  function setParam(key, val) {
    if (val === null || val === undefined || val === "") sp.delete(key);
    else sp.set(key, String(val));
    if (key !== "page") sp.set("page", "1"); // reset to first page on filter change
    setSp(sp, { replace: true });
  }

  function clearChip(key) {
    setParam(key, "");
  }

  function goToPage(targetPage) {
    setParam("page", Math.max(1, targetPage));
  }

  const title = q
    ? `Results for “${q}”`
    : category
    ? `Category: ${category}`
    : "Products";

  const pageCount = count ? Math.max(1, Math.ceil(count / PAGE_SIZE)) : 1;
  const startIdx = count ? (page - 1) * PAGE_SIZE + 1 : null;
  const endIdx = count ? Math.min(page * PAGE_SIZE, count) : null;

  const canPrev = page > 1;
  const canNext = page < pageCount;

  return (
    <div className="grid md:grid-cols-[16rem,1fr] gap-6">
      {/* Sidebar filters (desktop) */}
      <div className="hidden md:block">
        <Filters />
      </div>

      {/* Main */}
      <div>
        {/* Mobile filter toggle hint */}
        <div className="md:hidden mb-3 text-sm">
          Tip: use filters on a larger screen for more options.
        </div>

        <div className="flex items-end justify-between gap-3 mb-3">
          <div>
            <h1 className="text-xl font-semibold">{title}</h1>
            {count > 0 && startIdx && endIdx && (
              <div className="text-xs text-gray-600">
                Showing {startIdx}-{endIdx} of {count}
              </div>
            )}
          </div>

          {/* Sort — backend /search currently orders by name; leaving disabled */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-500">Sort</label>
            <select className="border rounded px-2 py-1 text-sm opacity-60" disabled>
              <option>Relevance</option>
            </select>
          </div>
        </div>

        {/* Applied filter chips */}
        <div className="flex flex-wrap gap-2 mb-4">
          {q && (
            <button
              className="text-xs rounded-full bg-gray-100 px-2 py-1"
              onClick={() => clearChip("q")}
            >
              “{q}” ✕
            </button>
          )}
          {category && (
            <button
              className="text-xs rounded-full bg-gray-100 px-2 py-1"
              onClick={() => clearChip("category")}
            >
              Category: {category} ✕
            </button>
          )}
          {brand && (
            <button
              className="text-xs rounded-full bg-gray-100 px-2 py-1"
              onClick={() => clearChip("brand")}
            >
              Brand: {brand} ✕
            </button>
          )}
          {priceMin && (
            <button
              className="text-xs rounded-full bg-gray-100 px-2 py-1"
              onClick={() => clearChip("price_min")}
            >
              Min ₹{priceMin} ✕
            </button>
          )}
          {priceMax && (
            <button
              className="text-xs rounded-full bg-gray-100 px-2 py-1"
              onClick={() => clearChip("price_max")}
            >
              Max ₹{priceMax} ✕
            </button>
          )}
          {(q || category || brand || priceMin || priceMax) && (
            <button
              className="text-xs underline text-gray-700"
              onClick={() => {
                ["q", "category", "brand", "price_min", "price_max", "page"].forEach(
                  (k) => sp.delete(k)
                );
                setSp(sp, { replace: true });
              }}
            >
              Clear all
            </button>
          )}
        </div>

        {/* Results */}
        {err && <div className="mb-3 text-sm text-red-600">{err}</div>}

        {loading ? (
          <ResultSkeleton />
        ) : items.length === 0 ? (
          <div className="rounded-xl border bg-white p-8 text-center text-gray-600">
            No items found. Try adjusting filters.
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {items.map((p) => (
                <ProductCard key={p.id} p={p} />
              ))}
            </div>

            {/* Pagination */}
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                disabled={!canPrev}
                onClick={() => goToPage(page - 1)}
              >
                Prev
              </button>
              <span className="text-sm">
                Page <b>{page}</b> of <b>{pageCount}</b>
              </span>
              <button
                className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                disabled={!canNext}
                onClick={() => goToPage(page + 1)}
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
