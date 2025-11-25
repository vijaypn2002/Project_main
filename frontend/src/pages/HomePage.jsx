// src/pages/HomePage.jsx
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import api from "../lib/api";
import BannerCarousel from "../components/BannerCarousel";
import ProductCard from "../components/ProductCard";
import CategoryBelt from "../components/CategoryBelt";
import ProductRail from "../components/ProductRail";
import FeaturedCategories from "../components/FeaturedCategories";
import BrandStrip from "../components/BrandStrip";
import TrustStrip from "../components/TrustStrip";
import NewsletterCTA from "../components/NewsletterCTA";

function useApiOrigin() {
  return useMemo(
    () => (import.meta.env.VITE_API_BASE || "").replace(/\/api\/v1\/?$/, ""),
    []
  );
}

function RailSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="h-48 animate-pulse rounded-xl bg-gray-100" />
      ))}
    </div>
  );
}

export default function HomePage() {
  const [loading, setLoading] = useState(true);
  const [banners, setBanners] = useState([]);
  const [rails, setRails] = useState([]);
  const origin = useApiOrigin();

  useEffect(() => {
    let alive = true;
    const safeSet = (fn) => (v) => {
      if (alive) fn(v);
    };

    (async () => {
      setLoading(true);

      try {
        // Try CMS-powered home content first
        const cms = await api.get("/content/home", { params: { _public: 1 } });

        // Normalize banner image URLs to absolute
        const bn = cms.data?.banners || [];
        safeSet(setBanners)(
          bn.map((b) => ({
            ...b,
            image: b?.image?.startsWith?.("http") ? b.image : `${origin}${b?.image || ""}`,
          }))
        );

        const r = cms.data?.rails || [];
        if (Array.isArray(r) && r.length) {
          safeSet(setRails)(r);
          safeSet(setLoading)(false);
          return;
        }
      } catch {
        // fall through to fallback rails
      }

      // Fallback: simple “New arrivals” rail using catalog products
      try {
        const p = await api.get("/catalog/products/", { params: { _public: 1, page: 1, ordering: "-id" } });
        const items = (p.data?.results || p.data || []).slice(0, 12);
        safeSet(setRails)([
          { title: "New arrivals", viewAll: "/search?ordering=-id", items },
        ]);
      } catch {
        safeSet(setRails)([]);
      } finally {
        safeSet(setLoading)(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [origin]);

  return (
    <main className="relative">
      {/* soft background */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-white via-white to-gray-50" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Category belt (always above hero) */}
        <div className="pt-4">
          <CategoryBelt />
        </div>

        {/* Hero */}
        <section className="mt-4">
          {loading ? (
            <div className="h-40 animate-pulse rounded-2xl bg-gray-100 sm:h-56 md:h-72" />
          ) : (
            <BannerCarousel banners={banners} />
          )}
        </section>

        {/* Featured categories */}
        <section className="mt-8">
          <FeaturedCategories />
        </section>

        {/* Divider */}
        <div className="my-10 h-px w-full bg-gradient-to-r from-transparent via-gray-200 to-transparent" />

        {/* Rails from CMS or fallback */}
        <section className="space-y-10">
          {rails.map((rail, idx) => (
            <section key={idx}>
              <div className="mb-3 flex items-baseline justify-between">
                <h2 className="text-xl font-semibold">{rail.title || "Featured"}</h2>
                {rail.viewAll && (
                  <Link to={rail.viewAll} className="text-sm text-indigo-600 hover:underline">
                    View all
                  </Link>
                )}
              </div>

              {loading ? (
                <RailSkeleton />
              ) : (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
                  className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
                >
                  {(rail.items || []).map((p) => (
                    <ProductCard key={p.id} p={p} />
                  ))}
                </motion.div>
              )}
            </section>
          ))}

          {/* Extra rails — use only endpoints that exist on backend */}
          <ProductRail
            title="Trending now"
            source="/catalog/products/"
            params={{ ordering: "-id" }} // latest as a proxy for trending
            viewAll="/search?ordering=-id"
          />

          <ProductRail
            title="Editor’s picks"
            source="/catalog/products/"
            params={{}} // default ordering/name; safe & supported
            viewAll="/search"
          />

          <ProductRail
            title="Under ₹999"
            source="/catalog/products/"
            params={{ price_max: 999 }}
            viewAll="/search?price_max=999"
          />
        </section>

        {/* Brand logos strip */}
        <section className="my-12">
          <BrandStrip />
        </section>

        {/* Trust + newsletter */}
        <section className="my-12">
          <TrustStrip />
          <div className="mt-8">
            <NewsletterCTA />
          </div>
        </section>
      </div>
    </main>
  );
}
