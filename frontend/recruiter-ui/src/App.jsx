import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import Dashboard from "./pages/Dashboard";
import AuthPage from "./pages/AuthPage";

function AuthGuard() {
  const token = localStorage.getItem("auth_token");
  if (!token) return <Navigate to="/auth" replace />;
  return <Outlet />;
}

function GuestGuard() {
  const token = localStorage.getItem("auth_token");
  if (token) return <Navigate to="/" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<GuestGuard />}>
          <Route path="/auth" element={<AuthPage />} />
        </Route>
        <Route element={<AuthGuard />}>
          <Route path="/" element={<UploadPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/:reportId" element={<Dashboard />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
