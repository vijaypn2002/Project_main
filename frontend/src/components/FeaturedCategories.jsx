// src/components/FeaturedCategories.jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";

const LIMIT = 8;

function SkeletonCard() {
  return (
    <div className="border rounded-xl p-3 bg-white animate-pulse">
      <div className="h-16 w-16 mx-auto mb-2 rounded bg-gray-200" />
      <div className="h-3 w-20 mx-auto rounded bg-gray-200" />
    </div>
  );
}

export default function FeaturedCategories() {
  const [cats, setCats] = useState(null); // null = loading, [] = none

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      try {
        // Prefer a curated endpoint if you add one later:
        // const r = await api.get("/catalog/categories/featured/", { params: { _public: 1 }, signal: ctrl.signal });
        // For now: fetch all & filter to top-level
        const r = await api.get("/catalog/categories/", {
          params: { _public: 1 },
          signal: ctrl.signal,
        });
        const all = Array.isArray(r.data?.results) ? r.data.results : r.data || [];
        const top = all.filter((c) => c.parent == null).slice(0, LIMIT);

        // Normalize & absolutize icon/image URLs if backend returns media paths
        const shaped = top.map((c) => {
          const raw = c.icon_url || c.icon || c.image || "";
          let url = "";
          if (raw) {
            url = /^https?:\/\//i.test(raw) ? raw : `${window.location.origin}${raw.startsWith("/") ? "" : "/"}${raw}`;
          }
            return {
            id: c.id ?? c.slug ?? c.name,
            slug: c.slug,
            name: c.name,
            img: url,
          };
        });

        setCats(shaped);
      } catch (e) {
        if (!ctrl.signal.aborted) setCats([]);
      }
    })();
    return () => ctrl.abort();
  }, []);

  if (cats === null) {
    return (
      <section className="mt-10">
        <h2 className="text-xl font-semibold mb-3">Featured categories</h2>
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4">
          {Array.from({ length: LIMIT }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </section>
    );
  }

  if (!cats.length) return null;

  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold mb-3">Featured categories</h2>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4">
        {cats.map((c) => (
          <Link
            key={c.id}
            to={`/search?category=${encodeURIComponent(c.slug)}`}
            className="border rounded-xl p-3 hover:shadow bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {c.img ? (
              <img
                src={c.img}
                alt={c.name}
                className="h-16 w-16 object-contain mx-auto mb-2"
                loading="lazy"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                  const fallback = e.currentTarget.parentElement.querySelector(".fc-fallback");
                  if (fallback) fallback.style.display = "block";
                }}
              />
            ) : null}
            <div className={`h-16 w-16 mx-auto mb-2 rounded bg-gray-100 fc-fallback ${c.img ? "hidden" : ""}`} />
            <div className="text-center text-sm">{c.name}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
