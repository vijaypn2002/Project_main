// src/pages/OrderDetail.jsx
import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api.js";
import { auth } from "../lib/auth.js";

const PLACEHOLDER = "/placeholder-product.png";
const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

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
  return <span className={`text-xs px-2 py-1 rounded-full capitalize ${cls}`}>{s || "—"}</span>;
}

export default function OrderDetail() {
  const { id } = useParams();
  const [o, setO] = useState(null);
  const [err, setErr] = useState("");
  const authed = useMemo(() => !!auth.access(), []);

  useEffect(() => {
    (async () => {
      setErr("");
      setO(null);
      try {
        const url = authed ? `/orders/me/${id}/` : `/orders/${id}/`;
        const params = authed ? {} : { params: { email: "buyer@example.com", _public: 1 } };
        const r = await api.get(url, params);
        setO(r.data);
      } catch (e) {
        setErr(e?.response?.data?.detail || "Could not load order.");
      }
    })();
  }, [id, authed]);

  if (err) return <div className="text-sm text-red-600">{err}</div>;
  if (!o) return <div>Loading…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm">
            Order <b>#{o.id}</b>
            {o.tracking_number ? (
              <span className="ml-2 text-xs text-gray-500">• Tracking: {o.tracking_number}</span>
            ) : null}
            {o.coupon_code ? (
              <span className="ml-2 text-xs text-green-700">• Coupon: {o.coupon_code}</span>
            ) : null}
          </div>
          <div className="text-xs text-gray-600">Total: {inr.format(Number(o.total || 0))}</div>
        </div>
        <StatusPill status={o.status} />
      </div>

      <div className="rounded-xl border bg-white divide-y">
        {(o.items || []).map((it) => (
          <div key={it.id ?? `${o.id}-${it.sku}`} className="p-3 flex items-center gap-3">
            <img
              src={it.image_url || PLACEHOLDER}
              alt={it.name}
              className="h-16 w-16 rounded-md border bg-white object-cover"
              onError={(e) => (e.currentTarget.src = PLACEHOLDER)}
              loading="lazy"
              decoding="async"
            />
            <div className="min-w-0 flex-1">
              <div className="line-clamp-2 text-sm font-medium">{it.name}</div>
              <div className="truncate text-xs text-gray-500">SKU: {it.sku}</div>
            </div>
            <div className="shrink-0 text-sm text-gray-600">x{it.qty}</div>
            <div className="shrink-0 text-sm font-medium">{inr.format(Number(it.line_total || 0))}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm text-gray-700 sm:grid-cols-4">
        <div>
          <div className="text-xs uppercase text-gray-500">Subtotal</div>
          <div>{inr.format(Number(o.subtotal || 0))}</div>
        </div>
        <div>
          <div className="text-xs uppercase text-gray-500">Shipping</div>
          <div>{inr.format(Number(o.shipping_total || 0))}</div>
        </div>
        <div>
          <div className="text-xs uppercase text-gray-500">Tax</div>
          <div>{inr.format(Number(o.tax_total || 0))}</div>
        </div>
        <div>
          <div className="text-xs uppercase text-gray-500">Total</div>
          <div className="font-semibold">{inr.format(Number(o.total || 0))}</div>
        </div>
      </div>

      <Link to="/orders" className="text-indigo-600 underline text-sm">
        Back to all orders
      </Link>
    </div>
  );
}
