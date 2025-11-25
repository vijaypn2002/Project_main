// src/admin/pages/Banners.jsx
import { useEffect, useState } from "react";
import api from "../../lib/api";

export default function AdminBanners() {
  const [rows, setRows] = useState([]);
  const [file, setFile] = useState(null);
  const [form, setForm] = useState({ title: "", alt: "", href: "", sort: 0, is_active: true });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    try {
      const r = await api.get("/backoffice/banners/");
      setRows(r.data || []);
    } catch (e) {
      setErr("Failed to load banners.");
      setRows([]);
    }
  }
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setErr("");
    try {
      const fd = new FormData();
      if (file) fd.append("image", file);
      Object.entries(form).forEach(([k, v]) => fd.append(k, v));
      await api.post("/backoffice/banners/", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setForm({ title: "", alt: "", href: "", sort: 0, is_active: true });
      setFile(null);
      await load();
    } catch {
      setErr("Failed to create banner.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(row) {
    try {
      await api.patch(`/backoffice/banners/${row.id}/`, { is_active: !row.is_active });
      await load();
    } catch {
      alert("Failed to update banner");
    }
  }

  async function remove(row) {
    if (!confirm("Delete this banner?")) return;
    try {
      await api.delete(`/backoffice/banners/${row.id}/`);
      await load();
    } catch {
      alert("Delete failed");
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={create} className="grid md:grid-cols-2 gap-3">
        <div className="md:col-span-2 font-medium">Add banner</div>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Image</div>
          <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Title</div>
          <input className="border rounded px-3 py-2 w-full" value={form.title}
                 onChange={(e) => setForm({ ...form, title: e.target.value })}/>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Alt text</div>
          <input className="border rounded px-3 py-2 w-full" value={form.alt}
                 onChange={(e) => setForm({ ...form, alt: e.target.value })}/>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Link (href)</div>
          <input className="border rounded px-3 py-2 w-full" value={form.href}
                 onChange={(e) => setForm({ ...form, href: e.target.value })}/>
        </label>
        <label className="block">
          <div className="text-xs text-gray-600 mb-1">Sort</div>
          <input type="number" className="border rounded px-3 py-2 w-full" value={form.sort}
                 onChange={(e) => setForm({ ...form, sort: Number(e.target.value) || 0 })}/>
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.is_active}
                 onChange={(e) => setForm({ ...form, is_active: e.target.checked })}/>
          <span className="text-sm">Active</span>
        </label>
        <div className="md:col-span-2">
          {err && <div className="text-sm text-red-600 mb-2">{err}</div>}
          <button disabled={busy} className="px-3 py-2 rounded bg-black text-white disabled:opacity-60">
            {busy ? "Saving…" : "Create"}
          </button>
        </div>
      </form>

      <div>
        <div className="font-medium mb-2">Existing banners</div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {rows.map((r) => (
            <div key={r.id} className="border rounded-lg p-3">
              <div className="aspect-[3/1] rounded bg-gray-50 overflow-hidden mb-2">
                {r.image ? <img src={r.image} alt={r.alt} className="w-full h-full object-cover" /> : null}
              </div>
              <div className="text-sm font-medium truncate">{r.title || "—"}</div>
              <div className="text-xs text-gray-500 truncate">{r.href || "—"}</div>
              <div className="mt-2 flex items-center justify-between">
                <button onClick={() => toggleActive(r)} className="text-sm underline">
                  {r.is_active ? "Deactivate" : "Activate"}
                </button>
                <button onClick={() => remove(r)} className="text-sm text-rose-600 underline">
                  Delete
                </button>
              </div>
            </div>
          ))}
          {rows.length === 0 && <div className="text-sm text-gray-600">No banners yet.</div>}
        </div>
      </div>
    </div>
  );
}
