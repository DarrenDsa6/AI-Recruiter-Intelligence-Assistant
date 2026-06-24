import { useEffect, useState, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import ScoreGauge from "../components/ScoreGauge";
import SkillsSection from "../components/SkillsSection";
import GithubSection from "../components/GithubSection";
import ReportSection from "../components/ReportSection";
import QuestionsSection from "../components/QuestionsSection";
import ChatSection from "../components/ChatSection";
import { generateReportPdf } from "../utils/pdfGenerator";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

export default function Dashboard() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const sessionId = state?.sessionId || localStorage.getItem("session_id");
  const github = state?.github || localStorage.getItem("github_username") || "";
  const jd = state?.jd || localStorage.getItem("job_description") || "";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("Loading...");
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) navigate("/", { replace: true });
  }, [sessionId, navigate]);

  useEffect(() => {
    if (!sessionId) return;

    localStorage.removeItem("session_id");
    localStorage.removeItem("github_username");
    localStorage.removeItem("job_description");

    const fetchMatch = async () => {
      try {
        setStatus("Analyzing resume against job description...");

        const res = await fetch(`${API}/match`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            job_description: jd,
            github_username: github || null,
          }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || `Server error: ${res.status}`);
        }

        const result = await res.json();
        setData(result);
        setStatus("Analysis complete");
      } catch (err) {
        console.error(err);
        setError(err.message || "Failed to analyze. Check backend connection.");
        setStatus("Error");
      } finally {
        setLoading(false);
      }
    };

    fetchMatch();
  }, [sessionId, jd, github]);

  const handleEndSession = useCallback(async () => {
    try {
      await fetch(`${API}/session/end/${sessionId}`, { method: "DELETE" });
    } catch {}
    navigate("/", { replace: true });
  }, [sessionId, navigate]);

  const handleDownloadPdf = async () => {
    setPdfLoading(true);
    try {
      await generateReportPdf("report-content", `candidate-report-${sessionId?.slice(0, 8)}.pdf`);
    } catch (err) {
      console.error("PDF generation failed:", err);
    }
    setPdfLoading(false);
  };

  if (!sessionId) return null;

  const match = data?.match || {};
  const finalScore = match.final_score ?? null;

  return (
    <div className="min-h-screen bg-[#0B0F19] text-white">
      {/* HEADER */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0B0F19]/80 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-semibold">AI Recruiter</h1>
            {!loading && (
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                status === "Analysis complete" ? "bg-emerald-900/50 text-emerald-400 border border-emerald-700/50" :
                status === "Error" ? "bg-red-900/50 text-red-400 border border-red-700/50" :
                "bg-blue-900/50 text-blue-400 border border-blue-700/50 animate-pulse"
              }`}>
                {status}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!loading && !error && data && (
              <button
                onClick={handleDownloadPdf}
                disabled={pdfLoading}
                className="text-xs px-3 py-1.5 bg-white/10 hover:bg-white/20 text-gray-300 border border-white/10 rounded-lg transition disabled:opacity-50 flex items-center gap-1.5"
              >
                {pdfLoading ? (
                  <span className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                )}
                {pdfLoading ? "Generating..." : "PDF"}
              </button>
            )}
            <button
              onClick={handleEndSession}
              className="text-xs px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 border border-red-700/30 rounded-lg transition"
            >
              End Session
            </button>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT — wrapped for PDF capture */}
      <main id="report-content" className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* LOADING */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-purple-500/20 border-t-purple-500 rounded-full animate-spin" style={{ animationDirection: "reverse", animationDuration: "0.8s" }} />
              </div>
            </div>
            <p className="text-sm text-gray-500 animate-pulse">{status}</p>
          </div>
        )}

        {/* ERROR */}
        {!loading && error && (
          <div className="bg-red-900/20 border border-red-700/30 rounded-2xl p-8 text-center">
            <svg className="w-12 h-12 text-red-400/50 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            <h2 className="text-lg font-semibold text-red-300 mb-2">Analysis Failed</h2>
            <p className="text-sm text-red-400/70 mb-4">{error}</p>
            <button
              onClick={() => navigate("/", { replace: true })}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl text-sm transition"
            >
              Go Back
            </button>
          </div>
        )}

        {/* RESULTS */}
        {!loading && !error && data && (
          <>
            {/* Score + Metadata */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 stagger-1 animate-fade-in">
              <div className="md:col-span-1">
                <ScoreGauge
                  score={finalScore ?? 0}
                  label="Overall Match"
                  sublabel={match.summary || ""}
                />
              </div>
              <div className="md:col-span-3 grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-4 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold text-emerald-400">{match.skill_score ?? "—"}</span>
                  <span className="text-[10px] text-gray-500 mt-1 uppercase tracking-wider">Skill Score</span>
                </div>
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-4 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold text-blue-400">{match.document_score ?? "—"}</span>
                  <span className="text-[10px] text-gray-500 mt-1 uppercase tracking-wider">Doc Score</span>
                </div>
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-4 flex flex-col items-center justify-center sm:col-span-1 col-span-2">
                  <span className="text-2xl font-bold text-purple-400">
                    {match.required_skills?.length ?? "—"}
                  </span>
                  <span className="text-[10px] text-gray-500 mt-1 uppercase tracking-wider">Skills Required</span>
                </div>
              </div>
            </div>

            {/* Skills */}
            <div className="stagger-2 animate-fade-in">
              <SkillsSection
                required={match.required_skills}
                matched={match.matched_skills}
                missing={[...(match.missing_required || []), ...(match.missing_optional || [])]}
              />
            </div>

            {/* Recommendations */}
            {match.recommendations?.length > 0 && (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 stagger-3 animate-fade-in">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">Recommendations</h3>
                <ul className="space-y-1.5">
                  {match.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                      <span className="text-amber-400 mt-0.5 shrink-0">→</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* GitHub */}
            {data.github && (
              <div className="stagger-4 animate-fade-in">
                <GithubSection data={data.github} />
              </div>
            )}

            {/* Report */}
            {data.report && (
              <div className="stagger-4 animate-fade-in">
                <ReportSection report={data.report} />
              </div>
            )}

            {/* Questions */}
            {data.questions && (
              <div className="stagger-5 animate-fade-in">
                <QuestionsSection questions={data.questions} />
              </div>
            )}

            {/* Chat */}
            <div className="animate-fade-in" style={{ animationDelay: "0.6s" }}>
              <ChatSection sessionId={sessionId} disabled={false} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
