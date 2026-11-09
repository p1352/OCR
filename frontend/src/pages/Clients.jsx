import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import { Empty, ErrorBox, Pagination, Spinner, StatusBadge } from "../components/ui";

const emptyForm = { name: "", email: "", phone: "", address: "", notes: "" };

export default function Clients() {
  const [data, setData] = useState(null);
  const [search, setSearch] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = (params = "") => {
    const q = new URLSearchParams(params);
    if (search) q.set("search", search);
    if (showArchived) q.set("status", "archived");
    api.get(`/clients/?${q}`).then((r) => setData(r.data));
  };

  useEffect(load, [search, showArchived]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (editing) await api.patch(`/clients/${editing}/`, form);
      else await api.post("/clients/", form);
      setForm(emptyForm);
      setEditing(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const archive = async (client) => {
    await api.post(`/clients/${client.id}/${client.status === "archived" ? "restore" : "archive"}/`);
    load();
  };

  if (!data) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-bold">Clients</h2>
        <div className="flex gap-2">
          <input
            className="input w-56" placeholder="Rechercher…" aria-label="Rechercher un client"
            value={search} onChange={(e) => setSearch(e.target.value)}
          />
          <label className="flex items-center gap-1 text-sm text-gray-600">
            <input type="checkbox" checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)} />
            Archivés
          </label>
        </div>
      </div>

      <form onSubmit={submit} className="card grid gap-3 sm:grid-cols-2">
        <h3 className="sm:col-span-2 font-semibold">
          {editing ? "Modifier le client" : "Nouveau client"}
        </h3>
        <ErrorBox message={error} />
        <input className="input" placeholder="Nom / raison sociale *" required
          value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="input" type="email" placeholder="E-mail"
          value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input className="input" placeholder="Téléphone"
          value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <input className="input" placeholder="Adresse"
          value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        <textarea className="input sm:col-span-2" placeholder="Notes" rows={2}
          value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        <div className="flex gap-2 sm:col-span-2">
          <button className="btn-primary" disabled={busy}>
            {editing ? "Enregistrer" : "Créer"}
          </button>
          {editing && (
            <button type="button" className="btn-secondary"
              onClick={() => { setEditing(null); setForm(emptyForm); }}>
              Annuler
            </button>
          )}
        </div>
      </form>

      {data.results.length === 0 ? <Empty label="Aucun client." /> : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 text-left text-gray-600">
              <tr>
                <th className="p-3">Nom</th><th className="p-3">Contact</th>
                <th className="p-3">Images</th><th className="p-3">Statut</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.results.map((c) => (
                <tr key={c.id}>
                  <td className="p-3">
                    <Link to={`/clients/${c.id}`} className="font-medium text-brand-600 hover:underline">
                      {c.name}
                    </Link>
                  </td>
                  <td className="p-3 text-gray-600">{c.email || c.phone || "—"}</td>
                  <td className="p-3">{c.image_count}</td>
                  <td className="p-3"><StatusBadge value={c.status} /></td>
                  <td className="p-3">
                    <div className="flex gap-2">
                      <button className="text-brand-600 hover:underline"
                        onClick={() => { setEditing(c.id); setForm({
                          name: c.name, email: c.email, phone: c.phone,
                          address: c.address, notes: c.notes,
                        }); }}>
                        Modifier
                      </button>
                      <button className="text-gray-600 hover:underline" onClick={() => archive(c)}>
                        {c.status === "archived" ? "Restaurer" : "Archiver"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination data={data} onPage={load} />
    </div>
  );
}
