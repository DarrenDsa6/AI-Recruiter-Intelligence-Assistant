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

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300">Follow-Up Questions</h3>
        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="text-[10px] text-gray-600 hover:text-gray-400 transition"
          >
            Clear chat
          </button>
        )}
      </div>

      <div className="max-h-72 overflow-y-auto space-y-3 mb-4 scrollbar-thin">
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
    </div>
  );
}
