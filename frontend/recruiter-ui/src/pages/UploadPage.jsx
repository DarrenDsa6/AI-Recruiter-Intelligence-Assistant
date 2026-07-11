import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { uploadResumeAndJD, startMatch } from "../services/api";
import useBackendStatus from "../hooks/useBackendStatus";

const STEPS = { INPUT: 0, PROCESSING: 1, QUEUED: 2 };

export default function UploadPage() {
  const [step, setStep] = useState(STEPS.INPUT);
  const [resumeFile, setResumeFile] = useState(null);
  const [jdText, setJdText] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { connected } = useBackendStatus();

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_email");
    navigate("/auth", { replace: true });
  };

  const handleSubmit = useCallback(async () => {
    if (!resumeFile || !jdText.trim()) return;
    setStep(STEPS.PROCESSING);
    setError("");
    setStatusMsg("Uploading resume...");
    try {
      const uploadResult = await uploadResumeAndJD(resumeFile, jdText);
      setStatusMsg("Queuing analysis job...");
      await startMatch(uploadResult.upload_id);
      setStep(STEPS.QUEUED);
      setTimeout(() => navigate("/dashboard"), 1500);
    } catch (err) {
      setError(err.message || "Something went wrong");
      setStep(STEPS.INPUT);
    }
  }, [resumeFile, jdText, navigate]);

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
      <div className="w-full max-w-lg space-y-6 animate-fade-in">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 mb-4 shadow-lg shadow-blue-600/20">
            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-1">AI Resume Tailor</h1>
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <span>{localStorage.getItem("user_email") || "Signed in"}</span>
            <button onClick={handleLogout} className="text-gray-600 hover:text-gray-300 underline transition">
              Logout
            </button>
          </div>
        </div>

        {!connected && (
          <div className="bg-red-900/30 border border-red-700/30 rounded-xl px-4 py-3 text-center">
            <p className="text-sm text-red-300">Backend is offline. Please try again later.</p>
          </div>
        )}

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
          {step === STEPS.INPUT && (
            <div className="space-y-5">
              <div>
                <label className="text-xs font-medium text-gray-400 mb-1.5 block">Resume (PDF)</label>
                <label className="flex items-center justify-center w-full h-32 border-2 border-dashed rounded-xl cursor-pointer transition hover:border-blue-500/40">
                  <input
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => {
                      setResumeFile(e.target.files?.[0] || null);
                      setError("");
                    }}
                  />
                  {resumeFile ? (
                    <div className="text-center">
                      <svg className="w-8 h-8 mx-auto text-green-400 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-sm text-gray-300">{resumeFile.name}</p>
                      <p className="text-xs text-gray-500">{(resumeFile.size / 1024).toFixed(0)} KB</p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <svg className="w-8 h-8 mx-auto text-gray-600 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                      </svg>
                      <p className="text-sm text-gray-500">Click to upload PDF</p>
                      <p className="text-xs text-gray-600">Max 200 pages</p>
                    </div>
                  )}
                </label>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-400 mb-1.5 block">Job Description</label>
                <textarea
                  placeholder="Paste the full job description here..."
                  value={jdText}
                  onChange={(e) => { setJdText(e.target.value); setError(""); }}
                  className="w-full h-40 px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 text-sm resize-none transition"
                />
              </div>

              {error && (
                <div className="bg-red-900/30 border border-red-700/30 rounded-xl px-4 py-3">
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}

              <button
                onClick={handleSubmit}
                disabled={!resumeFile || !jdText.trim()}
                className="w-full py-3.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-white/10 disabled:to-white/5 disabled:text-gray-600 transition disabled:cursor-not-allowed shadow-lg shadow-blue-600/10"
              >
                Analyze Resume
              </button>
            </div>
          )}

          {step === STEPS.PROCESSING && (
            <div className="text-center py-8 space-y-4">
              <div className="w-12 h-12 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto" />
              <p className="text-sm text-gray-400">{statusMsg}</p>
            </div>
          )}

          {step === STEPS.QUEUED && (
            <div className="text-center py-8 space-y-4">
              <div className="w-12 h-12 rounded-full bg-green-900/30 border border-green-700/30 flex items-center justify-center mx-auto">
                <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-green-300">Job queued successfully</p>
                <p className="text-xs text-gray-500 mt-1">Redirecting to dashboard...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
