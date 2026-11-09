import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import ClientDetail from "./pages/ClientDetail";
import Clients from "./pages/Clients";
import ConversionDetail from "./pages/ConversionDetail";
import Conversions from "./pages/Conversions";
import Dashboard from "./pages/Dashboard";
import Images from "./pages/Images";
import Login from "./pages/Login";
import Users from "./pages/Users";

function Protected({ children, adminOnly = false }) {
  const { user, loading } = useAuth();
  if (loading)
    return <div className="p-8 text-center text-gray-500">Chargement…</div>;
  if (!user) return <Navigate to="/connexion" replace />;
  if (adminOnly && !user.is_admin) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="clients" element={<Clients />} />
        <Route path="clients/:id" element={<ClientDetail />} />
        <Route path="images" element={<Images />} />
        <Route path="conversions" element={<Conversions />} />
        <Route path="conversions/:id" element={<ConversionDetail />} />
        <Route
          path="utilisateurs"
          element={
            <Protected adminOnly>
              <Users />
            </Protected>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
