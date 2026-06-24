export default function ScoreGauge({ score, label = "Match Score", sublabel }) {
  const r = 70;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 80 ? "#10b981" :
    score >= 60 ? "#f59e0b" :
    score >= 40 ? "#f97316" :
    "#ef4444";

  const textColor =
    score >= 80 ? "text-emerald-400" :
    score >= 60 ? "text-amber-400" :
    score >= 40 ? "text-orange-400" :
    "text-red-400";

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 flex flex-col items-center">
      <h3 className="text-sm font-medium text-gray-400 mb-3">{label}</h3>
      <div className="relative">
        <svg width="180" height="180" className="-rotate-90">
          <circle
            cx="90" cy="90" r={r}
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="10"
          />
          <circle
            cx="90" cy="90" r={r}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-bold ${textColor}`}>{score}</span>
          <span className="text-xs text-gray-500 mt-0.5">out of 100</span>
        </div>
      </div>
      {sublabel && (
        <p className="text-xs text-gray-500 mt-3">{sublabel}</p>
      )}
    </div>
  );
}
