// src/components/Filters.jsx
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

function useQS() {
  const [sp, setSp] = useSearchParams();
  const clone = useMemo(() => new URLSearchParams(sp), [sp]);
  const apply = (mutator) => {
    const next = new URLSearchParams(clone);
    mutator(next);
    setSp(next, { replace: true });
  };
  return [clone, apply];
}

export default function Filters() {
  const [qs, applyQS] = useQS();

  // Initialise from URL
  const [brand, setBrand] = useState(qs.get("brand") || "");
  const [min, setMin] = useState(qs.get("price_min") || "");
  const [max, setMax] = useState(qs.get("price_max") || "");
  const [open, setOpen] = useState(true); // collapsible for mobile

  // Keep local state in sync if URL changes elsewhere
  useEffect(() => {
    setBrand(qs.get("brand") || "");
    setMin(qs.get("price_min") || "");
    setMax(qs.get("price_max") || "");
  }, [qs]);

  const hasAnyFilter = !!(brand || min || max);

  function normalizeNumber(v) {
    if (v === "" || v === null || v === undefined) return "";
    // Keep only digits and a single dot
    const cleaned = String(v).replace(/[^\d.]/g, "");
    // Avoid leading dots
    const normalized = cleaned.replace(/^\.*/, "");
    // Collapse multiple dots
    const parts = normalized.split(".");
    return parts.length > 1 ? `${parts[0]}.${parts.slice(1).join("")}` : parts[0];
  }

  function handleApply() {
    // Validate numeric range
    const nMin = min === "" ? null : Number(min);
    const nMax = max === "" ? null : Number(max);

    if (nMin !== null && Number.isNaN(nMin)) return;
    if (nMax !== null && Number.isNaN(nMax)) return;
    if (nMin !== null && nMax !== null && nMin > nMax) {
      // Swap if user inverted by mistake
      const tmp = nMin;
      setMin(String(nMax));
      setMax(String(tmp));
    }

    applyQS((next) => {
      if (brand) next.set("brand", brand.trim());
      else next.delete("brand");

      if (min) next.set("price_min", String(Number(min)));
      else next.delete("price_min");

      if (max) next.set("price_max", String(Number(max)));
      else next.delete("price_max");

      // reset pagination on filter change
      next.set("page", "1");
    });
  }

  function handleClear() {
    setBrand("");
    setMin("");
    setMax("");
    applyQS((next) => {
      ["brand", "price_min", "price_max", "page"].forEach((k) => next.delete(k));
    });
  }

  function onKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleApply();
    }
  }

  return (
    <aside className="w-full sm:w-64 sm:shrink-0">
      {/* Header (collapsible on small screens) */}
      <div className="sm:hidden flex items-center justify-between mb-2">
        <h3 className="font-semibold">Filters</h3>
        <div className="flex items-center gap-3">
          {hasAnyFilter && (
            <button
              type="button"
              onClick={handleClear}
              className="text-xs text-blue-600 underline"
            >
              Clear
            </button>
          )}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="text-xs px-2 py-1 border rounded"
          >
            {open ? "Hide" : "Show"}
          </button>
        </div>
      </div>

      <div className="hidden sm:flex items-center justify-between mb-2">
        <h3 className="font-semibold">Filters</h3>
        <button
          type="button"
          onClick={handleClear}
          className="text-xs text-blue-600 underline disabled:text-gray-400"
          disabled={!hasAnyFilter}
        >
          Clear
        </button>
      </div>

      <div
        className={[
          "border rounded-lg p-3 h-fit sm:sticky sm:top-20 bg-white",
          open ? "block" : "hidden sm:block",
        ].join(" ")}
        onKeyDown={onKeyDown}
      >
        <div className="space-y-3">
          {/* Brand */}
          <div>
            <label htmlFor="f-brand" className="text-xs text-gray-500 mb-1 block">
              Brand
            </label>
            <input
              id="f-brand"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="e.g. ACME"
              className="w-full border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
              autoComplete="off"
            />
          </div>

          {/* Price */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Price</div>
            <div className="flex items-center gap-2">
              <input
                inputMode="decimal"
                id="f-min"
                value={min}
                onChange={(e) => setMin(normalizeNumber(e.target.value))}
                onBlur={(e) => setMin(normalizeNumber(e.target.value))}
                placeholder="Min"
                className="w-1/2 border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
                aria-label="Minimum price"
              />
              <input
                inputMode="decimal"
                id="f-max"
                value={max}
                onChange={(e) => setMax(normalizeNumber(e.target.value))}
                onBlur={(e) => setMax(normalizeNumber(e.target.value))}
                placeholder="Max"
                className="w-1/2 border rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
                aria-label="Maximum price"
              />
            </div>
            {min !== "" && max !== "" && Number(min) > Number(max) && (
              <div className="mt-1 text-xs text-amber-700">
                Min is greater than max — will be corrected.
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleApply}
            className="w-full mt-1 px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
            disabled={brand.trim() === "" && min === "" && max === ""}
            aria-label="Apply filters"
          >
            Apply
          </button>
        </div>
      </div>
    </aside>
  );
}
