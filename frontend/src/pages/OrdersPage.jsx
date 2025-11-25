// src/pages/OrdersPage.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import api from "../lib/api.js";
import { currentUser } from "../lib/auth.js";
import { auth } from "../lib/auth.js";

const PLACEHOLDER = "/placeholder-product.png";

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
});
function Money({ children }) {
  const n = Number(children ?? 0);
  return <span>{inr.format(Number.isFinite(n) ? n : 0)}</span>;
}

function StatusPill({ status }) {
  const s = String(status || "").toLowerCase();
  const styles = {
    created: "bg-gray-100 text-gray-800",
    paid: "bg-blue-100 text-blue-800",
    picking: "bg-amber-100 text-amber-800",
    shipped: "bg-indigo-100 text-indigo-800",
    delivered: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800",
    returned: "bg-purple-100 text-purple-800",
    refunded: "bg-rose-100 text-rose-800",
  };
  const cls = styles[s] || "bg-gray-100 text-gray-800";
  return (
    <span className={`text-xs px-2 py-1 rounded-full capitalize ${cls}`} aria-label={`Status: ${s || "unknown"}`}>
      {s || "—"}
    </span>
  );
}

function OrderSkeleton() {
  return (
    <div className="border rounded-xl p-4 bg-white animate-pulse">
      <div className="mb-3 flex justify-between">
        <div className="h-4 w-32 rounded bg-gray-200" />
        <div className="h-5 w-20 rounded-full bg-gray-200" />
      </div>
      {[...Array(2)].map((_, i) => (
        <div key={i} className="mt-3 flex items-center gap-3">
          <div className="h-16 w-16 rounded-md bg-gray-200" />
          <div className="flex-1">
            <div className="mb-1 h-4 w-48 rounded bg-gray-200" />
            <div className="h-3 w-24 rounded bg-gray-200" />
          </div>
          <div className="h-4 w-8 rounded bg-gray-200" />
          <div className="h-4 w-16 rounded bg-gray-200" />
        </div>
      ))}
      <div className="mt-4 grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i}>
            <div className="mb-2 h-3 w-20 rounded bg-gray-200" />
            <div className="h-4 w-16 rounded bg-gray-200" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function OrdersPage() {
  const [orders, setOrders] = useState(null);
  const [err, setErr] = useState("");
  const isAuthed = useMemo(() => !!auth.access(), []);
  const loadedRef = useRef(false);

  async function load() {
    setErr("");
    try {
      let res;
      if (isAuthed) {
        // Authenticated: JWT will be attached automatically
        res = await api.get("/orders/me/");
      } else {
        // Public-by-email demo. Prefer saved email; fallback to demo seed.
        const demoEmail = (currentUser.email || "").trim() || "buyer@example.com";
        res = await api.get("/orders/", { params: { email: demoEmail, _public: 1 } });
      }
      setOrders(res.data || []);
    } catch (e) {
      const status = e?.response?.status;
      if (isAuthed && status === 401 && !loadedRef.current) {
        // Session expired: show demo orders so page isn't empty
        try {
          const demoEmail = (currentUser.email || "").trim() || "buyer@example.com";
          const r2 = await api.get("/orders/", { params: { email: demoEmail, _public: 1 } });
          setOrders(r2.data || []);
          setErr("Session expired. Showing demo orders.");
        } catch {
          setOrders([]);
          setErr("Could not load orders.");
        }
      } else {
        setOrders([]);
        setErr("Could not load orders.");
      }
    } finally {
      loadedRef.current = true;
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthed]);

  if (orders === null) {
    return (
      <div className="space-y-4">
        <OrderSkeleton />
        <OrderSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {!isAuthed && (
        <div className="text-sm text-amber-700">
          Tip: <b>Login</b> to view your orders securely. Showing demo orders.
        </div>
      )}

      {err && (
        <div
          className="flex items-center justify-between rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          role="alert"
          aria-live="polite"
        >
          <span>{err}</span>
          <button onClick={load} className="underline">
            Retry
          </button>
        </div>
      )}

      {orders.length === 0 && <div className="text-sm text-gray-600">No orders found.</div>}

      {orders.map((o) => (
        <div key={o.id} className="rounded-xl border bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm">
              Order <b>#{o.id}</b>
              {o.tracking_number ? (
                <span className="ml-2 text-xs text-gray-500">• Tracking: {o.tracking_number}</span>
              ) : null}
              {o.coupon_code ? (
                <span className="ml-2 text-xs text-green-700">• Coupon: {o.coupon_code}</span>
              ) : null}
            </div>
            <StatusPill status={o.status} />
          </div>

          {(o.items || []).map((it) => (
            <div key={it.id ?? `${o.id}-${it.sku}-${it.qty}`} className="mt-3 flex items-center gap-3">
              <img
                src={it.image_url || PLACEHOLDER}
                alt={it.name || "Product image"}
                className="h-16 w-16 rounded-md border bg-white object-cover"
                onError={(e) => (e.currentTarget.src = PLACEHOLDER)}
                loading="lazy"
                decoding="async"
                width={64}
                height={64}
              />
              <div className="min-w-0 flex-1">
                <div className="line-clamp-2 text-sm font-medium">{it.name}</div>
                <div className="truncate text-xs text-gray-500">SKU: {it.sku}</div>
              </div>
              <div className="shrink-0 text-sm text-gray-600">x{it.qty}</div>
              <div className="shrink-0 text-sm font-medium">
                <Money>{it.line_total}</Money>
              </div>
            </div>
          ))}

          <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-gray-700 sm:grid-cols-4">
            <div>
              <div className="text-xs uppercase text-gray-500">Subtotal</div>
              <div><Money>{o.subtotal}</Money></div>
            </div>
            <div>
              <div className="text-xs uppercase text-gray-500">Shipping</div>
              <div><Money>{o.shipping_total}</Money></div>
            </div>
            <div>
              <div className="text-xs uppercase text-gray-500">Tax</div>
              <div><Money>{o.tax_total}</Money></div>
            </div>
            <div>
              <div className="text-xs uppercase text-gray-500">Total</div>
              <div className="font-semibold"><Money>{o.total}</Money></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
