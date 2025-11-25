import { useEffect, useState } from "react";
import api from "../../lib/api";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [tops, setTops] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      setErr("");
      try {
        const [s, t] = await Promise.all([
          api.get("/reports/summary"),
          api.get("/reports/top-products?limit=8"),
        ]);
        setSummary(s.data);
        setTops(t.data);
      } catch {
        setErr("Could not load reports.");
      }
    })();
  }, []);

  return (
    <div className="space-y-6">
      {err && <div className="text-sm text-red-600">{err}</div>}

      <section>
        <h2 className="font-semibold mb-3">Last 30 days</h2>
        {!summary ? (
          <div className="text-sm text-gray-600">Loading…</div>
        ) : (
          <div className="grid sm:grid-cols-3 md:grid-cols-6 gap-3">
            <Card label="Orders (created)" value={summary.orders_created} />
            <Card label="Orders (paid-like)" value={summary.orders_paid} />
            <Card label="GMV (₹)" value={summary.gmv} />
            <Card label="AOV (₹)" value={summary.aov} />
            <Card label="Refunds (count)" value={summary.refunds_count} />
            <Card label="Refunds (₹)" value={summary.refunds_amount} />
          </div>
        )}
      </section>

      <section>
        <h2 className="font-semibold mb-3">Top products</h2>
        {!tops ? (
          <div className="text-sm text-gray-600">Loading…</div>
        ) : tops.items.length === 0 ? (
          <div className="text-sm text-gray-600">No data.</div>
        ) : (
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3">
            {tops.items.map((it, i) => (
              <div key={i} className="border rounded-lg p-3">
                <div className="font-medium">{it.name}</div>
                <div className="text-xs text-gray-500">{it.sku}</div>
                <div className="mt-1 text-sm">Qty: {it.qty_sold}</div>
                <div className="text-sm">Revenue: ₹{it.revenue}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Card({ label, value }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}
