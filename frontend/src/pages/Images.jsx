import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { errorMessage } from "../api";
import { Empty, ErrorBox, Pagination, Spinner, StatusBadge } from "../components/ui";

export default function Images() {
  const [data, setData] = useState(null);
  const [clients, setClients] = useState([]);
  const [file, setFile] = useState(null);
  const [clientId, setClientId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [converting, setConverting] = useState({});
  const fileInput = useRef(null);
  const navigate = useNavigate();

  const load = (params = "") => api.get(`/images/${params}`).then((r) => setData(r.data));

  useEffect(() => {
    load();
    api.get("/clients/?status=active").then((r) => setClients(r.data.results));
  }, []);

  const upload = async (e) => {
    e.preventDefault();
    if (!file) return setError("Sélectionnez un fichier image.");
    setBusy(true);
    setError("");
    const fd = new FormData();
    fd.append("file", file);
    if (clientId) fd.append("client", clientId);
    try {
      await api.post("/images/", fd);
      setFile(null);
      setClientId("");
      fileInput.current.value = "";
      load();
    } catch (err) {
      setError(errorMessage(err, "Échec de l'import."));
    } finally {
      setBusy(false);
    }
  };

  const convert = async (image, type) => {
    setConverting((c) => ({ ...c, [image.id]: type }));
    try {
      const { data: conv } = await api.post(`/images/${image.id}/convert/`, { type });
      navigate(`/conversions/${conv.id}`);
    } catch (err) {
      setError(errorMessage(err, "Échec de la conversion."));
      setConverting((c) => ({ ...c, [image.id]: null }));
    }
  };

  const remove = async (image) => {
    if (!window.confirm(`Supprimer « ${image.original_name} » et ses conversions ?`)) return;
    await api.delete(`/images/${image.id}/`);
    load();
  };

  if (!data) return <Spinner />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Images</h2>

      <form onSubmit={upload} className="card space-y-3">
        <h3 className="font-semibold">Importer une image</h3>
        <ErrorBox message={error} />
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-52">
            <label className="mb-1 block text-sm font-medium" htmlFor="file">Fichier image</label>
            <input id="file" ref={fileInput} type="file" accept="image/*" className="input"
              onChange={(e) => setFile(e.target.files[0] || null)} />
          </div>
          <div className="w-56">
            <label className="mb-1 block text-sm font-medium" htmlFor="client">Client (optionnel)</label>
            <select id="client" className="input" value={clientId}
              onChange={(e) => setClientId(e.target.value)}>
              <option value="">— Aucun —</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <button className="btn-primary" disabled={busy}>
            {busy ? "Import…" : "Importer"}
          </button>
        </div>
        <p className="text-xs text-gray-500">
          Formats acceptés : JPEG, PNG, WebP, TIFF, BMP — 10 Mo max. Le type est vérifié côté serveur.
        </p>
      </form>

      {data.results.length === 0 ? <Empty label="Aucune image importée." /> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.results.map((img) => (
            <div key={img.id} className="card space-y-2">
              <img src={img.file_url} alt={img.original_name}
                className="h-36 w-full rounded-lg border object-contain bg-gray-50" />
              <p className="truncate text-sm font-medium" title={img.original_name}>
                {img.original_name}
              </p>
              <p className="text-xs text-gray-500">
                {img.client_name || "Sans client"} · {(img.size_bytes / 1024).toFixed(0)} Ko
                {img.width ? ` · ${img.width}×${img.height}` : ""} · <StatusBadge value={img.status} />
              </p>
              <div className="flex flex-wrap gap-2">
                <button className="btn-primary !px-3 !py-1 text-xs" disabled={!!converting[img.id]}
                  onClick={() => convert(img, "text")}>
                  {converting[img.id] === "text" ? "…" : "→ Texte"}
                </button>
                <button className="btn-secondary !px-3 !py-1 text-xs" disabled={!!converting[img.id]}
                  onClick={() => convert(img, "table")}>
                  {converting[img.id] === "table" ? "…" : "→ Tableau"}
                </button>
                <button className="btn-danger !px-3 !py-1 text-xs" onClick={() => remove(img)}>
                  Supprimer
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <Pagination data={data} onPage={load} />
    </div>
  );
}
