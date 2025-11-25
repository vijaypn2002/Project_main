// src/pages/CartPage.jsx
import { useEffect, useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api.js";

function formatINR(v) {
  if (v == null || v === "") return "₹0";
  const n = Number(v);
  if (!Number.isFinite(n)) return `₹${v}`;
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

function cls(...xs) {
  return xs.filter(Boolean).join(" ");
}

export default function CartPage() {
  const [cart, setCart] = useState(null);
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyIds, setBusyIds] = useState(() => new Set()); // per-item busy

  const isItemBusy = useCallback((id) => busyIds.has(id), [busyIds]);
  const setItemBusy = useCallback((id, on) => {
    setBusyIds((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  const load = useCallback(async () => {
    setErr("");
    try {
      // public GET to avoid Authorization header
      const r = await api.get("/cart/", { params: { _public: 1 } });
      setCart(r.data);
    } catch (e) {
      setErr(
        e?.response?.data?.detail ||
          "Could not load cart. Please refresh the page."
      );
      setCart({
        version: null,
        items: [],
        subtotal: 0,
        discount_total: 0,
        tax_total: 0,
        shipping_total: 0,
        grand_total: 0,
        coupon: null,
      });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const items = cart?.items || [];
  const itemCount = useMemo(
    () => items.reduce((s, i) => s + Number(i.qty || 0), 0),
    [items]
  );

  const maxQty = Number(cart?.max_qty || 0) || null; // optional (if API exposes CART_MAX_QTY)

  async function applyCoupon() {
    const codeTrim = code.trim();
    if (!codeTrim) return;
    setBusy(true);
    setErr("");
    try {
      await api.post(
        "/cart/apply-coupon/",
        { code: codeTrim },
        { params: { _public: 1 } }
      );
      setCode("");
      await load();
    } catch (e) {
      const status = e?.response?.status;
      const msg =
        e?.response?.data?.detail ||
        e?.response?.data?.message ||
        (status === 429
          ? "Too many attempts. Please wait a moment and try again."
          : "Coupon failed. Check the code and try again.");
      setErr(msg);
    } finally {
      setBusy(false);
    }
  }

  async function removeCoupon() {
    setBusy(true);
    setErr("");
    try {
      await api.post(
        "/cart/apply-coupon/",
        { code: "" },
        { params: { _public: 1 } }
      );
      await load();
    } catch (e) {
      setErr(
        e?.response?.data?.detail || "Could not remove coupon. Please retry."
      );
    } finally {
      setBusy(false);
    }
  }

  // small helper to show better stock messages from backend (409)
  function prettifyQtyError(e) {
    const status = e?.response?.status;
    if (status === 429) {
      return "You're doing that too quickly. Please slow down and try again.";
    }
    const raw =
      e?.response?.data?.detail ||
      e?.response?.data?.message ||
      "Could not update quantity.";
    // Try to pull out an available number if present
    const m = String(raw).match(/Available:\s*(\d+)/i);
    if (status === 409 && m && m[1]) {
      const avail = Number(m[1]);
      return `Stock changed — only ${avail} left.`;
    }
    return raw;
  }

  async function changeQty(itemId, nextQty) {
    if (nextQty < 1) nextQty = 1;
    if (maxQty && nextQty > maxQty) nextQty = maxQty;

    // optimistic UI: update locally first
    const prev = cart;
    const next = {
      ...cart,
      items: (cart?.items || []).map((it) =>
        it.id === itemId ? { ...it, qty: nextQty } : it
      ),
    };
    setCart(next);

    setItemBusy(itemId, true);
    setErr("");
    try {
      await api.patch(
        `/cart/items/${itemId}/`,
        { qty: nextQty },
        { params: { _public: 1 } }
      );
      await load();
    } catch (e) {
      setCart(prev); // rollback
      setErr(prettifyQtyError(e));
    } finally {
      setItemBusy(itemId, false);
    }
  }

  async function removeItem(itemId) {
    setItemBusy(itemId, true);
    setErr("");
    try {
      await api.delete(`/cart/items/${itemId}/`, { params: { _public: 1 } });
      await load();
    } catch (e) {
      setErr(
        e?.response?.data?.detail || "Could not remove item. Please retry."
      );
    } finally {
      setItemBusy(itemId, false);
    }
  }

  if (!cart && !err) {
    return (
      <div className="h-40 rounded-xl bg-white shadow-sm animate-pulse" />
    );
  }
  if (err && !cart) {
    return <div className="text-sm text-red-600">{err}</div>;
  }

  const canCheckout = items.length > 0;

  // Optional free-shipping UI if backend exposes a threshold & current taxable
  const freeOver = Number(cart?.free_shipping_threshold || 0) || 0;
  const currentTaxable = Number(
    (cart?.subtotal || 0) - (cart?.discount_total || 0)
  );
  const toFree = Math.max(0, freeOver - currentTaxable);
  const progress =
    freeOver > 0 ? Math.min(100, Math.round((currentTaxable / freeOver) * 100)) : 0;

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your cart</h1>
          <p className="text-sm text-gray-600">
            Review your items and apply a coupon before checkout.
          </p>
        </div>
        <div className="text-sm text-gray-500">
          Items: <span className="font-medium">{itemCount}</span>
        </div>
      </div>

      {!!err && (
        <div
          role="alert"
          aria-live="polite"
          className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {err}
        </div>
      )}

      <div className="grid gap-8 md:grid-cols-3">
        {/* Left: items + coupon */}
        <div className="md:col-span-2 space-y-4">
          {/* Items card */}
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            {items.length === 0 ? (
              <div className="text-sm text-gray-600 py-6 text-center">
                <div className="font-medium mb-1">Your cart is empty</div>
                <p className="text-gray-500 mb-3">
                  Add products to your cart to see them here.
                </p>
                <Link
                  to="/"
                  className="inline-flex items-center rounded-lg border px-4 py-2 text-sm text-gray-800 hover:bg-gray-50"
                >
                  Continue shopping
                </Link>
              </div>
            ) : (
              <ul className="divide-y">
                {items.map((it) => {
                  const img =
                    it.image_url || it.image || it.thumbnail || it.thumb || "";
                  const disabled = busy || isItemBusy(it.id);
                  const each = Number(it.price || 0);
                  const lineTotal = each * Number(it.qty || 0);

                  return (
                    <li
                      key={it.id}
                      className="flex items-start justify-between gap-3 py-3"
                    >
                      {/* Thumb + name */}
                      <div className="flex min-w-0 flex-1 items-start gap-3">
                        <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg border bg-white">
                          {img ? (
                            <img
                              src={img}
                              alt={it.name || "Product image"}
                              className="h-full w-full object-cover"
                              loading="lazy"
                            />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center text-xs text-gray-400">
                              No image
                            </div>
                          )}
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="truncate font-medium text-gray-900">
                            {it.name}
                          </div>
                          <div className="text-xs text-gray-500">
                            SKU: {it.sku}
                          </div>

                          {/* Backorder status */}
                          {it.backordered && (
                            <div className="mt-1 inline-flex items-center gap-2 rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-800">
                              Backordered
                              {it.expected_date && (
                                <span className="text-amber-700">
                                  (ETA:{" "}
                                  {new Date(
                                    it.expected_date
                                  ).toLocaleDateString()}
                                  )
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Qty controls */}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() =>
                            changeQty(it.id, Number(it.qty || 1) - 1)
                          }
                          className={cls(
                            "rounded border px-2 py-1 text-sm hover:bg-gray-50",
                            disabled && "opacity-60 cursor-not-allowed"
                          )}
                          disabled={disabled}
                          aria-label="Decrease quantity"
                        >
                          −
                        </button>
                        <div
                          className="w-12 select-none text-center text-sm"
                          aria-live="polite"
                          aria-atomic="true"
                        >
                          x{it.qty}
                        </div>
                        <button
                          onClick={() =>
                            changeQty(it.id, Number(it.qty || 0) + 1)
                          }
                          className={cls(
                            "rounded border px-2 py-1 text-sm hover:bg-gray-50",
                            (disabled ||
                              (maxQty && Number(it.qty || 0) >= maxQty)) &&
                              "opacity-60 cursor-not-allowed"
                          )}
                          disabled={
                            disabled || (maxQty && Number(it.qty || 0) >= maxQty)
                          }
                          aria-label="Increase quantity"
                          title={
                            maxQty && Number(it.qty || 0) >= maxQty
                              ? `Max allowed is ${maxQty}`
                              : undefined
                          }
                        >
                          +
                        </button>
                        <button
                          onClick={() => removeItem(it.id)}
                          className={cls(
                            "ml-2 text-xs text-red-600 hover:text-red-700 hover:underline",
                            disabled && "opacity-60 cursor-not-allowed"
                          )}
                          disabled={disabled}
                        >
                          Remove
                        </button>
                      </div>

                      {/* Price */}
                      <div className="ml-4 shrink-0 text-right text-sm">
                        <div className="font-semibold text-gray-900">
                          {formatINR(each)}
                        </div>
                        <div className="text-xs text-gray-500">each</div>
                        <div className="mt-1 text-xs text-gray-600">
                          Line: <b>{formatINR(lineTotal)}</b>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Coupon card */}
          <div className="rounded-xl border bg-white p-4 shadow-sm flex flex-wrap items-center gap-2">
            <label
              htmlFor="coupon"
              className="text-xs font-medium text-gray-600"
            >
              Coupon code
            </label>
            <input
              id="coupon"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applyCoupon()}
              placeholder="Enter coupon"
              className="w-48 rounded border px-3 py-2 text-sm"
              disabled={busy}
              aria-label="Coupon code"
            />
            <button
              onClick={applyCoupon}
              className="rounded bg-gray-900 px-3 py-2 text-sm text-white disabled:opacity-60"
              disabled={!code.trim() || busy}
            >
              {busy ? "Applying…" : "Apply"}
            </button>

            {cart?.coupon && (
              <>
                <span className="ml-2 text-sm">
                  Applied: <b>{cart.coupon}</b>
                </span>
                <button
                  onClick={removeCoupon}
                  className="ml-2 text-xs underline disabled:opacity-60"
                  disabled={busy}
                >
                  Remove coupon
                </button>
              </>
            )}

            {/* Version badge for debugging / optimistic UIs */}
            {cart?.version && (
              <span className="ml-auto text-[11px] text-gray-400">
                v: {new Date(cart.version).toLocaleString()}
              </span>
            )}
          </div>
        </div>

        {/* Right: summary */}
        <aside className="h-fit rounded-xl border bg-white p-4 shadow-sm">
          {/* Optional free-shipping progress */}
          {freeOver > 0 && (
            <div className="mb-4 rounded-lg bg-gray-50 p-3">
              {toFree > 0 ? (
                <div className="mb-1 text-xs text-gray-700">
                  Add <b>{formatINR(toFree)}</b> more to unlock{" "}
                  <b>free shipping</b>.
                </div>
              ) : (
                <div className="mb-1 text-xs text-green-700">
                  You’ve unlocked <b>free shipping</b>.
                </div>
              )}
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-full bg-black transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Subtotal</span>
            <b>{formatINR(cart?.subtotal)}</b>
          </div>
          <div className="flex justify-between text-sm text-green-600">
            <span>Discount</span>
            <b>-{formatINR(cart?.discount_total)}</b>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Tax</span>
            <b>{formatINR(cart?.tax_total)}</b>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Shipping</span>
            <b>{formatINR(cart?.shipping_total)}</b>
          </div>

          <div className="mt-3 border-t pt-3">
            <div className="flex justify-between items-center">
              <span className="text-base font-medium">Total</span>
              <b className="text-lg">{formatINR(cart?.grand_total)}</b>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Taxes and discounts are included above.
            </p>
          </div>

          {canCheckout ? (
            <Link
              to="/checkout"
              className="mt-4 block rounded-lg bg-black px-4 py-2 text-center text-sm font-medium text-white hover:bg-black/90"
            >
              Checkout
            </Link>
          ) : (
            <button
              type="button"
              className="mt-4 block w-full cursor-not-allowed rounded-lg bg-gray-300 px-4 py-2 text-center text-sm text-gray-600"
              disabled
              aria-disabled="true"
            >
              Checkout
            </button>
          )}

          <Link
            to="/"
            className="mt-2 block text-center text-xs text-gray-500 hover:text-gray-700"
          >
            ← Continue shopping
          </Link>
        </aside>
      </div>
    </div>
  );
}
