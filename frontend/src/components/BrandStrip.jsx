// src/components/BrandStrip.jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";

const SKELETON_COUNT = 12;

function SkeletonTile() {
  return (
    <div className="border rounded-xl bg-white p-3 animate-pulse">
      <div className="h-10 bg-gray-200 rounded" />
    </div>
  );
}

export default function BrandStrip() {
  const [brands, setBrands] = useState(null); // null = loading, [] = loaded-empty

  useEffect(() => {
    const ctrl = new AbortController();
    (async () => {
      try {
        // Backend endpoint: implement /catalog/brands/ (paginated or plain list)
        const r = await api.get("/catalog/brands/", {
          params: { _public: 1 },
          signal: ctrl.signal,
        });
        const list = r.data?.results || r.data || [];
        // Normalize minimal fields we need
        const normalized = list
          .map((b) => ({
            id: b.id ?? b.slug ?? b.name,
            name: b.name ?? "",
            slug: b.slug ?? b.name ?? "",
            logo: b.logo || b.image || null,
          }))
          .filter((b) => b.name && b.slug);

        setBrands(normalized.slice(0, 12));
      } catch {
        if (!ctrl.signal.aborted) setBrands([]);
      }
    })();
    return () => ctrl.abort();
  }, []);

  if (brands === null) {
    // Loading skeletons
    return (
      <section className="mt-10">
        <h2 className="text-xl font-semibold mb-3">Shop by brand</h2>
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
          {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
            <SkeletonTile key={i} />
          ))}
        </div>
      </section>
    );
  }

  if (!brands.length) return null;

  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold mb-3">Shop by brand</h2>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
        {brands.map((b) => (
          <Link
            key={b.id}
            to={`/search?brand=${encodeURIComponent(b.slug || b.name)}`}
            className="border rounded-xl bg-white p-3 hover:shadow flex items-center justify-center"
          >
            {b.logo ? (
              <img
                src={b.logo}
                alt={b.name}
                className="h-10 max-w-full object-contain"
                loading="lazy"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                  // let the text fallback show
                  const sibling = e.currentTarget.nextElementSibling;
                  if (sibling) sibling.style.display = "block";
                }}
              />
            ) : null}
            <span className="text-sm" style={{ display: b.logo ? "none" : "block" }}>
              {b.name}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
