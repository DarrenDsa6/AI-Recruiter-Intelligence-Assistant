import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchReports, fetchReport, getMatchStatus, chatWithAI } from "../services/api";

const STATUS_POLL_INTERVAL = 3000;

export default function Dashboard() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const [reports, setReports] = useState([]);
  const [activeReport, setActiveReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState(null);
  const chatEndRef = useRef(null);

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_email");
    navigate("/auth", { replace: true });
  };

  const loadReports = useCallback(async () => {
    try {
      const data = await fetchReports();
      setReports(data.reports || []);
      return data.reports || [];
    } catch {
      return [];
    }
  }, []);

  const loadReport = useCallback(async (id) => {
    try {
      const report = await fetchReport(id);
      setActiveReport(report);
      return report;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setLoading(true);
      const allReports = await loadReports();
      if (cancelled) return;

      if (reportId) {
        await loadReport(reportId);
      } else if (allReports.length > 0) {
        navigate(`/dashboard/${allReports[0].report_id}`, { replace: true });
        return;
      }
      setLoading(false);
    }

    init();
    return () => { cancelled = true; };
  }, [reportId]);

  useEffect(() => {
    if (!activeReport || activeReport.status === "completed" || activeReport.status === "failed") return;

    let cancelled = false;
    const timer = setInterval(async () => {
      if (cancelled) return;
      try {
        const statusData = await getMatchStatus(activeReport.upload_id || activeReport.report_id);
        if (statusData.status === "completed" || statusData.status === "failed") {
          await loadReport(activeReport.report_id);
          clearInterval(timer);
        }
      } catch {
        // keep polling
      }
    }, STATUS_POLL_INTERVAL);

    return () => { cancelled = true; clearInterval(timer); };
  }, [activeReport?.report_id, activeReport?.status]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleChat = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading || !activeReport) return;

    const userMsg = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setChatLoading(true);

    try {
      const data = await chatWithAI({
        message: userMsg,
        report_id: activeReport.report_id,
        selected_skill: selectedSkill,
        history: chatMessages.map((m) => ({ role: m.role, content: m.content })),
      });
      setChatMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const formatDate = (iso) => new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });

  const scoreColor = (score) => {
    if (score >= 80) return "text-green-400";
    if (score >= 60) return "text-yellow-400";
    return "text-orange-400";
  };

  const statusBadge = (status) => {
    const base = "px-2 py-0.5 rounded-full text-xs font-medium";
    if (status === "completed") return `${base} bg-green-900/40 text-green-300 border border-green-700/30`;
    if (status === "failed") return `${base} bg-red-900/40 text-red-300 border border-red-700/30`;
    return `${base} bg-blue-900/40 text-blue-300 border border-blue-700/30`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center">
        <div className="w-10 h-10 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] flex">
      <aside className="w-72 border-r border-white/10 flex flex-col bg-white/[0.02]">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-300">Reports</h2>
          <div className="flex gap-1">
            <button
              onClick={() => navigate("/")}
              className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded-lg hover:bg-white/5 transition"
              title="New analysis"
            >
              + New
            </button>
            <button
              onClick={handleLogout}
              className="text-xs text-gray-600 hover:text-gray-300 px-2 py-1 rounded-lg hover:bg-white/5 transition"
            >
              Logout
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {reports.length === 0 && (
            <p className="text-xs text-gray-600 p-4">No reports yet.</p>
          )}
          {reports.map((r) => (
            <button
              key={r.report_id}
              onClick={() => navigate(`/dashboard/${r.report_id}`)}
              className={`w-full text-left px-4 py-3 border-b border-white/5 hover:bg-white/5 transition ${
                r.report_id === activeReport?.report_id ? "bg-white/[0.07]" : ""
              }`}
            >
              <p className="text-xs text-gray-400 truncate">{r.job_title || "Untitled"}</p>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[10px] text-gray-600">{formatDate(r.created_at)}</span>
                <span className={statusBadge(r.status)}>{r.status}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-8">
        {!activeReport ? (
          <div className="text-center py-20">
            <p className="text-gray-500 text-sm">Select a report or upload a new resume.</p>
            <button
              onClick={() => navigate("/")}
              className="mt-4 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-sm font-medium hover:from-blue-500 hover:to-purple-500 transition"
            >
              Upload Resume
            </button>
          </div>
        ) : activeReport.status === "pending" || activeReport.status === "processing" ? (
          <div className="text-center py-20 space-y-4">
            <div className="w-12 h-12 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto" />
            <p className="text-sm text-gray-400">
              {activeReport.status === "pending" ? "Waiting to be processed..." : "Analyzing resume..."}
            </p>
            <p className="text-xs text-gray-600">This page will update automatically.</p>
          </div>
        ) : activeReport.status === "failed" ? (
          <div className="text-center py-20 space-y-4">
            <div className="w-12 h-12 rounded-full bg-red-900/30 border border-red-700/30 flex items-center justify-center mx-auto">
              <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <p className="text-sm text-red-300">Analysis failed</p>
            <p className="text-xs text-gray-600">{activeReport.error_message || "Unknown error"}</p>
            <button
              onClick={() => navigate("/")}
              className="mt-2 px-4 py-2 rounded-xl bg-white/10 text-sm hover:bg-white/15 transition"
            >
              Try again
            </button>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold">{activeReport.job_title || "Resume Analysis"}</h1>
                <p className="text-xs text-gray-500 mt-1">
                  Analyzed {formatDate(activeReport.created_at)}
                  {activeReport.candidate_name && ` for ${activeReport.candidate_name}`}
                </p>
              </div>
              <div className="text-right">
                <p className={`text-4xl font-bold ${scoreColor(activeReport.ats_score)}`}>
                  {activeReport.ats_score != null ? activeReport.ats_score : "—"}
                  {activeReport.ats_score != null && <span className="text-lg text-gray-500">/100</span>}
                </p>
                <p className="text-xs text-gray-500">ATS Score</p>
              </div>
            </div>

            {activeReport.summary && (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Summary</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{activeReport.summary}</p>
              </div>
            )}

            {activeReport.strengths?.length > 0 && (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-green-400 mb-3">Strengths</h3>
                <ul className="space-y-2">
                  {activeReport.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                      <svg className="w-4 h-4 text-green-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {activeReport.gaps?.length > 0 && (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-orange-400 mb-3">Gaps</h3>
                <ul className="space-y-2">
                  {activeReport.gaps.map((g, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                      <svg className="w-4 h-4 text-orange-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                      </svg>
                      {g}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {activeReport.recommendations?.length > 0 && (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-blue-400 mb-3">Recommendations</h3>
                <ul className="space-y-2">
                  {activeReport.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                      <svg className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                      </svg>
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {activeReport.actionable_rewrites?.length > 0 && (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-purple-400 mb-3">Actionable Rewrites</h3>
                <div className="space-y-3">
                  {activeReport.actionable_rewrites.map((rewrite, i) => (
                    <div key={i} className="bg-white/[0.03] border border-white/5 rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          rewrite.section === "experience"
                            ? "bg-blue-900/30 text-blue-300"
                            : rewrite.section === "skills"
                            ? "bg-purple-900/30 text-purple-300"
                            : rewrite.section === "education"
                            ? "bg-green-900/30 text-green-300"
                            : "bg-gray-800/40 text-gray-400"
                        }`}>
                          {rewrite.section}
                        </span>
                      </div>
                      {rewrite.original && (
                        <p className="text-xs text-gray-500 line-through mb-1">{rewrite.original}</p>
                      )}
                      <p className="text-sm text-gray-300">{rewrite.rewrite}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Career Coach Chat</h3>
              {selectedSkill && (
                <div className="mb-3 flex items-center gap-2">
                  <span className="text-xs text-purple-400 bg-purple-900/30 px-2 py-1 rounded-lg">
                    Focused: {selectedSkill}
                  </span>
                  <button
                    onClick={() => setSelectedSkill(null)}
                    className="text-xs text-gray-500 hover:text-gray-300"
                  >
                    Clear
                  </button>
                </div>
              )}
              <div className="h-64 overflow-y-auto mb-4 space-y-3">
                {chatMessages.length === 0 && (
                  <p className="text-xs text-gray-600 text-center py-8">
                    Ask about gaps, rewrites, interview prep, or anything else.
                  </p>
                )}
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm ${
                      msg.role === "user"
                        ? "bg-blue-600/20 text-blue-200"
                        : "bg-white/5 text-gray-400"
                    }`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white/5 px-3 py-2 rounded-xl text-sm text-gray-500">
                      Thinking...
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
              <form onSubmit={handleChat} className="flex gap-2">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask the career coach..."
                  className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 text-sm transition"
                  disabled={chatLoading}
                />
                <button
                  type="submit"
                  disabled={chatLoading || !chatInput.trim()}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-sm font-medium hover:from-blue-500 hover:to-purple-500 disabled:from-white/10 disabled:to-white/5 transition disabled:cursor-not-allowed"
                >
                  Send
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
