import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../auth";
import { Empty, ErrorBox, Pagination, Spinner, StatusBadge } from "../components/ui";

const emptyForm = {
  username: "", email: "", first_name: "", last_name: "",
  role: "user", password: "", is_active: true,
};

export default function Users() {
  const { user: current } = useAuth();
  const [data, setData] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = (params = "") => api.get(`/users/${params}`).then((r) => setData(r.data));
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (editing) {
        const { password, ...payload } = form;
        await api.patch(`/users/${editing}/`, payload);
      } else {
        await api.post("/users/", form);
      }
      setForm(emptyForm);
      setEditing(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const toggleActive = async (u) => {
    if (u.id === current.id) return;
    if (u.is_active) await api.delete(`/users/${u.id}/`);
    else await api.patch(`/users/${u.id}/`, { is_active: true });
    load();
  };

  if (!data) return <Spinner />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Utilisateurs</h2>

      <form onSubmit={submit} className="card grid gap-3 sm:grid-cols-2">
        <h3 className="sm:col-span-2 font-semibold">
          {editing ? "Modifier le compte" : "Nouveau compte"}
        </h3>
        <ErrorBox message={error} />
        <input className="input" placeholder="Nom d'utilisateur *" required
          value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        <input className="input" type="email" placeholder="E-mail *" required
          value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input className="input" placeholder="Prénom"
          value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
        <input className="input" placeholder="Nom"
          value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
        <select className="input" value={form.role} aria-label="Rôle"
          onChange={(e) => setForm({ ...form, role: e.target.value })}>
          <option value="user">Utilisateur</option>
          <option value="admin">Administrateur</option>
        </select>
        {!editing && (
          <input className="input" type="password" placeholder="Mot de passe *" required
            autoComplete="new-password"
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        )}
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Compte actif
        </label>
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

      {data.results.length === 0 ? <Empty label="Aucun utilisateur." /> : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 text-left text-gray-600">
              <tr>
                <th className="p-3">Utilisateur</th><th className="p-3">E-mail</th>
                <th className="p-3">Rôle</th><th className="p-3">Statut</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.results.map((u) => (
                <tr key={u.id}>
                  <td className="p-3 font-medium">{u.username}</td>
                  <td className="p-3 text-gray-600">{u.email}</td>
                  <td className="p-3">{u.role === "admin" ? "Administrateur" : "Utilisateur"}</td>
                  <td className="p-3">
                    <StatusBadge value={u.is_active ? "active" : "archived"} />
                  </td>
                  <td className="p-3">
                    <div className="flex gap-2">
                      <button className="text-brand-600 hover:underline"
                        onClick={() => { setEditing(u.id); setForm({
                          username: u.username, email: u.email,
                          first_name: u.first_name, last_name: u.last_name,
                          role: u.role, password: "", is_active: u.is_active,
                        }); }}>
                        Modifier
                      </button>
                      {u.id !== current.id && (
                        <button className="text-gray-600 hover:underline" onClick={() => toggleActive(u)}>
                          {u.is_active ? "Désactiver" : "Réactiver"}
                        </button>
                      )}
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
