import { useEffect, useState } from "react";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

export default function useBackendStatus() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API}/health`);
        if (res.ok) {
          setStatus("connected");
        } else {
          setStatus("disconnected");
        }
      } catch {
        setStatus("disconnected");
      }
    };

    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  return status;
}
