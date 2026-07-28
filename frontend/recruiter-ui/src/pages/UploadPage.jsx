import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { uploadResumeAndJD, startMatch, ingestGitHub, checkAuth, fetchReports, deleteReport } from "../services/api";
import useBackendStatus from "../hooks/useBackendStatus";

const STEPS = { INPUT: 0, PROCESSING: 1 };

export default function UploadPage() {
  const [step, setStep] = useState(STEPS.INPUT);
  const [resumeFile, setResumeFile] = useState(null);
  const [jdText, setJdText] = useState("");
  const [githubUsername, setGithubUsername] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [sendEmail, setSendEmail] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [recentReports, setRecentReports] = useState([]);
  const [deletingId, setDeletingId] = useState(null);
  const navigate = useNavigate();
  const { connected } = useBackendStatus();
  const fileInputRef = useRef(null);

  useEffect(() => {
    checkAuth().then((data) => setUserEmail(data.email)).catch(() => {});
    fetchReports()
      .then((data) => setRecentReports(Array.isArray(data) ? data : data.reports || []))
      .catch(() => {});
  }, []);

  const handleLogout = async () => {
    try {
      await fetch(`${process.env.REACT_APP_API_URL ?? ""}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {}
    navigate("/auth", { replace: true });
  };

  const handleDeleteReport = async (reportId) => {
    if (deletingId) return;
    setDeletingId(reportId);
    try {
      await deleteReport(reportId);
      setRecentReports((prev) => prev.filter((r) => r.id !== reportId));
    } catch {}
    setDeletingId(null);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && (file.type === "application/pdf" || file.name?.toLowerCase().endsWith(".docx"))) {
      setResumeFile(file);
      setError("");
    }
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!resumeFile || !jdText.trim()) return;
    setStep(STEPS.PROCESSING);
    setError("");
    setStatusMsg("Uploading resume...");
    try {
      const uploadResult = await uploadResumeAndJD(resumeFile);
      if (githubUsername.trim()) {
        setStatusMsg("Ingesting GitHub repos...");
        try {
          await ingestGitHub(uploadResult.resume_id, githubUsername.trim(), githubToken.trim() || undefined);
        } catch (ghErr) {
          console.warn("GitHub ingestion failed, continuing without it:", ghErr.message);
        }
      }
      setStatusMsg("Queuing analysis job...");
      await startMatch(uploadResult.resume_id, jdText, sendEmail);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Something went wrong");
      setStep(STEPS.INPUT);
    }
  }, [resumeFile, jdText, githubUsername, githubToken, sendEmail]);

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
      <div className="w-full max-w-lg space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 shadow-lg shadow-blue-600/20">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold">AI Resume Tailor</h1>
              <p className="text-[10px] text-gray-600">{userEmail}</p>
            </div>
          </div>
          <button onClick={handleLogout} className="text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 transition px-3 py-1.5 rounded-lg border border-red-500/30 hover:border-red-500/50">
            Sign out
          </button>
        </div>

        {!connected && (
          <div className="bg-red-900/20 border border-red-800/30 rounded-xl px-4 py-2.5 flex items-center gap-2">
            <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <p className="text-sm text-red-300">Backend is offline. Please try again later.</p>
          </div>
        )}

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
          {step === STEPS.INPUT && (
            <div className="space-y-5">
              {recentReports.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-medium text-gray-400">Recent Reports</h3>
                    <button
                      onClick={() => navigate("/dashboard")}
                      className="text-[10px] text-blue-400 hover:text-blue-300 transition"
                    >
                      View all
                    </button>
                  </div>
                  <div className="space-y-2">
                    {recentReports.slice(0, 3).map((r) => (
                      <div key={r.id} className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.05] transition group">
                        <button
                          onClick={() => navigate(`/dashboard/${r.id}`)}
                          className="flex-1 text-left min-w-0"
                        >
                          <p className="text-xs text-gray-300 truncate font-medium">{r.filename || r.jd_text?.slice(0, 50) || "Untitled"}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                              r.status === "completed" ? "bg-green-900/40 text-green-400" :
                              r.status === "failed" ? "bg-red-900/40 text-red-400" :
                              "bg-blue-900/40 text-blue-400"
                            }`}>{r.status}</span>
                            {r.created_at && (
                              <span className="text-[10px] text-gray-600">{new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
                            )}
                          </div>
                        </button>
                        <button
                          onClick={() => handleDeleteReport(r.id)}
                          disabled={deletingId === r.id}
                          className="opacity-0 group-hover:opacity-100 ml-2 p-1.5 rounded-lg hover:bg-red-500/10 transition text-gray-600 hover:text-red-400 disabled:opacity-30"
                          title="Delete report"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <label className="text-xs font-medium text-gray-400 mb-2 block">Resume (PDF or DOCX)</label>
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative flex flex-col items-center justify-center w-full h-36 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
                    dragOver
                      ? "border-blue-500/60 bg-blue-500/5"
                      : resumeFile
                      ? "border-green-500/30 bg-green-500/5"
                      : "border-white/10 hover:border-white/20 hover:bg-white/[0.02]"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) { setResumeFile(file); setError(""); }
                    }}
                  />
                  {resumeFile ? (
                    <>
                      <svg className="w-8 h-8 text-green-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-sm text-gray-300 font-medium">{resumeFile.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{(resumeFile.size / 1024).toFixed(0)} KB · Click to replace</p>
                    </>
                  ) : (
                    <>
                      <svg className="w-8 h-8 text-gray-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                      </svg>
                      <p className="text-sm text-gray-500">Drop your PDF or DOCX here or <span className="text-blue-400">browse</span></p>
                      <p className="text-xs text-gray-600 mt-0.5">Max 200 pages</p>
                    </>
                  )}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 mb-2 block">Job Description</label>
                <textarea
                  placeholder="Paste the full job description here..."
                  value={jdText}
                  onChange={(e) => { setJdText(e.target.value); setError(""); }}
                  className="w-full h-40 px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 text-sm resize-none transition placeholder:text-gray-600"
                />
                {jdText.length > 0 && (
                  <p className="text-[10px] text-gray-600 mt-1 text-right">{jdText.length.toLocaleString()} characters</p>
                )}
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 mb-2 block">
                  GitHub Username <span className="text-gray-600">(optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. octocat"
                  value={githubUsername}
                  onChange={(e) => { setGithubUsername(e.target.value); setError(""); }}
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 text-sm transition placeholder:text-gray-600"
                />
                <p className="text-[10px] text-gray-600 mt-1">Public repos will be analyzed for skill signals</p>
              </div>

              {githubUsername.trim() && (
                <div>
                  <label className="text-xs font-medium text-gray-400 mb-2 block">
                    GitHub Token <span className="text-gray-600">(optional)</span>
                  </label>
                  <input
                    type="password"
                    placeholder="ghp_xxxxxxxxxxxx"
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 text-sm transition placeholder:text-gray-600"
                  />
                  <p className="text-[10px] text-gray-600 mt-1">For private repos and higher rate limits</p>
                </div>
              )}

              {error && (
                <div className="bg-red-900/20 border border-red-800/30 rounded-xl px-4 py-2.5 flex items-center gap-2">
                  <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                  </svg>
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}

              <button
                type="button"
                onClick={() => setSendEmail(!sendEmail)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${
                  sendEmail
                    ? "border-blue-500/50 bg-blue-500/10"
                    : "border-white/10 bg-white/5 hover:bg-white/[0.07]"
                }`}
              >
                <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all ${
                  sendEmail ? "border-blue-500 bg-blue-600" : "border-white/20"
                }`}>
                  {sendEmail && (
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  )}
                </div>
                <div className="text-left">
                  <p className="text-xs font-medium text-gray-300">Email PDF report when ready</p>
                  <p className="text-[10px] text-gray-600">Get the full analysis as a PDF attachment in your inbox</p>
                </div>
              </button>

              <button
                onClick={handleSubmit}
                disabled={!resumeFile || !jdText.trim()}
                className="w-full py-3.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-white/10 disabled:to-white/5 disabled:text-gray-600 transition-all disabled:cursor-not-allowed shadow-lg shadow-blue-600/10"
              >
                {sendEmail ? "Analyze & Email Report" : "Analyze Resume"}
              </button>

              {recentReports.length > 0 && (
                <button
                  onClick={() => navigate("/dashboard")}
                  className="w-full py-2.5 rounded-xl text-xs font-medium text-gray-400 border border-white/10 hover:bg-white/5 hover:text-gray-300 transition-all"
                >
                  View all reports
                </button>
              )}
            </div>
          )}

          {step === STEPS.PROCESSING && (
            <div className="text-center py-10 space-y-4">
              <div className="relative w-14 h-14 mx-auto">
                <div className="absolute inset-0 rounded-full border-2 border-blue-500/20" />
                <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 animate-spin" />
                <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-purple-400 animate-spin" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-300">{statusMsg}</p>
                <p className="text-xs text-gray-600 mt-1">This usually takes 30-60 seconds</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
