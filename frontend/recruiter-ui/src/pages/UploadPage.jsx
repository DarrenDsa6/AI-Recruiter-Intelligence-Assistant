import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [github, setGithub] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleUpload = async () => {
    if (!file) { setError("Please select a resume file"); return; }
    if (!jd.trim()) { setError("Please paste a job description"); return; }
    setError("");
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API}/upload`, { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Upload failed");
      }

      const { session_id } = await res.json();

      localStorage.setItem("session_id", session_id);
      if (github) localStorage.setItem("github_username", github);
      if (githubToken) localStorage.setItem("github_token", githubToken);
      localStorage.setItem("job_description", jd);

      navigate("/dashboard", { state: { sessionId: session_id, github, githubToken, jd } });
    } catch (err) {
      setError(err.message || "Upload failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const isValid = file && jd.trim();

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
      <div className="w-full max-w-lg space-y-6 animate-fade-in">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 mb-4 shadow-lg shadow-blue-600/20">
            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0M12 12.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-1">AI Recruiter</h1>
          <p className="text-sm text-gray-500">
            Upload a resume, paste a job description, and get an instant AI-powered match analysis
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 space-y-5">
          {/* Resume Upload */}
          <div>
            <label className="text-xs font-medium text-gray-400 mb-1.5 block">Resume</label>
            <div
              onClick={() => document.getElementById("fileInput").click()}
              className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition ${
                file ? "border-emerald-500/40 bg-emerald-500/5" : "border-white/10 hover:border-white/30 bg-white/5"
              }`}
            >
              {file ? (
                <div>
                  <svg className="w-6 h-6 text-emerald-400 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm font-medium text-emerald-400">{file.name}</p>
                  <p className="text-[10px] text-gray-600 mt-0.5">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div>
                  <svg className="w-6 h-6 text-gray-600 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                  <p className="text-sm text-gray-500">Click to upload</p>
                  <p className="text-[10px] text-gray-600 mt-0.5">PDF or DOCX</p>
                </div>
              )}
            </div>
            <input id="fileInput" type="file" accept=".pdf,.docx" hidden
              onChange={(e) => { setFile(e.target.files[0]); setError(""); }}
            />
          </div>

          {/* GitHub */}
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1.5 block">
                GitHub <span className="text-gray-600 font-normal">(optional)</span>
              </label>
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12 24 5.37 18.63 0 12 0z"/>
                </svg>
                <input
                  placeholder="UserName"
                  value={github}
                  onChange={(e) => setGithub(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 text-sm transition"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1.5 block">
                GitHub Token <span className="text-gray-600 font-normal">(optional, for higher API rate limits)</span>
              </label>
              <input
                type="password"
                placeholder="github_pat_xxxxxxxxxxxx"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 text-sm transition"
              />
            </div>
          </div>

          {/* Job Description */}
          <div>
            <label className="text-xs font-medium text-gray-400 mb-1.5 block">Job Description</label>
            <textarea
              placeholder="Paste the full job description here..."
              value={jd}
              onChange={(e) => { setJd(e.target.value); setError(""); }}
              rows={5}
              className="w-full p-3 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 text-sm resize-none transition"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-900/30 border border-red-700/30 rounded-xl px-4 py-3">
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleUpload}
            disabled={loading || !isValid}
            className="w-full py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-white/10 disabled:to-white/5 disabled:text-gray-600 transition disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Processing...
              </span>
            ) : (
              "Analyze Candidate"
            )}
          </button>
        </div>

        {/* Footer */}
        <p className="text-[10px] text-gray-700 text-center">
          Powered by AI · Your data is erased when you end the session
        </p>
      </div>
    </div>
  );
}
