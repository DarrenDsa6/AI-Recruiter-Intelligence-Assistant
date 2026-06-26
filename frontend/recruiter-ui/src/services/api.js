const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Upload failed");
  }

  return res.json();
}

export async function matchJD(data) {
  const res = await fetch(`${BASE_URL}/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) throw new Error("Match request failed");
  return res.json();
}

export async function endSession(sessionId) {
  await fetch(`${BASE_URL}/session/end/${sessionId}`, {
    method: "DELETE",
  });
}

export function matchStream(sessionId, jobDescription, githubUsername, githubToken) {
  return fetch(`${BASE_URL}/match/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      job_description: jobDescription,
      github_username: githubUsername || null,
      github_token: githubToken || null,
    }),
  });
}

export function chatStream(sessionId, message) {
  return fetch(`${BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}
