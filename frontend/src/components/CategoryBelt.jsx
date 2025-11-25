// src/components/CategoryBelt.jsx
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";

const SKELETONS = 10;

function Skeleton() {
  return (
    <div className="flex items-center gap-2">
      <span className="h-6 w-6 rounded bg-gray-200" />
      <span className="h-4 w-24 rounded bg-gray-200" />
    </div>
  );
}

/**
 * Category belt:
 * - Tries /catalog/categories/nav/ first (expects [{id,name/label,slug,icon/icon_url}])
 * - Falls back to top-level categories from /catalog/categories/
 */
export default function CategoryBelt() {
  const [items, setItems] = useState(null); // null = loading, [] = empty
  const scrollerRef = useRef(null);

  useEffect(() => {
    const ctrl = new AbortController();

    (async () => {
      // helper to normalize category-like objects
      const shape = (c) => ({
        id: c.id ?? c.slug ?? c.name,
        name: c.name ?? c.label ?? "",
        slug: c.slug ?? "",
        icon_url: c.icon_url ?? c.icon ?? "",
      });

      try {
        // Preferred nav endpoint (public)
        const r = await api.get("/catalog/categories/nav/", {
          params: { _public: 1 },
          signal: ctrl.signal,
        });
        const list = Array.isArray(r.data) ? r.data : [];
        if (list.length) {
          setItems(list.map(shape).filter((x) => x.name && x.slug));
          return;
        }
      } catch {
        // fall through
      }

      try {
        // Fallback: fetch all → filter top-level
        const r2 = await api.get("/catalog/categories/", {
          params: { _public: 1 },
          signal: ctrl.signal,
        });
        const all = Array.isArray(r2.data?.results) ? r2.data.results : r2.data || [];
        const top = all.filter((c) => c.parent == null);
        setItems(top.map(shape).filter((x) => x.name && x.slug));
      } catch (e) {
        if (!ctrl.signal.aborted) {
          console.error("Category belt failed", e);
          setItems([]);
        }
      }
    })();

    return () => ctrl.abort();
  }, []);

  // Loading skeletons
  if (items === null) {
    return (
      <div className="border-b bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 overflow-x-auto">
          <div className="flex gap-6 min-w-max">
            {Array.from({ length: SKELETONS }).map((_, i) => (
              <Skeleton key={i} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!items.length) return null;

  // Keyboard scroll (left/right arrows) for accessibility
  const onKeyDown = (e) => {
    const el = scrollerRef.current;
    if (!el) return;
    if (e.key === "ArrowRight") el.scrollBy({ left: 120, behavior: "smooth" });
    if (e.key === "ArrowLeft") el.scrollBy({ left: -120, behavior: "smooth" });
  };

  return (
    <div className="border-b bg-white sticky top-0 z-10">
      <div
        ref={scrollerRef}
        className="max-w-6xl mx-auto px-4 py-3 overflow-x-auto focus:outline-none"
        tabIndex={0}
        onKeyDown={onKeyDown}
        aria-label="Browse categories"
      >
        <div className="flex gap-6 min-w-max">
          {items.map((c) => {
            const to = `/search?category=${encodeURIComponent(c.slug)}`;
            return (
              <Link
                key={c.id}
                to={to}
                className="flex items-center gap-2 hover:text-indigo-600 focus:text-indigo-600"
              >
                {c.icon_url ? (
                  <img
                    src={c.icon_url}
                    alt=""
                    className="h-6 w-6 object-contain"
                    loading="lazy"
                    onError={(e) => (e.currentTarget.style.display = "none")}
                  />
                ) : (
                  <span className="h-6 w-6 rounded bg-gray-100" aria-hidden="true" />
                )}
                <span className="whitespace-nowrap">{c.name}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
