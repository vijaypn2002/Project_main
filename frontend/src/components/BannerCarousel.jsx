// src/components/BannerCarousel.jsx
import { useMemo } from "react";
import { Swiper, SwiperSlide } from "swiper/react";
import { Navigation, Pagination, Autoplay } from "swiper/modules";

// Swiper styles (ensure these are imported once in your app)
import "swiper/css";
import "swiper/css/navigation";
import "swiper/css/pagination";

/**
 * BannerCarousel
 * @param {Object[]} banners - [{ image, alt, link }]
 * @param {boolean} fullBleed - edge-to-edge (ignores container padding)
 */
export default function BannerCarousel({ banners = [], fullBleed = false }) {
  // Respect reduced-motion: pause autoplay if user prefers less motion
  const autoplay = useMemo(() => {
    if (typeof window !== "undefined") {
      const prefersReduced = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
      if (prefersReduced) return false;
    }
    return { delay: 3200, disableOnInteraction: false };
  }, []);

  const wrapperClass =
    (fullBleed ? "relative left-1/2 -translate-x-1/2 w-screen max-w-none overflow-hidden " : "") +
    "mb-6";

  if (!banners?.length) {
    return (
      <div className={wrapperClass}>
        <div
          className={[
            "aspect-[3.3/1] bg-gradient-to-r from-indigo-50 to-blue-50",
            "flex items-center justify-center",
            fullBleed ? "rounded-none" : "rounded-xl border",
          ].join(" ")}
        >
          <div className="text-gray-500">Add banners in CMS to replace this</div>
        </div>
      </div>
    );
  }

  return (
    <div className={wrapperClass}>
      <Swiper
        modules={[Navigation, Pagination, Autoplay]}
        navigation
        pagination={{ clickable: true }}
        autoplay={autoplay}
        loop
        className={fullBleed ? "" : "rounded-xl overflow-hidden"}
        aria-roledescription="carousel"
      >
        {banners.map((b, i) => {
          const href = b?.link?.trim() || "";
          const hasLink = Boolean(href);
          const isExternal = hasLink && /^(https?:)?\/\//i.test(href);
          const alt = b?.alt || `banner-${i + 1}`;
          const imgClasses = [
            "w-full object-cover",
            "h-[260px] sm:h-[320px] md:h-[400px] lg:h-[460px]",
            fullBleed ? "rounded-none" : "rounded-xl border",
          ].join(" ");

          return (
            <SwiperSlide key={i} aria-label={`Banner ${i + 1} of ${banners.length}`}>
              {hasLink ? (
                <a
                  href={href}
                  className="block"
                  target={isExternal ? "_blank" : undefined}
                  rel={isExternal ? "noopener noreferrer" : undefined}
                  aria-label={alt}
                >
                  <img src={b.image} alt={alt} loading={i === 0 ? "eager" : "lazy"} className={imgClasses} />
                </a>
              ) : (
                <img src={b.image} alt={alt} loading={i === 0 ? "eager" : "lazy"} className={imgClasses} />
              )}
            </SwiperSlide>
          );
        })}
      </Swiper>
    </div>
  );
}
