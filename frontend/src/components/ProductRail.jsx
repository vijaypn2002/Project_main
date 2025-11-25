// src/components/ProductRail.jsx
import { useEffect, useMemo, useState } from "react";
import api from "../lib/api";
import ProductCard from "./ProductCard";

/**
 * ProductRail
 * Props:
 *  - title: string                      (section heading)
 *  - viewAll: string | undefined        (href for "View all" link)
 *  - source: string | undefined         (GET endpoint to fetch from; ignored if `items` provided)
 *  - params: object                     (extra query params for fetch)
 *  - items: array | undefined           (preloaded items; skips fetching when present)
 */
export default function ProductRail({ title, viewAll, source, params = {}, items }) {
  const [data, setData] = useState(Array.isArray(items) ? items : []);
  const [loading, setLoading] = useState(!Array.isArray(items));
  const [err, setErr] = useState("");

  // Stable string for params comparison without re-running on every render
  const paramsKey = useMemo(() => JSON.stringify(params || {}), [params]);

  useEffect(() => {
    if (Array.isArray(items)) return; // use provided data

    if (!source) {
      setErr("Missing data source.");
      setLoading(false);
      setData([]);
      return;
    }

    const ac = new AbortController();
    (async () => {
      try {
        setLoading(true);
        setErr("");
        const r = await api.get(source, {
          params: { _public: 1, page: 1, ...params },
          signal: ac.signal,
        });
        const results = r?.data?.results ?? r?.data ?? [];
        // Keep a tight rail; 10 feels right for most grids
        setData(Array.isArray(results) ? results.slice(0, 10) : []);
      } catch (e) {
        if (ac.signal.aborted) return;
        setErr("Could not load.");
        setData([]);
      } finally {
        if (!ac.signal.aborted) setLoading(false);
      }
    })();

    return () => ac.abort();
  }, [source, paramsKey, items]);

  if (loading)
    return (
      <section className="mt-10">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-xl font-semibold">{title}</h2>
          {viewAll && (
            <a href={viewAll} className="text-sm text-indigo-600 hover:underline">
              View all
            </a>
          )}
        </div>
        {/* skeleton grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-64 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      </section>
    );

  if (!data.length) return null;

  return (
    <section className="mt-10">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-xl font-semibold">{title}</h2>
        {viewAll && (
          <a href={viewAll} className="text-sm text-indigo-600 hover:underline">
            View all
          </a>
        )}
      </div>

      {err && <div className="text-xs text-red-600 mb-2">{err}</div>}

      <div
        className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-6 gap-4"
        role="list"
        aria-label={title || "Products"}
      >
        {data.map((p) => (
          <div role="listitem" key={p.id ?? p.slug ?? Math.random()}>
            <ProductCard p={p} />
          </div>
        ))}
      </div>
    </section>
  );
}
