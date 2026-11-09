import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { Spinner, StatusBadge } from "../components/ui";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    Promise.all([
      api.get("/clients/"),
      api.get("/images/"),
      api.get("/conversions/"),
    ]).then(([clients, images, conversions]) => {
      setStats({
        clients: clients.data.count,
        images: images.data.count,
        conversions: conversions.data.count,
      });
      setRecent(conversions.data.results.slice(0, 5));
    });
  }, []);

  if (!stats) return <Spinner />;

  const cards = [
    { label: "Clients", value: stats.clients, to: "/clients" },
    { label: "Images", value: stats.images, to: "/images" },
    { label: "Conversions", value: stats.conversions, to: "/conversions" },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Tableau de bord</h2>
      <div className="grid gap-4 sm:grid-cols-3">
        {cards.map((c) => (
          <Link key={c.label} to={c.to} className="card hover:shadow-md">
            <p className="text-sm text-gray-500">{c.label}</p>
            <p className="mt-1 text-3xl font-bold text-brand-700">{c.value}</p>
          </Link>
        ))}
      </div>
      <div className="card">
        <h3 className="mb-3 font-semibold">Conversions récentes</h3>
        {recent.length === 0 ? (
          <p className="text-sm text-gray-500">
            Aucune conversion. Importez une image pour commencer.
          </p>
        ) : (
          <ul className="divide-y">
            {recent.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2 text-sm">
                <Link to={`/conversions/${c.id}`} className="text-brand-600 hover:underline">
                  {c.conversion_type === "text" ? "Image → texte" : "Image → tableau"} #{c.id}
                  {" — "}{c.image_detail.original_name}
                </Link>
                <StatusBadge value={c.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
