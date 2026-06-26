import { useState } from "react";

function QuestionGroup({ title, items, color, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);

  if (!items || items.length === 0) return null;

  return (
    <div className="bg-white/5 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/5 transition"
      >
        <span className={`text-xs font-semibold uppercase tracking-wider ${color}`}>
          {title} ({items.length})
        </span>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-2">
          {items.map((q, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span className="text-gray-600 shrink-0 mt-0.5">{i + 1}.</span>
              <span className="text-gray-300">{typeof q === "string" ? q : (typeof q.question === "string" ? q.question : JSON.stringify(q.question))}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function QuestionsSection({ questions }) {
  if (!questions) return null;

  const hasAny = questions.technical?.length > 0 ||
    questions.behavioral?.length > 0 ||
    questions.gap_based?.length > 0;

  if (!hasAny) return null;

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">Interview Questions</h3>
      <div className="space-y-2">
        <QuestionGroup
          title="Technical"
          items={questions.technical}
          color="text-blue-400"
          defaultOpen={true}
        />
        <QuestionGroup
          title="Behavioral"
          items={questions.behavioral}
          color="text-purple-400"
          defaultOpen={false}
        />
        <QuestionGroup
          title="Skill Gap Based"
          items={questions.gap_based}
          color="text-amber-400"
          defaultOpen={false}
        />
      </div>
    </div>
  );
}
