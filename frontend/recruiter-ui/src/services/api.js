const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getAuthHeaders() {
  const token = localStorage.getItem("auth_token");
  if (!token) throw new Error("Not authenticated");
  return { Authorization: `Bearer ${token}` };
}

async function request(path, { method = "GET", body, headers = {} } = {}) {
  const url = `${API_BASE}${path}`;
  const opts = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function uploadResumeAndJD(resumeFile) {
  const token = localStorage.getItem("auth_token");
  if (!token) throw new Error("Not authenticated");
  const formData = new FormData();
  formData.append("file", resumeFile);
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function startMatch(resumeId, jdText) {
  return request("/api/match", {
    method: "POST",
    headers: getAuthHeaders(),
    body: { resume_id: resumeId, jd_text: jdText },
  });
}

export async function getReportStatus(reportId) {
  return request(`/api/reports/${reportId}/status`, {
    headers: getAuthHeaders(),
  });
}

export async function fetchReports() {
  return request("/api/reports", {
    headers: getAuthHeaders(),
  });
}

export async function fetchReport(reportId) {
  return request(`/api/reports/${reportId}`, {
    headers: getAuthHeaders(),
  });
}

export async function chatWithAI(payload) {
  return request("/api/chat/stream", {
    method: "POST",
    headers: getAuthHeaders(),
    body: payload,
  });
}

export async function ingestGitHub(resumeId, username, token) {
  const params = new URLSearchParams();
  if (token) params.append("token", token);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return request(`/api/github/${resumeId}/${encodeURIComponent(username)}${qs}`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
}

export async function healthCheck() {
  return request("/api/health");
}
