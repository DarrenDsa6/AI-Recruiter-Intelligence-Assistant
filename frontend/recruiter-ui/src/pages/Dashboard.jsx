import { useState, useEffect, useRef, useCallback, useMemo, useContext } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchReports, fetchReport, fetchChatHistory, deleteReport, sendReportEmail, streamReportStatus, retryReport, logout } from "../services/api";
import { AuthContext } from "../context/AuthContext";
import GithubSection from "../components/GithubSection";
import Brand from "../components/Brand";
import ConfirmDialog from "../components/ConfirmDialog";

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function statusChip(status) {
  const map = {
    completed: "border-primary-400/30 bg-primary-500/10 text-primary-300",
    failed: "border-danger-500/30 bg-danger-500/10 text-danger-300",
    pending: "border-neutral-600/40 bg-neutral-700/30 text-neutral-300",
    processing: "border-primary-400/30 bg-primary-500/10 text-primary-300",
  };
  return `chip ${map[status] || map.pending}`;
}

function ScoreRing({ score }) {
  const pct = Math.min(score || 0, 100);
  const r = 34;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const tone = pct >= 80 ? "#E8B054" : pct >= 60 ? "#DF9636" : "#75818F";
  return (
    <div className="relative h-20 w-20 shrink-0">
      <svg width="80" height="80" viewBox="0 0 80 80" className="-rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="7" />
        <circle
          cx="40" cy="40" r={r} fill="none" stroke={tone} strokeWidth="7" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-xl font-semibold leading-none text-white">{Math.round(score)}</span>
        <span className="mt-1 text-[9px] uppercase tracking-widest text-neutral-400">ATS score</span>
      </div>
    </div>
  );
}

function ReportSection({ title, icon, delay, children }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="card animate-slide-up !p-0 overflow-hidden" style={{ animationDelay: `${delay}ms` }}>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-3">
          <span className="icon-tile">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
            </svg>
          </span>
          <h3 className="text-sm font-semibold text-neutral-100">{title}</h3>
        </div>
        <svg
          className={`h-4 w-4 text-neutral-500 transition-transform duration-300 ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {open && <div className="border-t border-white/[0.05] px-5 pb-5 pt-4">{children}</div>}
    </section>
  );
}

function EmptyState({ icon, title, desc, ctaLabel, onCta }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-20 text-center">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.02]">
        <svg className="h-8 w-8 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
        </svg>
      </div>
      <p className="text-sm font-medium text-neutral-300">{title}</p>
      <p className="mt-1 mb-5 max-w-xs text-xs text-neutral-500">{desc}</p>
      <button onClick={onCta} className="btn-primary !py-2.5 text-sm">{ctaLabel}</button>
    </div>
  );
}

const MSG_ICON = "M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z";

function ChatMessage({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mr-2.5 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-primary-500/15 text-primary-300">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
        </div>
      )}
      <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
        isUser
          ? "rounded-br-md bg-primary-500/15 text-primary-100"
          : "rounded-bl-md border border-white/[0.06] bg-white/[0.03] text-neutral-300"
      }`}>
        {!isUser ? (
          <div className="prose prose-sm prose-invert max-w-none prose-headings:my-2 prose-headings:text-white prose-p:my-1.5 prose-p:text-neutral-300 prose-strong:text-white prose-code:text-primary-300 prose-a:text-primary-300 prose-li:text-neutral-300 prose-li:marker:text-primary-400">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </div>
        ) : (
          msg.content
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="mr-2.5 mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-primary-500/15 text-primary-300">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
      </div>
      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-white/[0.06] bg-white/[0.03] px-4 py-3.5">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-500" style={{ animationDelay: "0ms" }} />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-500" style={{ animationDelay: "150ms" }} />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-500" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}

function ChatEmptyState({ maximized }) {
  return (
    <div className="flex h-full flex-col items-center justify-center py-8 text-center">
      <div className={`mb-3 flex items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.02] ${maximized ? "h-14 w-14" : "h-10 w-10"}`}>
        <svg className={`text-neutral-500 ${maximized ? "h-7 w-7" : "h-5 w-5"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d={MSG_ICON} />
        </svg>
      </div>
      <p className="text-xs font-medium text-neutral-400">Ask the career coach anything</p>
      <p className="mt-1 text-[11px] text-neutral-500">The coach has full context of your resume and this job.</p>
    </div>
  );
}

function finalizeStreaming(prev) {
  const updated = [...prev];
  const last = updated[updated.length - 1];
  if (last && last.role === "assistant" && last.streaming) {
    if (!last.content) {
      updated.pop();
    } else {
      updated[updated.length - 1] = { ...last, streaming: false };
    }
  }
  return updated;
}

function deriveReportTitle(activeReport) {
  const fromReport = activeReport?.report?.job_title;
  if (fromReport && fromReport.trim()) return fromReport.trim();

  const jd = activeReport?.jd_text || "";
  if (!jd.trim()) return "";
  const text = jd.trim();

  const header = text.match(/^\s*(?:job\s+title|position|role(?:\s+title)?|title)\s*:\s*(.+)$/im);
  if (header && header[1].trim()) return header[1].trim().slice(0, 60);

  const seeking = text.match(/\b(?:we\s+)?(?:are\s+(?:currently\s+)?)?(?:seeking|looking\s+for|hiring|recruiting)\s+(?:an?\s+|a\s+)?((?:[A-Z][A-Za-z0-9+#.-]+(?:\s|$)){1,3})/);
  if (seeking) return seeking[1].trim();

  const firstLine = text.split(/\r?\n/).map((l) => l.trim()).find((l) => l && l.length > 0 && l.length <= 50 && /^[A-Z]/.test(l) && !/[.:]$/.test(l));
  return firstLine ? firstLine : "";
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
  const [chatMaximized, setChatMaximized] = useState(false);
  const [emailSending, setEmailSending] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const chatEndRef = useRef(null);
  const abortRef = useRef(null);
  const reportsCache = useRef(null);
  const reportCache = useRef(new Map());
  const [loadError, setLoadError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [statusNotice, setStatusNotice] = useState("");

  const authUser = useContext(AuthContext);
  const userEmail = authUser?.email ?? "";

  const handleLogout = async () => {
    try {
      await logout();
    } catch {}
    navigate("/auth", { replace: true });
  };

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setLoading(true);
      setLoadError("");

      let list = [];
      try {
        list = reportsCache.current
          ? reportsCache.current
          : await fetchReports().then((data) => {
              const parsed = Array.isArray(data) ? data : data.reports || [];
              reportsCache.current = parsed;
              return parsed;
            });
        if (cancelled) return;
        setReports(list);

        if (reportId) {
          const cached = reportCache.current.get(reportId);
          if (cached) {
            setActiveReport(cached.report);
            setChatMessages(cached.messages);
          } else {
            const [report, history] = await Promise.all([
              fetchReport(reportId),
              fetchChatHistory(reportId).catch(() => ({ messages: [] })),
            ]);
            if (cancelled) return;
            const msgs = Array.isArray(history.messages) ? history.messages : [];
            reportCache.current.set(reportId, { report, messages: msgs });
            setActiveReport(report);
            setChatMessages(msgs);
          }
        } else if (list.length > 0) {
          navigate(`/dashboard/${list[0].id}`, { replace: true });
          return;
        }
        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        if (err?.status === 404 && list.length > 0) {
          navigate(`/dashboard/${list[0].id}`, { replace: true });
          return;
        }
        setLoadError("Failed to load your dashboard. Please try again.");
        setLoading(false);
      }
    }

    init();
    return () => { cancelled = true; };
  }, [reportId, navigate, reloadKey]);

  const refreshReport = useCallback(async (id) => {
    const [report, history] = await Promise.all([
      fetchReport(id),
      fetchChatHistory(id).catch(() => ({ messages: [] })),
    ]);
    const msgs = Array.isArray(history.messages) ? history.messages : [];
    reportCache.current.set(id, { report, messages: msgs });
    setActiveReport(report);
    setChatMessages(msgs);
    setReports((prev) => prev.map((r) => (r.id === id ? { ...r, status: report.status } : r)));
  }, []);

  const handleRetry = useCallback(async () => {
    if (!activeReport || retrying) return;
    setRetrying(true);
    try {
      await retryReport(activeReport.id);
      const optimistic = { ...activeReport, status: "pending", error_message: null };
      reportCache.current.set(activeReport.id, { report: optimistic, messages: [] });
      setActiveReport(optimistic);
      setReports((prev) => prev.map((r) => (r.id === activeReport.id ? { ...r, status: "pending" } : r)));
    } catch (err) {
      console.warn("Retry failed:", err);
    } finally {
      setRetrying(false);
    }
  }, [activeReport, retrying]);

  useEffect(() => {
    if (!activeReport || activeReport.status === "completed" || activeReport.status === "failed") return;

    const eventSource = streamReportStatus(
      activeReport.id,
      async (status) => {
        if (status === "completed" || status === "failed") {
          setStatusNotice("");
          await refreshReport(activeReport.id);
        } else if (status === "timeout") {
          setStatusNotice("Still processing... We'll notify you by email when your report is ready.");
        }
      },
      () => {},
    );

    return () => { eventSource.close(); setStatusNotice(""); };
  }, [activeReport, refreshReport]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleChat = useCallback(async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading || !activeReport) return;

    const userMsg = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setChatLoading(true);

    const API = (process.env.REACT_APP_API_URL ?? "") + "/api";

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
              const content = parsed.content;
              setChatMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant" && last.streaming) {
                  updated[updated.length - 1] = { ...last, content };
                } else {
                  updated.push({ role: "assistant", content, streaming: true });
                }
                return updated;
              });
            }
            if (parsed.type === "error") {
              const msg = parsed.message;
              setChatMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant" && last.streaming) {
                  updated[updated.length - 1] = { ...last, content: `**Error:** ${msg}` };
                } else {
                  updated.push({ role: "assistant", content: `**Error:** ${msg}`, streaming: true });
                }
                return updated;
              });
            }
            if (parsed.type === "final") {
              setChatMessages(finalizeStreaming);
            }
          } catch {}
        }
      }

      setChatMessages(finalizeStreaming);
    } catch (err) {
      if (err.name === "AbortError") return;
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: `**Error:** ${err.message || "Failed to get response."}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  }, [chatInput, chatLoading, activeReport]);

  useEffect(() => {
    return () => { if (abortRef.current) abortRef.current.abort(); };
  }, []);

  const { ats_score, summary, strengths, gaps, recommendations, actionableRewrites, questions } = useMemo(() => {
    const analysis = activeReport?.report || {};
    const rw = activeReport?.rewrites;
    return {
      ats_score: analysis.ats_score,
      summary: analysis.summary,
      strengths: analysis.strengths || [],
      gaps: analysis.improvement_areas || analysis.gaps || [],
      recommendations: analysis.keyword_suggestions || analysis.recommendations || [],
      actionableRewrites: !rw ? [] : Array.isArray(rw) ? rw : Array.isArray(rw.rewrites) ? rw.rewrites : [],
      questions: activeReport?.questions || {},
    };
  }, [activeReport]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="relative h-14 w-14">
          <div className="absolute inset-0 rounded-full border-2 border-primary-400/15" />
          <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-primary-400" />
          <div className="absolute inset-2 animate-spin rounded-full border-2 border-transparent border-t-primary-500/60" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-sm text-neutral-300">{loadError}</p>
        <button onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary !px-6 !py-2.5 text-sm">Try again</button>
      </div>
    );
  }

  const chatPanel = ({ maximized }) => (
    <>
      <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4">
        <span className="icon-tile">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
            <path strokeLinecap="round" strokeLinejoin="round" d={MSG_ICON} />
          </svg>
        </span>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-neutral-100">Career Coach Chat</h3>
          <p className="text-[11px] text-neutral-500">Resume-aware follow-ups &amp; interview prep</p>
        </div>
        {chatMessages.length > 0 && (
          <span className="text-[11px] tabular-nums text-neutral-500">{chatMessages.length} msgs</span>
        )}
        <button
          onClick={() => setChatMaximized(!maximized)}
          className="rounded-lg p-1.5 text-neutral-500 transition-colors hover:bg-white/[0.06] hover:text-neutral-200"
          title={maximized ? "Minimize chat" : "Maximize chat"}
        >
          {maximized ? (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 4.5l15 15m0 0H8.25m11.25 0V8.25" />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
            </svg>
          )}
        </button>
      </div>
      <div className={`flex flex-col p-5 ${maximized ? "min-h-0 flex-1" : "h-72"}`}>
        <div className="mb-4 flex-1 space-y-3.5 overflow-y-auto pr-1">
          {chatMessages.length === 0 && <ChatEmptyState maximized={maximized} />}
          {chatMessages.map((msg, i) => (
            <ChatMessage key={i} msg={msg} />
          ))}
          {chatLoading && <TypingIndicator />}
          <div ref={chatEndRef} />
        </div>
        <form onSubmit={handleChat} className="flex shrink-0 gap-2.5">
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Ask the career coach..."
            className="input flex-1"
            disabled={chatLoading}
          />
          <button
            type="submit"
            disabled={chatLoading || !chatInput.trim()}
            className="btn-primary !px-5"
          >
            Send
          </button>
        </form>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/[0.06] bg-neutral-900 transition-transform duration-300 lg:static lg:z-auto lg:h-screen lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b border-white/[0.06] p-5">
          <button onClick={() => navigate("/")} className="mb-5 block transition-opacity hover:opacity-80">
            <Brand size={34} />
          </button>
          <button onClick={() => navigate("/")} className="btn-primary w-full !py-2.5 text-sm">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New analysis
          </button>
          <div className="mt-5 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-primary-400/25 bg-primary-500/10 font-display text-sm font-semibold text-primary-300">
              {(userEmail || "?")[0].toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-neutral-200">{userEmail}</p>
              <p className="text-[11px] text-neutral-500">{reports.length} report{reports.length !== 1 ? "s" : ""}</p>
            </div>
            <button onClick={handleLogout} className="btn-ghost !px-2 !py-1.5 text-[11px]" title="Sign out">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-3">
          {reports.length === 0 && (
            <div className="px-5 py-6 text-center">
              <p className="text-xs text-neutral-500">No reports yet.</p>
              <p className="mt-1 text-[11px] text-neutral-600">Upload a resume to get started.</p>
            </div>
          )}
          {reports.map((r) => {
            const active = r.id === activeReport?.id;
            return (
              <div key={r.id} className="group relative px-2">
                <button
                  onClick={() => { setSidebarOpen(false); navigate(`/dashboard/${r.id}`); }}
                  className={`relative flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${
                    active ? "bg-primary-500/[0.08]" : "hover:bg-white/[0.04]"
                  }`}
                >
                  {active && <span className="absolute left-0 top-2.5 h-[calc(100%-1.25rem)] w-[3px] rounded-full bg-primary-400" />}
                  <div className="min-w-0 flex-1">
                    <p className={`truncate text-[13px] ${active ? "font-medium text-neutral-100" : "text-neutral-300"}`}>
                      {r.filename || "Untitled Position"}
                    </p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <span className="text-[11px] text-neutral-500">{formatDate(r.created_at)}</span>
                      <span className={statusChip(r.status)}>{r.status}</span>
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => setDeleteTarget(r.id)}
                  className="absolute right-2 top-2.5 rounded-lg p-1.5 text-neutral-500 opacity-0 transition-all hover:bg-danger-500/10 hover:text-danger-400 group-hover:opacity-100"
                  title="Delete report"
                >
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/[0.06] bg-neutral-950/80 px-4 py-3 backdrop-blur-xl lg:hidden">
          <button onClick={() => setSidebarOpen(true)} className="btn-secondary !px-2.5 !py-2" title="Open menu">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <Brand size={28} />
          <button onClick={handleLogout} className="btn-secondary !px-2.5 !py-2" title="Sign out">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
            </svg>
          </button>
        </header>

        <div className="mx-auto w-full max-w-4xl flex-1 px-4 py-6 sm:px-6 lg:py-10">
          {statusNotice && (
            <div className="mb-4 flex items-start gap-3 rounded-xl border border-primary-400/20 bg-primary-500/[0.06] px-4 py-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-500/20">
                <svg className="h-3 w-3 text-primary-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
              </span>
              <p className="text-xs leading-relaxed text-neutral-300">{statusNotice}</p>
            </div>
          )}
          {!activeReport ? (
            <EmptyState
              icon="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              title="No report selected"
              desc="Upload a resume and job description to see your analysis here."
              ctaLabel="Upload resume"
              onCta={() => navigate("/")}
            />
          ) : activeReport.status === "pending" || activeReport.status === "processing" ? (
            <div className="flex flex-1 flex-col items-center justify-center py-20 text-center">
              <div className="relative mb-6 h-16 w-16">
                <div className="absolute inset-0 rounded-full border-2 border-primary-400/15" />
                <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-primary-400" />
                <div className="absolute inset-2.5 animate-spin rounded-full border-2 border-transparent border-t-primary-500/60" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
              </div>
              <p className="text-sm font-medium text-neutral-200">
                {activeReport.status === "pending" ? "Waiting in queue..." : "Analyzing your resume..."}
              </p>
              <p className="mt-1.5 text-xs text-neutral-500">This usually takes 30–60 seconds</p>
              <div className="mt-8 flex items-center gap-3 text-[11px] text-neutral-400">
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${activeReport.status === "pending" ? "animate-pulse bg-primary-400" : "bg-neutral-600"}`} />
                  Queued
                </div>
                <span className="h-px w-6 bg-neutral-700" />
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${activeReport.status === "processing" ? "animate-pulse bg-primary-400" : "bg-neutral-600"}`} />
                  Processing
                </div>
                <span className="h-px w-6 bg-neutral-700" />
                <div className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-neutral-600" />
                  Complete
                </div>
              </div>
            </div>
          ) : activeReport.status === "failed" ? (
            <div className="flex flex-1 flex-col items-center justify-center py-20 text-center">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-danger-500/25 bg-danger-500/10">
                <svg className="h-7 w-7 text-danger-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-danger-300">Analysis failed</p>
              <p className="mt-1 max-w-xs text-xs text-neutral-500">{activeReport.error_message || "Something went wrong. Please try again."}</p>
              <button onClick={handleRetry} disabled={retrying} className="btn-secondary mt-5">
                {retrying ? "Retrying..." : "Try again"}
              </button>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-col gap-5 animate-fade-in md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={statusChip(activeReport.status)}>{activeReport.status}</span>
                    <span className="text-xs text-neutral-500">Analyzed {formatDate(activeReport.created_at)}</span>
                  </div>
                  <h1 className="mt-2 font-display text-2xl font-semibold tracking-tight text-white sm:text-[26px]">
                    {deriveReportTitle(activeReport) || activeReport.filename || activeReport.jd_text?.slice(0, 60) || "Resume Analysis"}
                  </h1>
                </div>
                <div className="flex items-center gap-4">
                  <button
                    onClick={async () => {
                      setEmailSending(true);
                      try {
                        await sendReportEmail(activeReport.id);
                        alert("Report sent to " + userEmail);
                      } catch (e) {
                        alert("Failed to send: " + (e.message || "Unknown error"));
                      } finally {
                        setEmailSending(false);
                      }
                    }}
                    disabled={emailSending}
                    className="btn-secondary !py-2.5"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                    </svg>
                    {emailSending ? "Sending..." : "Email report"}
                  </button>
                  {ats_score != null && <ScoreRing score={ats_score} />}
                </div>
              </div>

              {summary && (
                <ReportSection title="Summary" icon="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" delay={0}>
                  <p className="text-sm leading-relaxed text-neutral-300">{summary}</p>
                </ReportSection>
              )}

              {strengths.length > 0 && (
                <ReportSection title="Strengths" icon="M4.5 12.75l6 6 9-13.5" delay={80}>
                  <ul className="space-y-2.5">
                    {strengths.map((s, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-sm text-neutral-300">
                        <span className="icon-tile h-5 w-5 border-success-500/20 bg-success-500/10 text-success-400">
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                          </svg>
                        </span>
                        <span className="pt-0.5">{typeof s === "string" ? s : s.text || s.description || JSON.stringify(s)}</span>
                      </li>
                    ))}
                  </ul>
                </ReportSection>
              )}

              {gaps.length > 0 && (
                <ReportSection title="Skill Gaps" icon="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" delay={160}>
                  <ul className="space-y-2.5">
                    {gaps.map((g, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-sm text-neutral-300">
                        <span className="icon-tile h-5 w-5 border-danger-500/20 bg-danger-500/10 text-danger-400">
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                          </svg>
                        </span>
                        <span className="pt-0.5">{typeof g === "string" ? g : g.text || g.description || JSON.stringify(g)}</span>
                      </li>
                    ))}
                  </ul>
                </ReportSection>
              )}

              {recommendations.length > 0 && (
                <ReportSection title="Keyword Suggestions" icon="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" delay={240}>
                  <div className="space-y-3">
                    {recommendations.map((r, i) => (
                      <div key={i} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-2">
                        {r.original && (
                          <p className="text-xs text-neutral-500 line-through leading-relaxed">{r.original}</p>
                        )}
                        <p className="text-sm leading-relaxed text-neutral-200">{r.suggested_rewrite || r.suggestion || JSON.stringify(r)}</p>
                      </div>
                    ))}
                  </div>
                </ReportSection>
              )}

              <ReportSection title="Actionable Rewrites" icon="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" delay={320}>
                {actionableRewrites.length > 0 ? (
                  <div className="space-y-3">
                    {actionableRewrites.map((rewrite, i) => {
                      const orig = rewrite.original_chunk || rewrite.original || "";
                      const opts = rewrite.rewrite_options || rewrite.rewrites || [];
                      return (
                        <div key={i} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-2.5">
                          {orig && (
                            <div>
                              <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Original</p>
                              <p className="text-xs text-neutral-500 line-through leading-relaxed">{orig}</p>
                            </div>
                          )}
                          <div>
                            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-primary-300">Rewrite</p>
                            {opts.length > 0 ? (
                              <ul className="space-y-2">
                                {opts.map((opt, j) => (
                                  <li key={j} className="text-sm leading-relaxed text-neutral-100">
                                    {typeof opt === "string" ? opt : opt.text || opt.rewrite || JSON.stringify(opt)}
                                  </li>
                                ))}
                              </ul>
                            ) : rewrite.rewrite && (
                              <p className="text-sm leading-relaxed text-neutral-100">{rewrite.rewrite}</p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-neutral-500">No rewrites generated for this analysis.</p>
                )}
              </ReportSection>

              {activeReport.github_analysis && (
                <GithubSection data={activeReport.github_analysis} />
              )}

              {(() => {
                const gapQuestions = questions.gap_focused || [];
                const techQuestions = questions.technical || [];
                const behaviorQuestions = questions.behavioral || [];
                const allQuestions = [...techQuestions, ...behaviorQuestions, ...gapQuestions];
                if (allQuestions.length === 0) return null;
                return (
                  <ReportSection title="Interview Questions" icon="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" delay={400}>
                    <div className="space-y-3">
                      {allQuestions.map((q, i) => (
                        <div key={i} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-2">
                          <p className="text-sm font-medium leading-relaxed text-neutral-100">{q.question}</p>
                          {q.why_likely && <p className="text-xs text-neutral-500">{q.why_likely}</p>}
                          {q.prep_tips && <p className="text-xs text-primary-300">{q.prep_tips}</p>}
                        </div>
                      ))}
                    </div>
                  </ReportSection>
                );
              })()}

              {!chatMaximized && (
                <section className="card !p-0 overflow-hidden animate-slide-up" style={{ animationDelay: "400ms" }}>
                  {chatPanel({ maximized: false })}
                </section>
              )}
            </div>
          )}
        </div>
      </main>

      {chatMaximized && (
        <div className="fixed inset-0 z-[60] flex flex-col bg-neutral-950 animate-fade-in">
          <div className="mx-auto flex h-full w-full max-w-4xl flex-col">
            {chatPanel({ maximized: true })}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete this report?"
        message="This report and its analysis will be permanently removed. You cannot undo this action."
        confirmLabel="Delete"
        danger
        onConfirm={async () => {
          const id = deleteTarget;
          setDeleteTarget(null);
          try {
            await deleteReport(id);
            reportCache.current.delete(id);
            reportsCache.current = null;
            setReports((prev) => prev.filter((x) => x.id !== id));
            if (activeReport?.id === id) {
              setActiveReport(null);
              navigate("/dashboard", { replace: true });
            }
          } catch (e) {
            alert(`Failed to delete: ${e.message || "Unknown error"}`);
          }
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
