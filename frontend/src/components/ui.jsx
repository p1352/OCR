import Icon from "./Icon";

const STATUS_STYLES = {
  pending: "bg-gray-100 text-gray-600",
  processing: "bg-blue-100 text-blue-700",
  running: "bg-blue-100 text-blue-700",
  done: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  draft: "bg-brand-100 text-brand-700",
  validated: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  active: "bg-green-100 text-green-700",
  archived: "bg-gray-200 text-gray-600",
  none: "bg-gray-100 text-gray-600",
};

const STATUS_LABELS = {
  pending: "En attente", processing: "En cours", running: "En cours",
  done: "Terminée", failed: "Échouée", draft: "Brouillon",
  validated: "Validé", rejected: "Rejeté", active: "Actif",
  archived: "Archivé", none: "Aucune",
};

const STATUS_ICONS = { done: "check", failed: "x", validated: "check", rejected: "x" };

export function StatusBadge({ value }) {
  return (
    <span className={`badge ${STATUS_STYLES[value] || "bg-gray-100 text-gray-600"}`}>
      {STATUS_ICONS[value] && <Icon name={STATUS_ICONS[value]} size={12} />}
      {STATUS_LABELS[value] || value}
    </span>
  );
}

export function Spinner({ label = "Chargement…" }) {
  return <div className="p-8 text-center text-gray-500">{label}</div>;
}

export function ErrorBox({ message }) {
  if (!message) return null;
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
      {message}
    </div>
  );
}

export function Empty({ label = "Aucun élément." }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500">
      {label}
    </div>
  );
}

export function Pagination({ data, onPage }) {
  if (!data || (!data.next && !data.previous)) return null;
  const go = (url) => onPage(new URL(url).search);
  return (
    <div className="mt-4 flex items-center justify-between text-sm">
      <span className="text-gray-500">{data.count} résultat(s)</span>
      <div className="flex gap-2">
        <button className="btn-secondary" disabled={!data.previous} onClick={() => go(data.previous)}>
          Précédent
        </button>
        <button className="btn-secondary" disabled={!data.next} onClick={() => go(data.next)}>
          Suivant
        </button>
      </div>
    </div>
  );
}

/** Jauge circulaire de l'indicateur heuristique (0-1). */
export function ScoreGauge({ score }) {
  const pct = Math.round((score ?? 0) * 100);
  const r = 30;
  const circ = 2 * Math.PI * r;
  const color = pct >= 80 ? "#16a34a" : pct >= 50 ? "#f0b429" : "#dc2626";
  return (
    <div className="relative h-20 w-20">
      <svg viewBox="0 0 72 72" className="h-20 w-20 -rotate-90">
        <circle cx="36" cy="36" r={r} fill="none" stroke="#e5e7eb" strokeWidth="7" />
        <circle
          cx="36" cy="36" r={r} fill="none" stroke={color} strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ - (circ * pct) / 100}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-ink-900">
        {pct} %
      </span>
    </div>
  );
}
