import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { Empty, Pagination, Spinner, StatusBadge } from "../components/ui";

export default function Conversions() {
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({ status: "", type: "" });

  const load = (params = "") => {
    const q = new URLSearchParams(params);
    if (filters.status) q.set("status", filters.status);
    if (filters.type) q.set("type", filters.type);
    api.get(`/conversions/?${q}`).then((r) => setData(r.data));
  };

  useEffect(load, [filters]);

  if (!data) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-bold">Conversions</h2>
        <div className="flex gap-2">
          <select className="input w-44" value={filters.status} aria-label="Filtrer par statut"
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">Tous les statuts</option>
            <option value="done">Terminées</option>
            <option value="failed">Échouées</option>
            <option value="pending">En attente</option>
            <option value="running">En cours</option>
          </select>
          <select className="input w-44" value={filters.type} aria-label="Filtrer par type"
            onChange={(e) => setFilters({ ...filters, type: e.target.value })}>
            <option value="">Tous les types</option>
            <option value="text">Image → texte</option>
            <option value="table">Image → tableau</option>
          </select>
        </div>
      </div>

      {data.results.length === 0 ? <Empty label="Aucune conversion." /> : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 text-left text-gray-600">
              <tr>
                <th className="p-3">#</th><th className="p-3">Image</th><th className="p-3">Type</th>
                <th className="p-3">Statut</th><th className="p-3">Validation</th>
                <th className="p-3">Date</th><th className="p-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.results.map((c) => (
                <tr key={c.id}>
                  <td className="p-3">{c.id}</td>
                  <td className="p-3">{c.image_detail.original_name}</td>
                  <td className="p-3">{c.conversion_type === "text" ? "Texte" : "Tableau"}</td>
                  <td className="p-3"><StatusBadge value={c.status} /></td>
                  <td className="p-3">
                    <StatusBadge value={c.quality_check?.decision || "none"} />
                  </td>
                  <td className="p-3 text-gray-500">
                    {new Date(c.created_at).toLocaleString("fr-FR")}
                  </td>
                  <td className="p-3">
                    <Link to={`/conversions/${c.id}`} className="text-brand-600 hover:underline">
                      Ouvrir
                    </Link>
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
