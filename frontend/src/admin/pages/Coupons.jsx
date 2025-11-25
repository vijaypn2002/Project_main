// src/admin/pages/Coupons.jsx
import { useEffect, useState } from "react";
import api from "../../lib/api";

const EMPTY = {
  code: "",
  discount_type: "percent", // or "amount" based on your model choices
  value: 10,
  starts_at: "",
  ends_at: "",
  min_subtotal: "",
  max_uses: "",
  is_active: true,
};

export default function AdminCoupons() {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    try {
      const r = await api.get("/backoffice/coupons/");
      setRows(r.data || []);
    } catch {
      setErr("Failed to load coupons.");
      setRows([]);
    }
  }
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setErr("");
    try {
      const payload = { ...form };
      await api.post("/backoffice/coupons/", payload);
      setForm(EMPTY);
      await load();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to create coupon.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(row) {
    try {
      await api.patch(`/backoffice/coupons/${row.id}/`, { is_active: !row.is_active });
      await load();
    } catch { alert("Update failed"); }
  }

  async function remove(row) {
    if (!confirm("Delete this coupon?")) return;
    try {
      await api.delete(`/backoffice/coupons/${row.id}/`);
      await load();
    } catch { alert("Delete failed"); }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={create} className="grid md:grid-cols-3 gap-3">
        <div className="md:col-span-3 font-medium">Add coupon</div>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Code</div>
          <input className="border rounded px-3 py-2 w-full" value={form.code}
                 onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} required/>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Type</div>
          <select className="border rounded px-3 py-2 w-full" value={form.discount_type}
                  onChange={(e) => setForm({ ...form, discount_type: e.target.value })}>
            <option value="percent">Percent</option>
            <option value="amount">Amount</option>
          </select>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Value</div>
          <input type="number" className="border rounded px-3 py-2 w-full" value={form.value}
                 onChange={(e) => setForm({ ...form, value: Number(e.target.value) || 0 })}/>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Starts at</div>
          <input type="datetime-local" className="border rounded px-3 py-2 w-full" value={form.starts_at}
                 onChange={(e) => setForm({ ...form, starts_at: e.target.value })}/>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Ends at</div>
          <input type="datetime-local" className="border rounded px-3 py-2 w-full" value={form.ends_at}
                 onChange={(e) => setForm({ ...form, ends_at: e.target.value })}/>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Min subtotal</div>
          <input type="number" className="border rounded px-3 py-2 w-full" value={form.min_subtotal}
                 onChange={(e) => setForm({ ...form, min_subtotal: e.target.value })}/>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Max uses</div>
          <input type="number" className="border rounded px-3 py-2 w-full" value={form.max_uses}
                 onChange={(e) => setForm({ ...form, max_uses: e.target.value })}/>
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.is_active}
                 onChange={(e) => setForm({ ...form, is_active: e.target.checked })}/>
          <span className="text-sm">Active</span>
        </label>
        <div className="md:col-span-3">
          {err && <div className="text-sm text-red-600 mb-2">{err}</div>}
          <button disabled={busy} className="px-3 py-2 rounded bg-black text-white disabled:opacity-60">
            {busy ? "Saving…" : "Create"}
          </button>
        </div>
      </form>

      <div>
        <div className="font-medium mb-2">Existing coupons</div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="py-2 pr-3">Code</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Value</th>
                <th className="py-2 pr-3">Active</th>
                <th className="py-2 pr-3">Used</th>
                <th className="py-2 pr-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b">
                  <td className="py-2 pr-3 font-mono">{r.code}</td>
                  <td className="py-2 pr-3">{r.discount_type}</td>
                  <td className="py-2 pr-3">{r.value}</td>
                  <td className="py-2 pr-3">{r.is_active ? "Yes" : "No"}</td>
                  <td className="py-2 pr-3">{r.used_count ?? 0}</td>
                  <td className="py-2 pr-3">
                    <button onClick={() => toggle(r)} className="underline mr-3">
                      {r.is_active ? "Deactivate" : "Activate"}
                    </button>
                    <button onClick={() => remove(r)} className="underline text-rose-600">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-gray-600">No coupons yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
