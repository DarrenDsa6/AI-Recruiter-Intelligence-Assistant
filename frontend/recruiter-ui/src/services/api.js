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

export async function requestOTP(email) {
  return request("/api/auth/request-otp", {
    method: "POST",
    body: { email },
  });
}

export async function verifyOTP(email, code) {
  return request("/api/auth/verify-otp", {
    method: "POST",
    body: { email, code },
  });
}

export async function uploadResumeAndJD(resumeFile, jdText) {
  const token = localStorage.getItem("auth_token");
  if (!token) throw new Error("Not authenticated");
  const formData = new FormData();
  formData.append("resume_file", resumeFile);
  formData.append("jd_text", jdText);
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

export async function startMatch(uploadId) {
  return request(`/api/match/${uploadId}/start`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
}

export async function getMatchStatus(uploadId) {
  return request(`/api/match/${uploadId}/status`, {
    headers: getAuthHeaders(),
  });
}

export async function fetchReports({ limit = 50, offset = 0 } = {}) {
  return request(`/api/reports?limit=${limit}&offset=${offset}`, {
    headers: getAuthHeaders(),
  });
}

export async function fetchReport(reportId) {
  return request(`/api/reports/${reportId}`, {
    headers: getAuthHeaders(),
  });
}

export async function chatWithAI(payload) {
  return request("/api/chat", {
    method: "POST",
    headers: getAuthHeaders(),
    body: payload,
  });
}

export async function healthCheck() {
  return request("/health");
}
