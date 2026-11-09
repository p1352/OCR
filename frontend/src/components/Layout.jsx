import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import Icon from "./Icon";

const links = [
  { to: "/", label: "Tableau de bord", icon: "dashboard", end: true },
  { to: "/clients", label: "Clients", icon: "users" },
  { to: "/images", label: "Images", icon: "image" },
  { to: "/conversions", label: "Conversions", icon: "convert" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
      isActive
        ? "bg-brand-500 text-ink-900 shadow-sm"
        : "text-ink-700 hover:bg-gray-100"
    }`;

  const initials = (user?.first_name || user?.username || "?")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="min-h-screen bg-[#f7f8fa] md:flex">
      <aside className="flex flex-col border-b border-gray-200 bg-white p-4 md:sticky md:top-0 md:h-screen md:w-64 md:border-b-0 md:border-r">
        <div className="mb-6 flex items-center gap-2 px-1">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-ink-900">
            <Icon name="file" size={18} />
          </span>
          <h1 className="text-lg font-bold text-ink-900">
            Laurent<span className="text-brand-600">Convert</span>
          </h1>
        </div>

        <nav className="flex flex-1 gap-1 overflow-x-auto md:flex-col">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={linkClass}>
              <Icon name={l.icon} />
              {l.label}
            </NavLink>
          ))}
          {user?.is_admin && (
            <NavLink to="/utilisateurs" className={linkClass}>
              <Icon name="users" />
              Utilisateurs
            </NavLink>
          )}
        </nav>

        <button
          onClick={() => {
            logout();
            navigate("/connexion");
          }}
          className="mt-4 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 hover:bg-gray-100"
        >
          <Icon name="logout" />
          Déconnexion
        </button>
        <div className="mt-6 border-t pt-4 text-xs text-gray-400">
          <p className="font-semibold text-ink-700">LaurentConvert</p>
          <p>Vos documents, vos données, simplement.</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-end gap-4 border-b border-gray-200 bg-white px-6 py-3">
          <button className="icon-btn" aria-label="Notifications">
            <Icon name="bell" size={18} />
          </button>
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
              {initials}
            </span>
            <span className="text-sm font-medium text-ink-800">
              {user?.username}
              {user?.is_admin && <span className="text-gray-400"> · admin</span>}
            </span>
          </div>
        </header>
        <main className="flex-1 p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
