import { useState, useCallback, useRef, useEffect, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { uploadResumeAndJD, startMatch, ingestGitHub, logout, fetchReports, deleteReport } from "../services/api";
import { AuthContext } from "../context/AuthContext";
import useBackendStatus from "../hooks/useBackendStatus";
import Brand from "../components/Brand";
import ConfirmDialog from "../components/ConfirmDialog";

const STEPS = { INPUT: 0, PROCESSING: 1 };
const JD_MAX_LENGTH = 10000;

function StatusChip({ status }) {
  const map = {
    completed: "border-primary-400/30 bg-primary-500/10 text-primary-300",
    failed: "border-danger-500/30 bg-danger-500/10 text-danger-300",
    pending: "border-neutral-600/40 bg-neutral-700/30 text-neutral-300",
    processing: "border-neutral-600/40 bg-neutral-700/30 text-neutral-300",
  };
  return (
    <span className={`chip ${map[status] || map.pending}`}>
      {status === "processing" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary-400" />}
      {status}
    </span>
  );
}

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
  const [recentReports, setRecentReports] = useState([]);
  const [deletingId, setDeletingId] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState(null);
  const navigate = useNavigate();
  const { connected } = useBackendStatus();
  const fileInputRef = useRef(null);
  const authUser = useContext(AuthContext);
  const userEmail = authUser?.email ?? "";

  useEffect(() => {
    fetchReports()
      .then((data) => setRecentReports(Array.isArray(data) ? data : data.reports || []))
      .catch(() => {});
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
    } catch {}
    navigate("/auth", { replace: true });
  };

  const handleDeleteReport = async (reportId) => {
    if (deletingId) return;
    setDeletingId(reportId);
    setConfirmDialog(null);
    try {
      await deleteReport(reportId);
      setRecentReports((prev) => prev.filter((r) => r.id !== reportId));
      setError("");
    } catch (err) {
      setError(err?.message || "Couldn't delete the report. Please try again.");
    }
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

  const runSubmit = useCallback(async () => {
    if (!resumeFile || !jdText.trim()) return;
    if (!connected) {
      setError("Backend is offline. Please try again later.");
      return;
    }
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
      if (err.status === 409) {
        setConfirmDialog({ type: "overLimit" });
      } else {
        setError(err.message || "Something went wrong");
      }
      setStep(STEPS.INPUT);
    }
  }, [resumeFile, jdText, githubUsername, githubToken, sendEmail, connected, navigate]);

  const handleSubmit = useCallback(() => {
    if (recentReports.length >= 3) {
      setConfirmDialog({ type: "overLimit" });
      return;
    }
    runSubmit();
  }, [recentReports.length, runSubmit]);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-neutral-950/80 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between px-4 py-3.5 sm:px-6">
          <button onClick={() => navigate("/")} className="transition-opacity hover:opacity-80" title="AI Recruiter">
            <Brand size={36} />
          </button>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-1.5 rounded-full border border-white/10 px-2.5 py-1 sm:flex">
              <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-success-400" : "bg-danger-400"}`} />
              <span className={`text-[11px] font-medium ${connected ? "text-neutral-300" : "text-neutral-500"}`}>
                {connected ? "Backend online" : "Backend offline"}
              </span>
            </div>
            <span className="hidden max-w-[160px] truncate text-xs text-neutral-400 md:block">{userEmail}</span>
            <button onClick={handleLogout} className="btn-secondary !px-3 !py-1.5 text-xs">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6">
        {!connected && (
          <div className="mb-6 flex items-center gap-3 rounded-2xl border border-danger-500/25 bg-danger-500/10 px-4 py-3">
            <svg className="h-5 w-5 shrink-0 text-danger-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <p className="text-sm text-danger-300">Backend is offline. Please try again later.</p>
          </div>
        )}

        {step === STEPS.INPUT ? (
          <div className="space-y-6 animate-fade-in">
            <div>
              <h1 className="font-display text-2xl font-semibold tracking-tight text-white">New Analysis</h1>
              <p className="mt-1 text-sm text-neutral-400">
                Upload your resume and paste the job description to get started.
              </p>
            </div>

            <div className="card p-5 sm:p-6">
              <div className="space-y-5">
                <div>
                  <label className="label">Resume <span className="normal-case text-neutral-500">(PDF or DOCX)</span></label>
                  <div
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`relative flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed py-10 text-center transition-all duration-200 ${
                      dragOver
                        ? "border-primary-400/70 bg-primary-500/[0.06]"
                        : resumeFile
                        ? "border-primary-400/40 bg-primary-500/[0.04]"
                        : "border-white/15 hover:border-white/30 hover:bg-white/[0.02]"
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
                        <div className="icon-tile h-10 w-10 mb-2.5">
                          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <p className="max-w-full truncate px-6 text-sm font-medium text-neutral-100">{resumeFile.name}</p>
                        <p className="mt-0.5 text-xs text-neutral-500">{(resumeFile.size / 1024).toFixed(0)} KB — click to replace</p>
                      </>
                    ) : (
                      <>
                        <div className="icon-tile h-10 w-10 mb-2.5 border-white/10 bg-white/[0.03] text-neutral-400">
                          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                          </svg>
                        </div>
                        <p className="text-sm text-neutral-400">
                          Drop your resume here or <span className="font-medium text-primary-300">browse files</span>
                        </p>
                        <p className="mt-1 text-xs text-neutral-500">PDF or DOCX · up to 30 pages</p>
                      </>
                    )}
                  </div>
                </div>

                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <label className="label mb-0">Job description</label>
                    {jdText.length > 0 && (
                      <span className={`text-[11px] tabular-nums ${jdText.length >= JD_MAX_LENGTH ? "text-danger-400" : "text-neutral-500"}`}>
                        {jdText.length.toLocaleString()} / {JD_MAX_LENGTH.toLocaleString()} characters
                      </span>
                    )}
                  </div>
                  <textarea
                    placeholder="Paste the full job description here..."
                    value={jdText}
                    onChange={(e) => { setJdText(e.target.value); setError(""); }}
                    maxLength={JD_MAX_LENGTH}
                    className="input h-40 resize-none"
                  />
                </div>

                <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
                  <div className="flex items-center gap-3">
                    <div className="icon-tile">
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-neutral-200">Add GitHub context <span className="font-normal text-neutral-500">(optional)</span></p>
                      <p className="text-xs text-neutral-500">Public repos are analyzed for extra skill signals</p>
                    </div>
                    <span className="hidden text-[11px] text-neutral-600 sm:block">Boost accuracy</span>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_1.4fr]">
                    <input
                      type="text"
                      placeholder="GitHub username (e.g. octocat)"
                      value={githubUsername}
                      onChange={(e) => { setGithubUsername(e.target.value); setError(""); }}
                      className="input"
                    />
                    {githubUsername.trim() && (
                      <input
                        type="password"
                        placeholder="GitHub token for private repos (optional)"
                        value={githubToken}
                        onChange={(e) => setGithubToken(e.target.value)}
                        className="input"
                      />
                    )}
                  </div>
                </div>

                {error && (
                  <div className="flex items-start gap-2.5 rounded-xl border border-danger-500/25 bg-danger-500/10 px-3.5 py-2.5">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-danger-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                    <p className="text-sm text-danger-300">{error}</p>
                  </div>
                )}

                <div className="space-y-3">
                  <button
                    type="button"
                    onClick={() => setSendEmail(!sendEmail)}
                    className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3.5 text-left transition-all duration-200 ${
                      sendEmail
                        ? "border-primary-400/40 bg-primary-500/[0.06]"
                        : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                    }`}
                  >
                    <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-lg border transition-all ${sendEmail ? "border-primary-400 bg-primary-500 text-neutral-950" : "border-white/20"}`}>
                      {sendEmail && (
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-neutral-200">Email PDF report when ready</p>
                      <p className="text-xs text-neutral-500">Get the full analysis as a PDF attachment in your inbox</p>
                    </div>
                  </button>

                  <button
                    onClick={handleSubmit}
                    disabled={!resumeFile || !jdText.trim()}
                    className="btn-primary w-full !py-3 text-[15px]"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                    </svg>
                    {sendEmail ? "Analyze & email report" : "Analyze resume"}
                  </button>
                </div>
              </div>
            </div>

            {recentReports.length > 0 && (
              <div className="animate-fade-in stagger-2">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-neutral-200">Recent reports</h2>
                  <button onClick={() => navigate("/dashboard")} className="btn-ghost">
                    View all
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                    </svg>
                  </button>
                </div>
                <div className="card divide-y divide-white/[0.05] !p-0">
                  {recentReports.slice(0, 3).map((r) => (
                    <div key={r.id} className="group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-white/[0.02]">
                      <button
                        onClick={() => navigate(`/dashboard/${r.id}`)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <p className="truncate text-sm text-neutral-200">{r.filename || r.jd_text?.slice(0, 50) || "Untitled"}</p>
                        <div className="mt-1 flex items-center gap-2">
                          <StatusChip status={r.status} />
                          {r.created_at && (
                            <span className="text-[11px] text-neutral-500">
                              {new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                            </span>
                          )}
                        </div>
                      </button>
                      <button
                        onClick={() => setConfirmDialog({ type: "deleteReport", reportId: r.id })}
                        disabled={deletingId === r.id}
                        className="rounded-lg p-2 text-neutral-500 opacity-0 transition-all hover:bg-danger-500/10 hover:text-danger-400 group-hover:opacity-100 disabled:opacity-30"
                        title="Delete report"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex min-h-[60vh] flex-col items-center justify-center text-center animate-fade-in">
            <div className="relative mb-6 h-16 w-16">
              <div className="absolute inset-0 rounded-full border-2 border-primary-400/15" />
              <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-primary-400" />
              <div className="absolute inset-2.5 animate-spin rounded-full border-2 border-transparent border-t-primary-500/60" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
              <div className="absolute inset-0 flex items-center justify-center">
                <svg className="h-6 w-6 text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                </svg>
              </div>
            </div>
            <p className="text-sm font-medium text-neutral-200">{statusMsg}</p>
            <p className="mt-1.5 text-xs text-neutral-500">This usually takes 30–60 seconds. We'll notify you when it's ready.</p>
          </div>
        )}
      </main>

      <footer className="border-t border-white/[0.04] py-5">
        <p className="text-center text-[11px] text-neutral-600">AI Recruiter · Resume Intelligence Assistant</p>
      </footer>

      <ConfirmDialog
        open={!!confirmDialog}
        title={confirmDialog?.type === "overLimit" ? "Report limit reached" : "Delete this report?"}
        message={
          confirmDialog?.type === "overLimit"
            ? `You already have ${recentReports.length} reports (max 3). Delete one of your reports below to free up space.`
            : "This report and its analysis will be permanently removed. You cannot undo this action."
        }
        confirmLabel={confirmDialog?.type === "overLimit" ? "Got it" : "Delete"}
        danger={confirmDialog?.type !== "overLimit"}
        onConfirm={() => {
          if (confirmDialog?.type === "deleteReport") {
            handleDeleteReport(confirmDialog.reportId);
          } else {
            setConfirmDialog(null);
          }
        }}
        onCancel={() => setConfirmDialog(null)}
      />
    </div>
  );
}
