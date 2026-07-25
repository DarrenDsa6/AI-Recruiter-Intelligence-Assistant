import { useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { uploadResumeAndJD, startMatch, ingestGitHub } from "../services/api";
import useBackendStatus from "../hooks/useBackendStatus";

const STEPS = { INPUT: 0, PROCESSING: 1, QUEUED: 2 };

export default function UploadPage() {
  const [step, setStep] = useState(STEPS.INPUT);
  const [resumeFile, setResumeFile] = useState(null);
  const [jdText, setJdText] = useState("");
  const [githubUsername, setGithubUsername] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const navigate = useNavigate();
  const { connected } = useBackendStatus();
  const fileInputRef = useRef(null);

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_email");
    navigate("/auth", { replace: true });
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type === "application/pdf") {
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
      await startMatch(uploadResult.resume_id, jdText);
      setStep(STEPS.QUEUED);
    } catch (err) {
      setError(err.message || "Something went wrong");
      setStep(STEPS.INPUT);
    }
  }, [resumeFile, jdText, githubUsername]);

  const steps = [
    { label: "Upload", done: step > STEPS.INPUT },
    { label: "Analyze", done: step > STEPS.PROCESSING },
    { label: "Done", done: false },
  ];

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
      <div className="w-full max-w-lg space-y-6 animate-fade-in">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 shadow-lg shadow-blue-600/20">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold">AI Resume Tailor</h1>
            <div className="flex items-center justify-center gap-2 text-sm text-gray-500 mt-1">
              <span className="text-gray-600">{localStorage.getItem("user_email")}</span>
              <span className="text-gray-700">·</span>
              <button onClick={handleLogout} className="text-gray-600 hover:text-gray-300 transition">
                Sign out
              </button>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center gap-1.5">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <div className="flex items-center gap-1.5">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium border transition-all ${
                  s.done
                    ? "border-green-500 bg-green-500/10 text-green-400"
                    : i === step || (step === STEPS.PROCESSING && i === 1) || (step === STEPS.QUEUED && i === 2)
                    ? "border-blue-500 bg-blue-500/10 text-blue-400"
                    : "border-white/10 text-gray-600"
                }`}>
                  {s.done ? (
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : i + 1}
                </div>
                <span className={`text-xs font-medium ${
                  i === step || (step === STEPS.PROCESSING && i === 1) || (step === STEPS.QUEUED && i === 2)
                    ? "text-gray-300" : "text-gray-600"
                }`}>{s.label}</span>
              </div>
              {i < steps.length - 1 && <div className="w-6 h-px bg-white/10 mx-1" />}
            </div>
          ))}
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
              <div>
                <label className="text-xs font-medium text-gray-400 mb-2 block">Resume (PDF)</label>
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
                    accept=".pdf"
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
                      <p className="text-sm text-gray-500">Drop your PDF here or <span className="text-blue-400">browse</span></p>
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
                onClick={handleSubmit}
                disabled={!resumeFile || !jdText.trim()}
                className="w-full py-3.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-white/10 disabled:to-white/5 disabled:text-gray-600 transition-all disabled:cursor-not-allowed shadow-lg shadow-blue-600/10"
              >
                Analyze Resume
              </button>
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

          {step === STEPS.QUEUED && (
            <div className="text-center py-10 space-y-5">
              <div className="w-14 h-14 rounded-full bg-green-900/30 border border-green-700/30 flex items-center justify-center mx-auto animate-fade-in">
                <svg className="w-7 h-7 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-green-300">Analysis queued</p>
                <p className="text-xs text-gray-500 mt-1 max-w-xs mx-auto">
                  Your resume is being analyzed. Head to the dashboard to see results.
                </p>
              </div>
              <div className="flex gap-3 justify-center">
                <button
                  onClick={() => navigate("/dashboard")}
                  className="px-5 py-2.5 rounded-xl font-medium text-sm bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 transition-all shadow-lg shadow-blue-600/10"
                >
                  View Dashboard
                </button>
                <button
                  onClick={() => { setStep(STEPS.INPUT); setResumeFile(null); setJdText(""); setGithubUsername(""); setGithubToken(""); }}
                  className="px-5 py-2.5 rounded-xl font-medium text-sm bg-white/5 border border-white/10 hover:bg-white/10 transition-all"
                >
                  New Analysis
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
