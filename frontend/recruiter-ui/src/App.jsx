import { useState, useEffect, lazy, Suspense } from "react";
import { Routes, Route, Navigate, Outlet } from "react-router-dom";
import { checkAuth } from "./services/api";
import { AuthContext } from "./context/AuthContext";

const AuthPage = lazy(() => import("./pages/AuthPage"));
const UploadPage = lazy(() => import("./pages/UploadPage"));
const Dashboard = lazy(() => import("./pages/Dashboard"));

function LoadingFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="relative h-14 w-14">
        <div className="absolute inset-0 rounded-full border-2 border-primary-400/15" />
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-primary-400" />
        <div className="absolute inset-2 animate-spin rounded-full border-2 border-transparent border-t-primary-500/60" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
      </div>
    </div>
  );
}

function AuthGate() {
  const [ready, setReady] = useState(false);
  const [redirect, setRedirect] = useState(false);
  const [authError, setAuthError] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    checkAuth()
      .then((data) => { setUser(data); setReady(true); })
      .catch((err) => {
        if (err?.status === 401) {
          setRedirect(true);
        } else {
          setAuthError(true);
          setReady(true);
        }
      });
  }, []);

  if (redirect) return <Navigate to="/auth" replace />;
  if (!ready) return <LoadingFallback />;

  if (authError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-sm text-neutral-300">Couldn't reach the server. Check your connection and try again.</p>
        <button onClick={() => window.location.reload()} className="btn-secondary !px-6 !py-2.5 text-sm">Retry</button>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={user}>
      <Suspense fallback={<LoadingFallback />}>
        <Outlet />
      </Suspense>
    </AuthContext.Provider>
  );
}

export default function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route element={<AuthGate />}>
          <Route path="/" element={<UploadPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/:reportId" element={<Dashboard />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
