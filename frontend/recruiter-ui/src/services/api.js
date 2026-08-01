const API_BASE = process.env.REACT_APP_API_URL ?? "";

async function request(path, { method = "GET", body, headers = {} } = {}) {
  const url = `${API_BASE}${path}`;
  const opts = {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  if (!res.ok) {
    const err = await httpError(res);
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

async function httpError(res) {
  let message = `HTTP ${res.status}`;
  try {
    const data = await res.json();
    if (data && typeof data.detail === "string") message = data.detail;
    else if (data && typeof data.message === "string") message = data.message;
  } catch {}
  const err = new Error(message);
  err.status = res.status;
  return err;
}

export async function uploadResumeAndJD(resumeFile) {
  const formData = new FormData();
  formData.append("file", resumeFile);
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    throw await httpError(res);
  }
  return res.json();
}

export async function startMatch(resumeId, jdText, sendEmail = false) {
  return request("/api/match", {
    method: "POST",
    body: { resume_id: resumeId, jd_text: jdText, send_email: sendEmail },
  });
}

export async function getReportStatus(reportId) {
  return request(`/api/reports/${reportId}/status`);
}

export async function fetchReports() {
  return request("/api/reports");
}

export async function fetchReport(reportId) {
  return request(`/api/reports/${reportId}`);
}

export async function fetchChatHistory(reportId) {
  return request(`/api/chat/history/${reportId}`);
}

export async function deleteReport(reportId) {
  return request(`/api/reports/${reportId}`, { method: "DELETE" });
}

export async function retryReport(reportId) {
  return request(`/api/reports/${reportId}/retry`, { method: "POST" });
}

export async function sendReportEmail(reportId) {
  return request(`/api/reports/${reportId}/send-email`, { method: "POST" });
}

export async function chatWithAI(payload) {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw await httpError(res);
  }
  return res;
}

export async function ingestGitHub(resumeId, username, token) {
  const headers = {};
  if (token) headers["X-GitHub-Token"] = token;
  const res = await fetch(`${API_BASE}/api/github/${resumeId}/${encodeURIComponent(username)}`, {
    method: "POST",
    credentials: "include",
    headers,
  });
  if (!res.ok) {
    throw await httpError(res);
  }
  return res.json();
}

export async function healthCheck() {
  return request("/api/health");
}

export async function requestOTP(email) {
  return request("/api/auth/request-otp", {
    method: "POST",
    body: { email },
  });
}

export async function verifyOTP(email, otp) {
  return request("/api/auth/verify-otp", {
    method: "POST",
    body: { email, otp },
  });
}

export async function checkAuth() {
  return request("/api/auth/me");
}

export async function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export function streamReportStatus(reportId, onStatus, onError) {
  const url = `${API_BASE}/api/reports/${reportId}/stream`;
  const eventSource = new EventSource(url, { withCredentials: true });
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onStatus(data.status);
      if (data.status === "completed" || data.status === "failed" || data.status === "timeout") {
        eventSource.close();
      }
    } catch {}
  };
  eventSource.onerror = (err) => {
    eventSource.close();
    if (onError) onError(err);
  };
  return eventSource;
}
