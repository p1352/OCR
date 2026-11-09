import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import Icon from "../components/Icon";
import { ErrorBox, ScoreGauge, Spinner, StatusBadge } from "../components/ui";

function CardTitle({ icon, children, right }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h3 className="flex items-center gap-2 font-semibold text-ink-900">
        <span className="text-brand-600"><Icon name={icon} size={18} /></span>
        {children}
      </h3>
      {right}
    </div>
  );
}

function QualityPanel({ qc }) {
  if (!qc) return null;
  return (
    <div className="card">
      <CardTitle icon="alert">Contrôle qualité</CardTitle>
      {qc.confidence_score !== null && (
        <div className="flex items-center gap-4">
          <ScoreGauge score={qc.confidence_score} />
          <div>
            <p className="text-sm font-semibold text-ink-900">
              Indicateur heuristique : {Math.round(qc.confidence_score * 100)} %
            </p>
            <p className="mt-1 text-xs leading-relaxed text-gray-500">
              (signaux automatiques — ne garantit pas l'exactitude ; une
              relecture humaine est requise)
            </p>
          </div>
        </div>
      )}
      {qc.alerts?.length > 0 && (
        <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-amber-700">
          {qc.alerts.map((a, i) => <li key={i}>{a}</li>)}
        </ul>
      )}
      <p className="mt-4 flex items-center gap-2 text-sm text-ink-800">
        Décision : <StatusBadge value={qc.decision} />
      </p>
      {qc.decided_by_name && (
        <p className="mt-1 text-xs text-gray-500">
          par {qc.decided_by_name} le{" "}
          {new Date(qc.decided_at).toLocaleString("fr-FR")}
        </p>
      )}
      {qc.decision_comment && (
        <p className="mt-1 text-sm text-gray-600">« {qc.decision_comment} »</p>
      )}
    </div>
  );
}

function DecisionPanel({ conv, busy, onDecide }) {
  const [comment, setComment] = useState("");
  return (
    <div className="card">
      <CardTitle icon="file">Décision de validation</CardTitle>
      <label className="mb-1 block text-sm text-ink-700" htmlFor="decision-comment">
        Commentaire (optionnel)
      </label>
      <textarea
        id="decision-comment" className="input resize-none" rows={3}
        maxLength={1000} placeholder="Ajouter un commentaire…"
        value={comment} onChange={(e) => setComment(e.target.value)}
      />
      <div className="mt-3 flex items-center gap-3">
        <button
          className="btn-primary flex-1" disabled={busy || conv.status !== "done"}
          onClick={() => onDecide("validated", comment)}
        >
          <Icon name="check" /> Valider le résultat
        </button>
        <button
          className="btn-danger" disabled={busy || conv.status !== "done"}
          onClick={() => onDecide("rejected", comment)}
        >
          <Icon name="x" /> Rejeter
        </button>
      </div>
      <p className="mt-2 text-right text-xs text-gray-400">{comment.length}/1000</p>
    </div>
  );
}

function TextEditor({ conv, onSaved }) {
  const t = conv.extracted_text;
  const [text, setText] = useState(t.corrected_text || t.raw_text);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await api.patch(`/conversions/${conv.id}/text/`, { corrected_text: text });
      setMsg("Corrections enregistrées.");
      onSaved();
    } catch (err) {
      setMsg(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <CardTitle
        icon="file"
        right={
          <div className="flex items-center gap-2 text-xs text-gray-500">
            {t.language && <span>Langue : {t.language}</span>}
            <StatusBadge value={t.validation_status} />
          </div>
        }
      >
        Texte extrait
      </CardTitle>
      <textarea
        className="input min-h-64 font-mono text-sm" value={text}
        onChange={(e) => setText(e.target.value)} aria-label="Texte extrait"
      />
      <div className="mt-3 flex items-center gap-3">
        <button className="btn-primary" onClick={save} disabled={busy}>
          Enregistrer les corrections
        </button>
        {msg && <span className="text-sm text-gray-600">{msg}</span>}
      </div>
      {t.corrected_text && t.corrected_text !== t.raw_text && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-gray-500">
            Voir le texte brut initial
          </summary>
          <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-gray-50 p-3">
            {t.raw_text}
          </pre>
        </details>
      )}
    </div>
  );
}

function TableEditor({ conv, onSaved }) {
  const t = conv.extracted_table;
  const initial = t.corrected_data?.rows ? t.corrected_data : t.raw_data;
  const [headers, setHeaders] = useState([...(initial.headers || [])]);
  const [rows, setRows] = useState(initial.rows?.map((r) => [...r]) || []);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const setCell = (ri, ci, v) =>
    setRows(rows.map((r, i) => (i === ri ? r.map((c, j) => (j === ci ? v : c)) : r)));
  const setHeader = (ci, v) =>
    setHeaders(headers.map((h, i) => (i === ci ? v : h)));
  const addRow = () => setRows([...rows, headers.map(() => "")]);
  const delRow = (ri) => setRows(rows.filter((_, i) => i !== ri));
  const addCol = () => {
    setHeaders([...headers, `Colonne ${headers.length + 1}`]);
    setRows(rows.map((r) => [...r, ""]));
  };
  const delCol = (ci) => {
    setHeaders(headers.filter((_, i) => i !== ci));
    setRows(rows.map((r) => r.filter((_, i) => i !== ci)));
  };

  const save = async () => {
    setBusy(true);
    try {
      await api.patch(`/conversions/${conv.id}/table/`, {
        corrected_data: { headers, rows },
      });
      setMsg("Corrections enregistrées.");
      onSaved();
    } catch (err) {
      setMsg(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const download = async (endpoint, filename) => {
    const { data } = await api.get(`/conversions/${conv.id}/${endpoint}/`, {
      responseType: "blob",
    });
    const url = URL.createObjectURL(data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="card">
      <CardTitle icon="file" right={<StatusBadge value={t.validation_status} />}>
        Tableau extrait
      </CardTitle>
      {headers.length === 0 && rows.length === 0 ? (
        <p className="text-sm text-gray-500">
          Aucun tableau détecté. Vous pouvez en construire un ci-dessous.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-50">
                {headers.map((h, ci) => (
                  <th key={ci} className="border-b border-r border-gray-200 px-3 py-2 text-left">
                    <div className="flex items-center justify-between gap-2">
                      <input
                        className="w-full bg-transparent font-semibold text-ink-800 focus:outline-none"
                        value={h} onChange={(e) => setHeader(ci, e.target.value)}
                        aria-label={`En-tête ${ci + 1}`}
                      />
                      <button className="icon-btn" title="Supprimer la colonne"
                        onClick={() => delCol(ci)} aria-label={`Supprimer la colonne ${ci + 1}`}>
                        <Icon name="x" size={12} />
                      </button>
                    </div>
                  </th>
                ))}
                <th className="w-10 border-b border-gray-200"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  {headers.map((_, ci) => (
                    <td key={ci} className="border-r border-gray-100 px-3 py-1.5">
                      <input
                        className="w-full bg-transparent text-ink-800 focus:outline-none"
                        value={row[ci] ?? ""}
                        onChange={(e) => setCell(ri, ci, e.target.value)}
                        aria-label={`Ligne ${ri + 1} colonne ${ci + 1}`}
                      />
                    </td>
                  ))}
                  <td className="px-2 text-center">
                    <button className="text-xs font-medium text-red-500 hover:text-red-700"
                      onClick={() => delRow(ri)} aria-label={`Supprimer la ligne ${ri + 1}`}>
                      suppr.
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button className="btn-secondary" onClick={addRow}>
          <Icon name="plus" size={14} /> Ligne
        </button>
        <button className="btn-secondary" onClick={addCol}>
          <Icon name="plus" size={14} /> Colonne
        </button>
        <button className="btn-primary" onClick={save} disabled={busy}>
          Enregistrer les corrections
        </button>
        <button className="btn-secondary"
          onClick={() => download("export_xlsx", `conversion_${conv.id}.xlsx`)}>
          <Icon name="download" size={14} /> Exporter Excel
        </button>
        <button className="btn-secondary"
          onClick={() => download("export_csv", `conversion_${conv.id}.csv`)}>
          <Icon name="download" size={14} /> Exporter CSV
        </button>
        {msg && <span className="text-sm text-gray-600">{msg}</span>}
      </div>
    </div>
  );
}

export default function ConversionDetail() {
  const { id } = useParams();
  const [conv, setConv] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [zoom, setZoom] = useState(false);

  const load = () => api.get(`/conversions/${id}/`).then((r) => setConv(r.data));
  useEffect(() => {
    load().catch(() => setError("Conversion introuvable."));
  }, [id]);

  if (error) return <ErrorBox message={error} />;
  if (!conv) return <Spinner />;

  const decide = async (decision, comment) => {
    if (decision === "rejected" && !window.confirm("Rejeter ce résultat ?")) return;
    setBusy(true);
    try {
      await api.post(`/conversions/${conv.id}/decide/`, { decision, comment });
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const retry = async () => {
    setBusy(true);
    try {
      await api.post(`/conversions/${conv.id}/retry/`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold text-ink-900">
            <span className="text-brand-600"><Icon name="file" size={22} /></span>
            Conversion #{conv.id} — {conv.conversion_type === "text" ? "texte" : "tableau"}
            <StatusBadge value={conv.status} />
          </h2>
          <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <Icon name="image" size={14} /> {conv.image_detail.original_name}
            </span>
            {conv.model_used && (
              <span className="flex items-center gap-1">
                <Icon name="chip" size={14} /> modèle : {conv.model_used}
              </span>
            )}
            {conv.duration_ms != null && (
              <span className="flex items-center gap-1">
                <Icon name="clock" size={14} /> {(conv.duration_ms / 1000).toFixed(1)} s
              </span>
            )}
          </p>
        </div>
        {conv.status === "failed" && (
          <button className="btn-secondary" onClick={retry} disabled={busy}>
            Relancer
          </button>
        )}
      </div>

      {conv.status === "failed" && (
        <ErrorBox message={`Échec du traitement : ${conv.error_message}`} />
      )}

      <div className="grid gap-5 lg:grid-cols-5">
        <div className="card lg:col-span-3">
          <CardTitle
            icon="image"
            right={
              <button className="icon-btn" onClick={() => setZoom(true)}
                aria-label="Agrandir l'image">
                <Icon name="expand" size={16} />
              </button>
            }
          >
            Image source
          </CardTitle>
          <img
            src={conv.image_detail.file_url} alt={conv.image_detail.original_name}
            className="max-h-[26rem] w-full cursor-zoom-in rounded-lg border border-gray-200 bg-gray-50 object-contain"
            onClick={() => setZoom(true)}
          />
          <p className="mt-3 text-xs text-gray-500">
            {conv.image_detail.mime_type} · {(conv.image_detail.size_bytes / 1024).toFixed(0)} Ko
            {conv.image_detail.width && ` · ${conv.image_detail.width}×${conv.image_detail.height}`}
            {conv.image_detail.client_name && ` · ${conv.image_detail.client_name}`}
          </p>
        </div>
        <div className="space-y-5 lg:col-span-2">
          <QualityPanel qc={conv.quality_check} />
          <DecisionPanel conv={conv} busy={busy} onDecide={decide} />
        </div>
      </div>

      {conv.extracted_text && <TextEditor conv={conv} onSaved={load} />}
      {conv.extracted_table && <TableEditor conv={conv} onSaved={load} />}

      {zoom && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
          onClick={() => setZoom(false)} role="dialog" aria-modal="true"
        >
          <img src={conv.image_detail.file_url} alt={conv.image_detail.original_name}
            className="max-h-full max-w-full rounded-lg" />
        </div>
      )}
    </div>
  );
}
