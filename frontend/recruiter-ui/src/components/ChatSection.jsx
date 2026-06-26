import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

function ChatMessage({ role, content }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[90%] md:max-w-[80%] px-3.5 py-2.5 rounded-xl text-sm leading-relaxed ${
        isUser
          ? "bg-blue-600/80 rounded-br-sm"
          : "bg-white/10 rounded-bl-sm"
      }`}>
        {isUser ? (
          <p className="text-white/90">{content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none text-gray-200">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

function StreamingMessage({ content }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] md:max-w-[80%] px-3.5 py-2.5 rounded-xl rounded-bl-sm bg-white/10 text-sm leading-relaxed">
        <div className="prose prose-invert prose-sm max-w-none text-gray-200">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>
        <span className="inline-block w-1.5 h-3.5 bg-blue-400 ml-0.5 animate-pulse align-middle" />
      </div>
    </div>
  );
}

export default function ChatSection({ sessionId, disabled }) {
  const [messages, setMessages] = useState([]);
  const [currentAI, setCurrentAI] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [maximized, setMaximized] = useState(false);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentAI]);

  const streamChat = useCallback(async (message) => {
    setLoading(true);
    setCurrentAI("");

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message }),
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
          const json = trimmed.replace("data:", "").trim();
          if (!json) continue;

          try {
            const parsed = JSON.parse(json);
            if (parsed.type === "text") {
              fullText += parsed.content;
              setCurrentAI(fullText);
            }
            if (parsed.type === "error") {
              fullText += `\n\n**Error:** ${parsed.message}`;
              setCurrentAI(fullText);
            }
          } catch {}
        }
      }

      if (fullText) {
        setMessages((prev) => [...prev, { role: "assistant", content: fullText }]);
      }
      setCurrentAI("");
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }, [sessionId]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading || disabled) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    streamChat(text);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const chatContent = (
    <>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300">Follow-Up Questions</h3>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={() => setMessages([])}
              className="text-[10px] text-gray-600 hover:text-gray-400 transition"
            >
              Clear chat
            </button>
          )}
          <button
            onClick={() => setMaximized((m) => !m)}
            className="text-gray-500 hover:text-gray-300 transition"
            title="Expand"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>
        </div>
      </div>

      <div className="overflow-y-auto space-y-3 mb-4 scrollbar-thin max-h-72">
        {messages.length === 0 && !loading && (
          <p className="text-xs text-gray-600 text-center py-6">
            Ask anything about the candidate — skills, experience, or role fit.
          </p>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} role={msg.role} content={msg.content} />
        ))}

        {currentAI && <StreamingMessage content={currentAI} />}

        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 items-end">
        <textarea
          ref={inputRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a follow-up question..."
          disabled={loading || disabled}
          className="flex-1 p-2.5 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 resize-none text-sm disabled:opacity-40 transition"
          style={{ minHeight: "38px", maxHeight: "100px" }}
          onInput={(e) => {
            e.target.style.height = "auto";
            e.target.style.height = Math.min(e.target.scrollHeight, 100) + "px";
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim() || disabled}
          className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-white/10 disabled:text-gray-600 rounded-xl transition text-sm font-medium"
        >
          {loading ? (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin block" />
          ) : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          )}
        </button>
      </div>
    </>
  );

  return (
    <>
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
        {chatContent}
      </div>

      {maximized && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-[#0B0F19] border border-white/10 rounded-2xl w-[95vw] h-[90vh] flex flex-col p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4 shrink-0">
              <h3 className="text-sm font-semibold text-gray-300">Follow-Up Questions</h3>
              <button
                onClick={() => setMaximized(false)}
                className="text-gray-500 hover:text-gray-300 transition p-1"
                title="Close"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 mb-4 scrollbar-thin">
              {messages.length === 0 && !loading && (
                <p className="text-xs text-gray-600 text-center py-6">
                  Ask anything about the candidate — skills, experience, or role fit.
                </p>
              )}
              {messages.map((msg, i) => (
                <ChatMessage key={i} role={msg.role} content={msg.content} />
              ))}
              {currentAI && <StreamingMessage content={currentAI} />}
              <div ref={bottomRef} />
            </div>
            <div className="flex gap-2 items-end shrink-0">
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a follow-up question..."
                disabled={loading || disabled}
                className="flex-1 p-2.5 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 resize-none text-sm disabled:opacity-40 transition"
                style={{ minHeight: "38px", maxHeight: "100px" }}
                onInput={(e) => {
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 100) + "px";
                }}
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim() || disabled}
                className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-white/10 disabled:text-gray-600 rounded-xl transition text-sm font-medium"
              >
                {loading ? (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin block" />
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
