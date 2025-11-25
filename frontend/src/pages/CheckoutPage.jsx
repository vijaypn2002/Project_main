// src/pages/CheckoutPage.jsx
import { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api.js";
import { currentUser } from "../lib/auth";

function formatINR(v) {
  if (v == null) return "₹0";
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

export default function CheckoutPage() {
  const nav = useNavigate();

  // customer + address
  const [email, setEmail] = useState(currentUser.email || "buyer@example.com");
  const [address, setAddress] = useState({
    full_name: "Buyer Test",
    phone: "9999999999",
    line1: "221B Baker Street",
    line2: "",
    city: "Kochi",
    state: "Kerala",
    postal_code: "682001",
    country: "IN",
  });

  // cart + shipping quotes
  const [cartTotals, setCartTotals] = useState(null);
  const [quotes, setQuotes] = useState([]);
  const [shippingId, setShippingId] = useState(null);

  // flow
  const [coupon, setCoupon] = useState("WELCOME10");
  const [loading, setLoading] = useState(false);
  const [order, setOrder] = useState(null);
  const [err, setErr] = useState("");

  const canSubmit = useMemo(
    () =>
      !!email &&
      !!address.full_name &&
      !!address.phone &&
      !!address.line1 &&
      !!address.city &&
      !!address.state &&
      !!address.postal_code &&
      !!address.country &&
      (cartTotals?.items?.length || 0) > 0,
    [email, address, cartTotals]
  );

  // persist email for Orders page demo/public mode
  useEffect(() => {
    if (email) currentUser.email = email;
  }, [email]);

  // load cart totals (public GET to avoid Authorization header)
  useEffect(() => {
    (async () => {
      try {
        const r = await api.get("/cart/", { params: { _public: 1 } });
        setCartTotals(r.data);
      } catch {
        setCartTotals(null);
      }
    })();
  }, []);

  // fetch shipping quotes after we know the subtotal
  const loadQuotes = useCallback(async () => {
    if (!cartTotals?.subtotal) return;
    try {
      const body = { subtotal: cartTotals.subtotal };
      const r = await api.post("/shipping/quote/", body, { params: { _public: 1 } });
      const list = r.data || [];
      setQuotes((prev) => {
        // keep previous selection if still present
        const stillThere = list.some((q) => q.id === shippingId);
        if (!stillThere) {
          setShippingId(list.length ? list[0].id : null);
        }
        return list;
      });
      if (!shippingId && list.length) setShippingId(list[0].id);
    } catch {
      setQuotes([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cartTotals?.subtotal, shippingId]);

  useEffect(() => {
    loadQuotes();
  }, [loadQuotes]);

  function prettifyError(e) {
    const status = e?.response?.status;
    if (status === 429) return "Too many requests — please try again in a moment.";
    const raw =
      e?.response?.data?.detail ||
      e?.response?.data?.message ||
      "Could not place order.";
    if (status === 409) {
      // Try to show nicer stock race message if backend included "Available: N"
      const m = String(raw).match(/Available:\s*(\d+)/i);
      if (m && m[1]) return `Stock changed — only ${m[1]} left on one or more items.`;
    }
    return raw;
  }

  async function placeOrder(e) {
    e?.preventDefault?.();
    if (!canSubmit || loading) return;

    setLoading(true);
    setErr("");
    try {
      const payload = {
        email: (email || "").trim(),
        shipping_address: {
          ...address,
          country: (address.country || "IN").toUpperCase().slice(0, 2),
        },
      };
      const c = (coupon || "").trim().toUpperCase();
      if (c) payload.coupon_code = c;
      if (shippingId) payload.shipping_method_id = shippingId;

      const r = await api.post("/checkout/", payload, { params: { _public: 1 } });
      setOrder(r.data);
    } catch (e2) {
      setErr(prettifyError(e2));
    } finally {
      setLoading(false);
    }
  }

  const selectedQuote = useMemo(() => {
    if (!quotes?.length) return null;
    return quotes.find((x) => x.id === shippingId) || quotes[0];
  }, [quotes, shippingId]);

  if (order) {
    return (
      <div className="max-w-lg">
        <h2 className="mb-2 text-2xl font-bold">Order placed</h2>
        <div className="mb-2">
          Order ID: <b>#{order.id}</b>
        </div>
        <div className="mb-4">
          Total: <b>{formatINR(order.total)}</b>
        </div>
        <button onClick={() => nav("/orders")} className="rounded bg-black px-4 py-2 text-white">
          View Orders
        </button>
      </div>
    );
  }

  const items = cartTotals?.items || [];
  const estShipping = selectedQuote ? selectedQuote.rate : null;

  return (
    <form onSubmit={placeOrder} className="grid gap-8 md:grid-cols-2">
      <div className="space-y-3">
        <h2 className="text-xl font-semibold">Shipping details</h2>

        <label className="block">
          <span className="mb-1 block text-sm text-gray-600">Email</span>
          <input
            type="email"
            required
            className="w-full rounded border px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            disabled={loading}
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm text-gray-600">Full name</span>
          <input
            required
            className="w-full rounded border px-3 py-2"
            value={address.full_name}
            onChange={(e) => setAddress({ ...address, full_name: e.target.value })}
            placeholder="Full name"
            disabled={loading}
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm text-gray-600">Phone</span>
          <input
            inputMode="numeric"
            pattern="[0-9]{10,}"
            title="Enter a valid phone number"
            required
            className="w-full rounded border px-3 py-2"
            value={address.phone}
            onChange={(e) => setAddress({ ...address, phone: e.target.value })}
            placeholder="10-digit mobile"
            disabled={loading}
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm text-gray-600">Address line 1</span>
          <input
            required
            className="w-full rounded border px-3 py-2"
            value={address.line1}
            onChange={(e) => setAddress({ ...address, line1: e.target.value })}
            placeholder="Address line 1"
            disabled={loading}
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm text-gray-600">Address line 2</span>
          <input
            className="w-full rounded border px-3 py-2"
            value={address.line2}
            onChange={(e) => setAddress({ ...address, line2: e.target.value })}
            placeholder="Apartment, suite, etc. (optional)"
            disabled={loading}
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1 block text-sm text-gray-600">City</span>
            <input
              required
              className="w-full rounded border px-3 py-2"
              value={address.city}
              onChange={(e) => setAddress({ ...address, city: e.target.value })}
              placeholder="City"
              disabled={loading}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-gray-600">State</span>
            <input
              required
              className="w-full rounded border px-3 py-2"
              value={address.state}
              onChange={(e) => setAddress({ ...address, state: e.target.value })}
              placeholder="State"
              disabled={loading}
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1 block text-sm text-gray-600">PIN</span>
            <input
              inputMode="numeric"
              pattern="[0-9]{6}"
              title="6-digit PIN code"
              required
              className="w-full rounded border px-3 py-2"
              value={address.postal_code}
              onChange={(e) => setAddress({ ...address, postal_code: e.target.value })}
              placeholder="682001"
              disabled={loading}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-gray-600">Country</span>
            <input
              maxLength={2}
              className="w-full rounded border px-3 py-2"
              value={address.country}
              onChange={(e) =>
                setAddress({ ...address, country: e.target.value.toUpperCase() })
              }
              placeholder="IN"
              disabled={loading}
            />
          </label>
        </div>

        <label className="block">
          <span className="mb-1 block text-sm text-gray-600">Coupon (optional)</span>
          <input
            className="w-full rounded border px-3 py-2"
            value={coupon}
            onChange={(e) => setCoupon(e.target.value)}
            placeholder="WELCOME10"
            disabled={loading}
          />
        </label>

        {/* Shipping options */}
        <div className="mt-4">
          <h3 className="mb-2 font-semibold">Shipping method</h3>
          {quotes.length === 0 ? (
            <div className="text-sm text-gray-600">No shipping options yet.</div>
          ) : (
            <fieldset className="space-y-2">
              {quotes.map((q) => (
                <label key={q.id} className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="ship"
                    value={q.id}
                    checked={shippingId === q.id}
                    onChange={() => setShippingId(q.id)}
                    className="h-4 w-4"
                    disabled={loading}
                  />
                  <span className="text-sm">
                    {q.name} ({q.code}) — <b>{formatINR(q.rate)}</b>
                  </span>
                </label>
              ))}
            </fieldset>
          )}
        </div>

        {err && (
          <div
            role="alert"
            aria-live="polite"
            className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {err}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !canSubmit}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-60"
        >
          {loading ? "Placing…" : "Place order"}
        </button>
      </div>

      {/* Summary */}
      <div className="h-fit rounded-xl border p-4">
        <h3 className="mb-3 font-semibold">Summary</h3>

        {!cartTotals ? (
          <div className="text-sm text-gray-500">Loading cart…</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-gray-600">Your cart is empty.</div>
        ) : (
          <>
            {/* compact items list */}
            <ul className="mb-3 divide-y">
              {items.map((it) => {
                const each = Number(it.price || 0);
                const line = each * Number(it.qty || 0);
                return (
                  <li key={it.id} className="flex items-center justify-between py-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm">{it.name}</div>
                      <div className="text-xs text-gray-500">
                        x{it.qty} • {formatINR(each)}
                      </div>
                    </div>
                    <div className="ml-3 shrink-0 text-right text-sm font-medium">
                      {formatINR(line)}
                    </div>
                  </li>
                );
              })}
            </ul>

            <div className="flex justify-between">
              <span>Subtotal</span>
              <b>{formatINR(cartTotals.subtotal)}</b>
            </div>
            <div className="flex justify-between text-sm text-green-600">
              <span>Discount</span>
              <b>-{formatINR(cartTotals.discount_total)}</b>
            </div>
            <div className="flex justify-between text-sm">
              <span>Tax</span>
              <b>{formatINR(cartTotals.tax_total)}</b>
            </div>
            <div className="flex justify-between text-sm">
              <span>Shipping (estimated)</span>
              <b>{estShipping != null ? formatINR(estShipping) : "—"}</b>
            </div>
            <div className="mt-1 text-xs text-gray-500">
              Final total will reflect the selected method during order creation.
            </div>
          </>
        )}
      </div>
    </form>
  );
}
