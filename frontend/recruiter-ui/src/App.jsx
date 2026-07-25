import { useState, useEffect } from "react";
import { Routes, Route, Navigate, Outlet } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import Dashboard from "./pages/Dashboard";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function AuthGate() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      // Check if token is expired by decoding JWT
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        if (payload.exp * 1000 < Date.now()) {
          localStorage.removeItem("auth_token");
          localStorage.removeItem("user_id");
          localStorage.removeItem("user_email");
        } else {
          setReady(true);
          return;
        }
      } catch {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("user_id");
        localStorage.removeItem("user_email");
      }
    }

    fetch(`${API_BASE}/api/auth/anonymous`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        localStorage.setItem("auth_token", data.token);
        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("user_email", data.email);
        setReady(true);
      })
      .catch(() => {
        // Retry or show error
        setTimeout(() => window.location.reload(), 2000);
      });
  }, []);

  if (!ready) {
    return (
      <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border-2 border-blue-500/20" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 animate-spin" />
        </div>
      </div>
    );
  }

  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route element={<AuthGate />}>
        <Route path="/" element={<UploadPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/dashboard/:reportId" element={<Dashboard />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
