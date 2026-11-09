import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api";
import { Spinner, StatusBadge } from "../components/ui";

export default function ClientDetail() {
  const { id } = useParams();
  const [client, setClient] = useState(null);
  const [images, setImages] = useState([]);
  const [conversions, setConversions] = useState([]);

  useEffect(() => {
    api.get(`/clients/${id}/`).then((r) => setClient(r.data));
    api.get(`/clients/${id}/images/`).then((r) => setImages(r.data));
    api.get(`/clients/${id}/conversions/`).then((r) => setConversions(r.data));
  }, [id]);

  if (!client) return <Spinner />;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">{client.name}</h2>
        <p className="text-sm text-gray-500">
          {[client.email, client.phone].filter(Boolean).join(" · ") || "Pas de coordonnées"}
          {" · "}<StatusBadge value={client.status} />
        </p>
        {client.notes && <p className="mt-2 text-sm text-gray-600">{client.notes}</p>}
      </div>

      <div className="card">
        <h3 className="mb-3 font-semibold">Images ({images.length})</h3>
        {images.length === 0 ? <p className="text-sm text-gray-500">Aucune image.</p> : (
          <ul className="divide-y text-sm">
            {images.map((img) => (
              <li key={img.id} className="flex items-center justify-between py-2">
                <span>{img.original_name}</span>
                <StatusBadge value={img.status} />
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h3 className="mb-3 font-semibold">Conversions ({conversions.length})</h3>
        {conversions.length === 0 ? <p className="text-sm text-gray-500">Aucune conversion.</p> : (
          <ul className="divide-y text-sm">
            {conversions.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2">
                <Link to={`/conversions/${c.id}`} className="text-brand-600 hover:underline">
                  {c.conversion_type === "text" ? "Texte" : "Tableau"} · {c.image_detail.original_name}
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
