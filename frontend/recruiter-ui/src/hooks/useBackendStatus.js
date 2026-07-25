import { useState, useEffect } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function useBackendStatus() {
  const [status, setStatus] = useState({ connected: false, loading: true });

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const res = await fetch(`${API_URL}/api/health`);
        if (!cancelled) {
          setStatus({ connected: res.ok, loading: false });
        }
      } catch {
        if (!cancelled) {
          setStatus({ connected: false, loading: false });
        }
      }
    }

    check();
    const interval = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return status;
}
