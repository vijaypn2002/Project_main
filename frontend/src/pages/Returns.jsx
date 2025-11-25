// src/pages/Returns.jsx
import { useEffect, useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import api from "../lib/api";
import { auth } from "../lib/auth";

function StatusPill({ status }) {
  const s = String(status || "").toLowerCase();
  const styles = {
    requested: "bg-amber-100 text-amber-800",
    approved: "bg-blue-100 text-blue-800",
    rejected: "bg-red-100 text-red-800",
    received: "bg-indigo-100 text-indigo-800",
    refunded: "bg-green-100 text-green-800",
  };
  const cls = styles[s] || "bg-gray-100 text-gray-800";
  return <span className={`text-xs px-2 py-1 rounded-full capitalize ${cls}`}>{s || "—"}</span>;
}

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 });
function Money({ children }) {
  const n = Number(children ?? 0);
  return <span>{inr.format(Number.isFinite(n) ? n : 0)}</span>;
}

export default function Returns() {
  const [sp, setSp] = useSearchParams();
  const orderIdFromUrl = Number(sp.get("order") || 0);

  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);        // list for picker
  const [order, setOrder] = useState(null);        // selected order (details)
  const [items, setItems] = useState([]);
  const [rmas, setRmas] = useState([]);            // returns on this order
  const [attsByReturn, setAttsByReturn] = useState({}); // { [returnId]: [{id,file,mime,size,created_at}, ...] }
  const [qty, setQty] = useState(1);
  const [reason, setReason] = useState("Did not fit");
  const [selectedItem, setSelectedItem] = useState(null);
  const [file, setFile] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  const isAuthed = !!auth.access();

  // helper: reload RMAs + attachments for current order
  async function loadReturns(orderId) {
    try {
      const r = await api.get(`/orders/${orderId}/returns/`);
      const list = r.data || [];
      setRmas(list);

      // fetch attachments for each RMA (small lists → OK)
      const entries = await Promise.all(
        list.map(async (rr) => {
          try {
            const ra = await api.get(`/orders/${orderId}/returns/${rr.id}/attachments/`);
            return [rr.id, ra.data || []];
          } catch {
            return [rr.id, []];
          }
        })
      );
      setAttsByReturn(Object.fromEntries(entries));
    } catch {
      setRmas([]);
      setAttsByReturn({});
    }
  }

  // Load either: order picker (when no ?order=) OR the chosen order + its returns
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!isAuthed) {
        setLoading(false);
        return;
      }
      try {
        setErr("");
        setLoading(true);

        if (!orderIdFromUrl) {
          // No order chosen → show recent orders so user can pick one
          const res = await api.get("/orders/me/");
          if (!cancelled) {
            setOrders(res.data || []);
          }
          return;
        }

        // We have an order id → load that order + its returns
        const o = await api.get(`/orders/me/${orderIdFromUrl}/`);
        if (!cancelled) {
          setOrder(o.data);
          setItems(o.data.items || []);
        }
        await loadReturns(orderIdFromUrl);
      } catch (e) {
        if (!cancelled) {
          setErr(e?.response?.data?.detail || "Failed to load returns data.");
          setOrders([]);
          setOrder(null);
          setItems([]);
          setRmas([]);
          setAttsByReturn({});
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAuthed, orderIdFromUrl]);

  const maxQtyForSelected = useMemo(() => {
    const it = items.find((i) => i.id === selectedItem);
    return it ? Number(it.qty || 1) : 1;
  }, [items, selectedItem]);

  async function createRma() {
    if (!selectedItem || !order) return;
    setBusy(true);
    setErr("");
    try {
      const body = {
        order_item_id: selectedItem,
        qty: Math.max(1, Math.min(qty, maxQtyForSelected)),
        reason: (reason || "").slice(0, 200),
      };
      await api.post(`/orders/${order.id}/returns/`, body);
      // reload list to reflect server state (and attachments map)
      await loadReturns(order.id);
      // reset form
      setSelectedItem(null);
      setQty(1);
      setReason("Did not fit");
    } catch (e) {
      setErr(e?.response?.data?.detail || "Could not create return.");
    } finally {
      setBusy(false);
    }
  }

  async function upload(attReturnId) {
    if (!file || !order) return;
    setUploading(true);
    setErr("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      // Let the browser set the multipart boundary; do NOT hardcode Content-Type
      await api.post(`/orders/${order.id}/returns/${attReturnId}/attachments/`, fd);
      const r = await api.get(`/orders/${order.id}/returns/${attReturnId}/attachments/`);
      setAttsByReturn((m) => ({ ...m, [attReturnId]: r.data || [] }));
      setFile(null);
      alert("File uploaded");
    } catch (e) {
      setErr(e?.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  function chooseOrder(id) {
    // write ?order=id to URL, which triggers the effect above
    setSp({ order: String(id) }, { replace: true });
  }

  if (!isAuthed) {
    return (
      <div className="text-sm">
        Please{" "}
        <Link to="/login" className="text-indigo-600 underline">
          login
        </Link>{" "}
        to manage returns.
      </div>
    );
  }

  if (loading) {
    return <div>Loading…</div>;
  }

  // --------- Order picker (no ?order=) ----------
  if (!orderIdFromUrl) {
    if (!orders.length) {
      return <div className="text-sm text-gray-600">No orders found.</div>;
    }
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold">Pick an order to return</h2>
        {orders.map((o) => (
          <div key={o.id} className="rounded border bg-white p-3">
            <div className="flex items-center justify-between">
              <div>
                Order <b>#{o.id}</b>
              </div>
              <div className="text-sm">
                <StatusPill status={o.status} />
              </div>
            </div>
            <div className="text-sm">
              Total: <Money>{o.total}</Money>
            </div>
            <button onClick={() => chooseOrder(o.id)} className="mt-2 rounded bg-black px-3 py-1 text-white">
              Return this order
            </button>
          </div>
        ))}
      </div>
    );
  }

  // --------- Return workflow for a chosen order ----------
  if (!order) {
    return <div className="text-sm text-red-600">Could not load order #{orderIdFromUrl}.</div>;
  }

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div className="space-y-3">
        <h2 className="text-xl font-bold">Create return for order #{order.id}</h2>

        <label className="text-xs text-gray-600">Item</label>
        <select
          className="w-full rounded border px-3 py-2"
          value={selectedItem || ""}
          onChange={(e) => setSelectedItem(Number(e.target.value) || null)}
        >
          <option value="">Select item</option>
          {items.map((it) => (
            <option key={it.id} value={it.id}>
              {it.name} (x{it.qty})
            </option>
          ))}
        </select>

        <label className="text-xs text-gray-600">Quantity</label>
        <input
          type="number"
          min={1}
          max={maxQtyForSelected}
          value={qty}
          onChange={(e) => {
            const v = Math.max(1, Math.min(Number(e.target.value) || 1, maxQtyForSelected));
            setQty(v);
          }}
          className="w-32 rounded border px-3 py-2"
        />

        <label className="text-xs text-gray-600">Reason</label>
        <input
          type="text"
          maxLength={200}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g., Did not fit / Damaged"
          className="w-full rounded border px-3 py-2"
        />

        {err && <div className="text-sm text-red-600">{err}</div>}

        <button
          onClick={createRma}
          disabled={!selectedItem || busy}
          className="rounded bg-black px-3 py-2 text-white disabled:opacity-60"
        >
          {busy ? "Creating…" : "Create RMA"}
        </button>
      </div>

      <div>
        <h2 className="mb-2 text-xl font-bold">Your returns</h2>
        <div className="space-y-3">
          {rmas.map((r) => (
            <div key={r.id} className="rounded border bg-white p-3">
              <div className="flex items-center justify-between">
                <div>
                  RMA <b>#{r.id}</b> for item #{r.order_item_id}
                </div>
                <div className="text-sm">
                  <StatusPill status={r.status} />
                </div>
              </div>
              <div className="mb-2 text-sm text-gray-600">
                Qty {r.qty} — {r.reason || "—"}
              </div>

              {/* Attachments list */}
              <div className="mb-2">
                <div className="text-xs font-semibold text-gray-700">Attachments</div>
                <div className="mt-1 space-y-1 text-sm">
                  {(attsByReturn[r.id] || []).length ? (
                    (attsByReturn[r.id] || []).map((a) => (
                      <div key={a.id}>
                        <a
                          href={a.file}
                          target="_blank"
                          rel="noreferrer"
                          className="text-indigo-600 underline"
                        >
                          {a.file?.split("/").pop() || `file-${a.id}`}
                        </a>{" "}
                        <span className="text-gray-500">
                          ({a.mime || "file"}, {(a.size || 0) / 1024 >> 0} KB)
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="text-gray-500">No attachments yet.</div>
                  )}
                </div>
              </div>

              {/* Upload proof / photos */}
              <div className="flex items-center gap-2">
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <button
                  onClick={() => upload(r.id)}
                  className="rounded bg-gray-900 px-3 py-1 text-white disabled:opacity-60"
                  disabled={!file || uploading}
                >
                  {uploading ? "Uploading…" : "Upload"}
                </button>
              </div>
            </div>
          ))}
          {rmas.length === 0 && <div className="text-sm text-gray-600">No returns yet.</div>}
        </div>
      </div>
    </div>
  );
}
