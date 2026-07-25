import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchReports, fetchReport, streamReportStatus, checkAuth } from "../services/api";
import GithubSection from "../components/GithubSection";

function ReportSection({ title, color, icon, children, delay }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden animate-slide-up" style={{ animationDelay: `${delay}ms` }}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-white/[0.02] transition">
        <div className="flex items-center gap-2.5">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${color}`}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-gray-200">{title}</h3>
        </div>
        <svg className={`w-4 h-4 text-gray-500 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
}

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
  const [userEmail, setUserEmail] = useState("");
  const chatEndRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    checkAuth().then((data) => setUserEmail(data.email)).catch(() => {});
  }, []);

  const handleLogout = async () => {
    try {
      await fetch(`${process.env.REACT_APP_API_URL || "http://localhost:8000"}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {}
    navigate("/auth", { replace: true });
  };

  const loadReports = useCallback(async () => {
    try {
      const data = await fetchReports();
      const list = Array.isArray(data) ? data : data.reports || [];
      setReports(list);
      return list;
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
        navigate(`/dashboard/${allReports[0].id}`, { replace: true });
        return;
      }
      setLoading(false);
    }

    init();
    return () => { cancelled = true; };
  }, [reportId]);

  useEffect(() => {
    if (!activeReport || activeReport.status === "completed" || activeReport.status === "failed") return;

    const eventSource = streamReportStatus(
      activeReport.id,
      async (status) => {
        if (status === "completed" || status === "failed") {
          await loadReport(activeReport.id);
        }
      },
      () => {},
    );

    return () => eventSource.close();
  }, [activeReport?.id, activeReport?.status]);

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

    const API = (process.env.REACT_APP_API_URL || "http://localhost:8000") + "/api";

    const abortController = new AbortController();
    abortRef.current = abortController;

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_id: activeReport.resume_id,
          report_id: activeReport.id,
          message: userMsg,
        }),
        signal: abortController.signal,
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;
          const json = trimmed.slice(5).trim();
          if (!json) continue;

          try {
            const parsed = JSON.parse(json);
            if (parsed.type === "text") {
              fullText = parsed.content;
              setChatMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant" && last.streaming) {
                  updated[updated.length - 1] = { ...last, content: fullText };
                } else {
                  updated.push({ role: "assistant", content: fullText, streaming: true });
                }
                return updated;
              });
            }
            if (parsed.type === "error") {
              fullText = parsed.message;
              setChatMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant" && last.streaming) {
                  updated[updated.length - 1] = { ...last, content: `**Error:** ${fullText}` };
                } else {
                  updated.push({ role: "assistant", content: `**Error:** ${fullText}`, streaming: true });
                }
                return updated;
              });
            }
            if (parsed.type === "final") {
              setChatMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant" && last.streaming) {
                  updated[updated.length - 1] = { ...last, streaming: false };
                }
                return updated;
              });
            }
          } catch {}
        }
      }

      setChatMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant" && last.streaming) {
          updated[updated.length - 1] = { ...last, streaming: false };
        }
        return updated;
      });
    } catch (err) {
      if (err.name === "AbortError") return;
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: `**Error:** ${err.message || "Failed to get response."}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  useEffect(() => {
    return () => { if (abortRef.current) abortRef.current.abort(); };
  }, []);

  const formatDate = (iso) => new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });

  const scoreRing = (score) => {
    const pct = Math.min(score || 0, 100);
    const r = 38;
    const circ = 2 * Math.PI * r;
    const offset = circ - (pct / 100) * circ;
    return { r, circ, offset, pct };
  };

  const statusBadge = (status) => {
    const base = "px-2 py-0.5 rounded-full text-[10px] font-medium";
    if (status === "completed") return `${base} bg-green-900/40 text-green-300 border border-green-700/30`;
    if (status === "failed") return `${base} bg-red-900/40 text-red-300 border border-red-700/30`;
    return `${base} bg-blue-900/40 text-blue-300 border border-blue-700/30`;
  };

  const analysis = activeReport?.report || {};
  const ats_score = analysis.ats_score;
  const summary = analysis.summary;
  const strengths = analysis.strengths || [];
  const gaps = analysis.improvement_areas || analysis.gaps || [];
  const recommendations = analysis.keyword_suggestions || analysis.recommendations || [];
  const actionableRewrites = activeReport?.rewrites || [];

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border-2 border-blue-500/20" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] flex">
      <aside className="w-72 border-r border-white/10 flex flex-col bg-white/[0.02]">
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-sm font-bold text-white">
                {(userEmail || "?")[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-300 truncate">{userEmail}</p>
                <p className="text-[10px] text-gray-600">{reports.length} report{reports.length !== 1 ? "s" : ""}</p>
              </div>
            </div>
            <button onClick={handleLogout} className="text-[10px] text-red-400 hover:text-red-300 hover:bg-red-500/10 transition px-2 py-1 rounded border border-red-500/30 hover:border-red-500/50">
              Sign out
            </button>
          </div>
          <button
            onClick={() => navigate("/")}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-xs font-semibold hover:from-blue-500 hover:to-purple-500 transition-all shadow-lg shadow-blue-600/10"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Analysis
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {reports.length === 0 && (
            <div className="p-4 text-center">
              <p className="text-xs text-gray-600">No reports yet.</p>
              <p className="text-[10px] text-gray-700 mt-1">Upload a resume to get started.</p>
            </div>
          )}
          {reports.map((r) => (
            <button
              key={r.id}
              onClick={() => navigate(`/dashboard/${r.id}`)}
              className={`w-full text-left px-4 py-3 border-b border-white/5 transition-all hover:bg-white/5 ${
                r.id === activeReport?.id ? "bg-white/[0.07] border-l-2 border-l-blue-500" : "border-l-2 border-l-transparent"
              }`}
            >
              <p className="text-xs text-gray-300 truncate font-medium">{r.filename || "Untitled Position"}</p>
              <div className="flex items-center justify-between mt-1.5">
                <span className="text-[10px] text-gray-600">{formatDate(r.created_at)}</span>
                <span className={statusBadge(r.status)}>{r.status}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        {!activeReport ? (
          <div className="flex flex-col items-center justify-center h-full py-20 animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 mb-1">No report selected</p>
            <p className="text-xs text-gray-600 mb-4">Upload a resume to see your analysis here.</p>
            <button
              onClick={() => navigate("/")}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-sm font-semibold hover:from-blue-500 hover:to-purple-500 transition-all shadow-lg shadow-blue-600/10"
            >
              Upload Resume
            </button>
          </div>
        ) : activeReport.status === "pending" || activeReport.status === "processing" ? (
          <div className="flex flex-col items-center justify-center h-full py-20 animate-fade-in">
            <div className="relative w-14 h-14 mb-4">
              <div className="absolute inset-0 rounded-full border-2 border-blue-500/20" />
              <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 animate-spin" />
              <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-purple-400 animate-spin" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
            </div>
            <p className="text-sm font-medium text-gray-300">
              {activeReport.status === "pending" ? "Waiting in queue..." : "Analyzing your resume..."}
            </p>
            <p className="text-xs text-gray-600 mt-1">This usually takes 30-60 seconds</p>
            <div className="flex items-center gap-3 mt-6 text-[10px] text-gray-600">
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${activeReport.status === "pending" ? "bg-blue-400 animate-pulse" : "bg-green-400"}`} />
                Queued
              </div>
              <div className="w-4 h-px bg-white/10" />
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${activeReport.status === "processing" ? "bg-blue-400 animate-pulse" : "bg-white/10"}`} />
                Processing
              </div>
              <div className="w-4 h-px bg-white/10" />
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-white/10" />
                Complete
              </div>
            </div>
          </div>
        ) : activeReport.status === "failed" ? (
          <div className="flex flex-col items-center justify-center h-full py-20 animate-fade-in">
            <div className="w-14 h-14 rounded-full bg-red-900/30 border border-red-700/30 flex items-center justify-center mb-4">
              <svg className="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-red-300">Analysis failed</p>
            <p className="text-xs text-gray-600 mt-1 max-w-xs text-center">{activeReport.error_message || "Something went wrong. Please try again."}</p>
            <button
              onClick={() => navigate("/")}
              className="mt-4 px-5 py-2.5 rounded-xl bg-white/5 border border-white/10 text-sm font-medium hover:bg-white/10 transition-all"
            >
              Try again
            </button>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto p-8 space-y-6">
            <div className="flex items-start justify-between animate-fade-in">
              <div>
                <h1 className="text-xl font-bold">{activeReport.filename || activeReport.jd_text?.slice(0, 60) || "Resume Analysis"}</h1>
                <p className="text-xs text-gray-500 mt-1">
                  Analyzed {formatDate(activeReport.created_at)}
                </p>
              </div>
              {ats_score != null && (
                <div className="relative flex items-center justify-center">
                  <svg width="88" height="88" className="-rotate-90">
                    <circle cx="44" cy="44" r={scoreRing(ats_score).r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
                    <circle
                      cx="44" cy="44" r={scoreRing(ats_score).r}
                      fill="none"
                      stroke="url(#scoreGradient)"
                      strokeWidth="6"
                      strokeDasharray={scoreRing(ats_score).circ}
                      strokeDashoffset={scoreRing(ats_score).offset}
                      strokeLinecap="round"
                      className="transition-all duration-1000"
                    />
                    <defs>
                      <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor={ats_score >= 80 ? "#22c55e" : ats_score >= 60 ? "#eab308" : "#f97316"} />
                        <stop offset="100%" stopColor={ats_score >= 80 ? "#10b981" : ats_score >= 60 ? "#f59e0b" : "#ef4444"} />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute text-center">
                    <p className={`text-2xl font-bold ${ats_score >= 80 ? "text-green-400" : ats_score >= 60 ? "text-yellow-400" : "text-orange-400"}`}>
                      {ats_score}
                    </p>
                    <p className="text-[10px] text-gray-500">ATS Score</p>
                  </div>
                </div>
              )}
            </div>

            {summary && (
              <ReportSection title="Summary" color="bg-blue-900/30 text-blue-400" icon="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" delay={0}>
                <p className="text-sm text-gray-400 leading-relaxed">{summary}</p>
              </ReportSection>
            )}

            {strengths.length > 0 && (
              <ReportSection title="Strengths" color="bg-green-900/30 text-green-400" icon="M4.5 12.75l6 6 9-13.5" delay={80}>
                <ul className="space-y-2.5">
                  {strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-gray-400">
                      <div className="w-5 h-5 rounded-md bg-green-900/30 flex items-center justify-center shrink-0 mt-0.5">
                        <svg className="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      </div>
                      {typeof s === "string" ? s : s.text || s.description || JSON.stringify(s)}
                    </li>
                  ))}
                </ul>
              </ReportSection>
            )}

            {gaps.length > 0 && (
              <ReportSection title="Skill Gaps" color="bg-orange-900/30 text-orange-400" icon="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" delay={160}>
                <ul className="space-y-2.5">
                  {gaps.map((g, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-gray-400">
                      <div className="w-5 h-5 rounded-md bg-orange-900/30 flex items-center justify-center shrink-0 mt-0.5">
                        <svg className="w-3 h-3 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                        </svg>
                      </div>
                      {typeof g === "string" ? g : g.text || g.description || JSON.stringify(g)}
                    </li>
                  ))}
                </ul>
              </ReportSection>
            )}

            {recommendations.length > 0 && (
              <ReportSection title="Keyword Suggestions" color="bg-purple-900/30 text-purple-400" icon="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" delay={240}>
                <div className="space-y-3">
                  {recommendations.map((r, i) => (
                    <div key={i} className="bg-white/[0.03] border border-white/5 rounded-xl p-4 space-y-2">
                      {r.original && (
                        <p className="text-xs text-gray-500 line-through leading-relaxed">{r.original}</p>
                      )}
                      <p className="text-sm text-gray-300 leading-relaxed">{r.suggested_rewrite || r.suggestion || JSON.stringify(r)}</p>
                    </div>
                  ))}
                </div>
              </ReportSection>
            )}

            {actionableRewrites.length > 0 && (
              <ReportSection title="Actionable Rewrites" color="bg-cyan-900/30 text-cyan-400" icon="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" delay={320}>
                <div className="space-y-3">
                  {actionableRewrites.map((rewrite, i) => (
                    <div key={i} className="bg-white/[0.03] border border-white/5 rounded-xl p-4 space-y-2">
                      {rewrite.section && (
                        <span className="inline-block px-2 py-0.5 rounded-md text-[10px] font-medium bg-white/5 text-gray-400 border border-white/5">
                          {rewrite.section}
                        </span>
                      )}
                      {rewrite.original && (
                        <p className="text-xs text-gray-500 line-through leading-relaxed">{rewrite.original}</p>
                      )}
                      <p className="text-sm text-gray-300 leading-relaxed">{rewrite.rewrite}</p>
                    </div>
                  ))}
                </div>
              </ReportSection>
            )}

            {activeReport.github_analysis && (
              <GithubSection data={activeReport.github_analysis} />
            )}

            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl animate-slide-up" style={{ animationDelay: "400ms" }}>
              <div className="px-5 py-4 border-b border-white/5 flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-blue-900/30 flex items-center justify-center">
                  <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
                  </svg>
                </div>
                <h3 className="text-sm font-semibold text-gray-200">Career Coach Chat</h3>
              </div>
              <div className="p-5">
                {selectedSkill && (
                  <div className="mb-3 flex items-center gap-2">
                    <span className="text-xs text-cyan-400 bg-cyan-900/30 px-2.5 py-1 rounded-lg border border-cyan-700/20">
                      Focused: {selectedSkill}
                    </span>
                    <button onClick={() => setSelectedSkill(null)} className="text-xs text-gray-500 hover:text-gray-300 transition">
                      Clear
                    </button>
                  </div>
                )}
                <div className="h-64 overflow-y-auto mb-4 space-y-3">
                  {chatMessages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center py-8">
                      <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mb-3">
                        <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                        </svg>
                      </div>
                      <p className="text-xs text-gray-500">Ask about gaps, rewrites, or interview prep.</p>
                      <p className="text-[10px] text-gray-600 mt-1">The coach has full context of your resume and this job.</p>
                    </div>
                  )}
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                      {msg.role === "assistant" && (
                        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-[10px] font-bold text-white mr-2 mt-1 shrink-0">
                          AI
                        </div>
                      )}
                      <div className={`max-w-[75%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-blue-600/20 text-blue-100 rounded-br-md"
                          : "bg-white/5 text-gray-400 rounded-bl-md"
                      }`}>
                        {msg.role === "assistant" ? (
                          <div className="prose prose-invert prose-sm max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          msg.content
                        )}
                      </div>
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="flex justify-start">
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-[10px] font-bold text-white mr-2 mt-1 shrink-0">
                        AI
                      </div>
                      <div className="bg-white/5 px-3.5 py-2.5 rounded-2xl rounded-bl-md">
                        <div className="flex gap-1">
                          <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                          <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                          <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                        </div>
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
                    className="flex-1 px-3.5 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 text-sm transition placeholder:text-gray-600"
                    disabled={chatLoading}
                  />
                  <button
                    type="submit"
                    disabled={chatLoading || !chatInput.trim()}
                    className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-sm font-medium hover:from-blue-500 hover:to-purple-500 disabled:from-white/10 disabled:to-white/5 transition-all disabled:cursor-not-allowed shadow-lg shadow-blue-600/10"
                  >
                    Send
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
