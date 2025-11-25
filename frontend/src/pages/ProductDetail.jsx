// src/pages/ProductDetail.jsx
import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../lib/api.js";

const PLACEHOLDER = "/placeholder-product.png";

function formatINR(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    return `₹${n.toFixed(2)}`;
  }
}

function useApiOrigin() {
  // turn VITE_API_BASE (…/api/v1) into host origin for media: http://localhost:8000
  return useMemo(
    () => (import.meta.env.VITE_API_BASE || "").replace(/\/api\/v1\/?$/, ""),
    []
  );
}

function toAbs(url, origin) {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${origin}${url}`;
}

export default function ProductDetail() {
  const { slug } = useParams();
  const nav = useNavigate();
  const origin = useApiOrigin();

  const [p, setP] = useState(null);
  const [selVarId, setSelVarId] = useState(null);
  const [qty, setQty] = useState(1);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [imgIdx, setImgIdx] = useState(0);

  // ---- Load product ----
  useEffect(() => {
    (async () => {
      setErr("");
      setP(null);
      setSelVarId(null);
      setImgIdx(0);
      try {
        // Public GET (no Authorization header)
        const r = await api.get(`/catalog/products/${slug}/`, { params: { _public: 1 } });
        const prod = r.data;

        // Normalize product-level image fields to absolute (if backend returned relative)
        const norm = { ...prod };
        if (Array.isArray(norm.images)) {
          norm.images = norm.images.map((im) => ({
            ...im,
            image: toAbs(im?.image || im?.url, origin),
          }));
        }
        if (norm.primary_image?.image) {
          norm.primary_image = { ...norm.primary_image, image: toAbs(norm.primary_image.image, origin) };
        }
        if (norm.image) norm.image = toAbs(norm.image, origin);

        // Normalize variant image-ish fields too (best effort)
        if (Array.isArray(norm.variants)) {
          norm.variants = norm.variants.map((v) => {
            const copy = { ...v };
            for (const k of ["image", "primary_image", "thumbnail", "thumb", "image_url", "primary_image_url"]) {
              if (copy[k]) copy[k] = toAbs(copy[k], origin);
            }
            return copy;
          });
        }

        setP(norm);

        // pick first variant by default
        const firstV = norm?.variants?.[0];
        if (firstV) setSelVarId(firstV.id);
      } catch {
        setErr("Could not load product.");
      }
    })();
  }, [slug, origin]);

  const variants = p?.variants || [];

  const images = useMemo(() => {
    const gallery = [];

    // 1) product.images[]
    if (Array.isArray(p?.images) && p.images.length) {
      for (const im of p.images) {
        const src = im?.image || im?.url;
        if (src) gallery.push(src);
      }
    }

    // 2) variant-specific image (for the selected variant)
    const v = variants.find((x) => x.id === selVarId) || variants[0];
    if (v) {
      const cand =
        v.image ||
        v.primary_image ||
        v.thumbnail ||
        v.thumb ||
        v.image_url ||
        v.primary_image_url;
      if (cand) gallery.unshift(cand);
    }

    // 3) product primary/single image fallback
    const primary1 = p?.primary_image?.image || p?.image;
    if (!gallery.length && primary1) gallery.push(primary1);

    // unique + max 8
    return Array.from(new Set(gallery.filter(Boolean))).slice(0, 8);
  }, [p, variants, selVarId]);

  const variant = useMemo(() => variants.find((v) => v.id === selVarId) || variants[0], [variants, selVarId]);

  const price = useMemo(() => {
    if (!variant) return null;
    return variant.price_sale ?? variant.price_mrp ?? null;
  }, [variant]);

  const mrp = variant?.price_mrp ?? null;
  const hasDiscount = mrp != null && price != null && Number(price) < Number(mrp);

  const stockInfo = useMemo(() => {
    const inv = variant?.inventory;
    const qtyAvail = inv?.qty_available ?? null;
    const backorder = inv?.backorder_policy === "allow";
    if (qtyAvail == null) return { label: "", ok: true };
    if (qtyAvail > 0) return { label: `In stock (${qtyAvail} available)`, ok: true };
    if (backorder) return { label: "Backorder available", ok: true };
    return { label: "Out of stock", ok: false };
  }, [variant]);

  async function addToCart(vId) {
    const q = Math.max(1, Number(qty) || 1);
    setBusy(true);
    setErr("");
    try {
      // Public POST so the anonymous/session cart works
      await api.post(
        "/cart/items/",
        { variant_id: vId, qty: q, mode: "inc" },
        { params: { _public: 1 } }
      );
      nav("/cart");
    } catch (e) {
      const msg = e?.response?.data?.detail || "Could not add to cart. Check server logs.";
      setErr(msg);
      alert(msg);
    } finally {
      setBusy(false);
    }
  }

  if (err && !p) return <div className="text-sm text-red-600">{err}</div>;
  if (!p) return <div>Loading…</div>;

  return (
    <div className="grid gap-8 md:grid-cols-2">
      {/* --- Gallery --- */}
      <div>
        <div className="aspect-square overflow-hidden rounded-xl border bg-gray-50">
          <img
            src={images[imgIdx] || PLACEHOLDER}
            alt={p.name}
            className="h-full w-full object-cover"
            onError={(e) => (e.currentTarget.src = PLACEHOLDER)}
            loading="eager"
            decoding="async"
          />
        </div>

        {images.length > 1 && (
          <div className="mt-3 grid grid-cols-5 gap-2">
            {images.map((src, i) => (
              <button
                key={`${src}-${i}`}
                onClick={() => setImgIdx(i)}
                className={`aspect-square overflow-hidden rounded border bg-white ${imgIdx === i ? "ring-2 ring-indigo-500" : ""}`}
                aria-label={`View image ${i + 1}`}
              >
                <img
                  src={src || PLACEHOLDER}
                  alt={`${p.name} ${i + 1}`}
                  className="h-full w-full object-cover"
                  onError={(e) => (e.currentTarget.src = PLACEHOLDER)}
                  loading="lazy"
                  decoding="async"
                />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* --- Details --- */}
      <div>
        <h1 className="mb-1 text-2xl font-bold">{p.name}</h1>
        {p.brand && <div className="text-sm text-gray-500">{p.brand}</div>}

        {/* Price block */}
        <div className="mt-3 text-lg">
          {hasDiscount && <span className="mr-2 text-gray-400 line-through">{formatINR(mrp)}</span>}
          <span className="font-semibold">{price != null ? formatINR(price) : "—"}</span>
          {hasDiscount && (
            <span className="ml-2 align-middle rounded bg-rose-50 px-2 py-0.5 text-xs font-semibold text-rose-700">
              Save {formatINR(Number(mrp) - Number(price))}
            </span>
          )}
        </div>

        {/* Variant selector (if multiple) */}
        {variants.length > 1 && (
          <div className="mt-4">
            <div className="mb-1 text-sm text-gray-600">Choose an option</div>
            <select
              className="w-full rounded border px-3 py-2"
              value={selVarId ?? variants[0]?.id}
              onChange={(e) => setSelVarId(Number(e.target.value))}
            >
              {variants.map((v) => {
                const label =
                  v.name ||
                  v.sku ||
                  Object.entries(v.attributes || {})
                    .map(([k, val]) => `${k}:${val}`)
                    .join(" / ") ||
                  "Variant";
                const pv = v.price_sale ?? v.price_mrp;
                return (
                  <option key={v.id} value={v.id}>
                    {label} — {formatINR(pv)}
                  </option>
                );
              })}
            </select>
          </div>
        )}

        {/* Stock / backorder status */}
        {stockInfo.label && (
          <div className={`mt-2 text-sm ${stockInfo.ok ? "text-green-700" : "text-red-700"}`}>{stockInfo.label}</div>
        )}

        {/* Qty + CTAs */}
        <div className="mt-4 flex items-center gap-3">
          <label className="text-sm" htmlFor="qty-input">
            Qty
          </label>
          <input
            id="qty-input"
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(Math.max(1, Number(e.target.value) || 1))}
            className="w-20 rounded border px-2 py-1"
          />

        <button
            onClick={() => addToCart(variant?.id)}
            disabled={busy || !stockInfo.ok || !variant}
            className="rounded-lg bg-black px-4 py-2 text-white disabled:opacity-60"
          >
            {busy ? "Adding…" : stockInfo.ok ? "Add to cart" : "Out of stock"}
          </button>
        </div>

        {/* Description */}
        {p.description && (
          <div className="prose mt-6 max-w-none">
            <h3 className="mb-1 text-base font-semibold">Description</h3>
            <p className="whitespace-pre-line text-sm text-gray-700">{p.description}</p>
          </div>
        )}

        {err && <div className="mt-3 text-sm text-red-600">{err}</div>}
      </div>
    </div>
  );
}
