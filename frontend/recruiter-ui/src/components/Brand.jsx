import { useId } from "react";

export default function Brand({ size = 40, compact = false, className = "" }) {
  const id = useId();

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true" className="shrink-0 drop-shadow-[0_4px_12px_rgba(232,176,84,0.35)]">
        <defs>
          <linearGradient id={`${id}-grad`} x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
            <stop stopColor="#F0C778" />
            <stop offset="1" stopColor="#D68A24" />
          </linearGradient>
        </defs>
        <rect x="1" y="1" width="46" height="46" rx="13" fill={`url(#${id}-grad)`} />
        <rect x="1" y="1" width="46" height="46" rx="13" stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
        <path d="M15 10.5h11.5a4.5 4.5 0 0 1 4.5 4.5v17.5a4.5 4.5 0 0 1-4.5 4.5H15a4 4 0 0 1-4-4V14.5a4 4 0 0 1 4-4Z" fill="#14181F" />
        <path d="M15.5 18.5h13M15.5 23.5h13M15.5 28.5h9" stroke="#E8B054" strokeWidth="2.2" strokeLinecap="round" />
        <path d="M36 7l1.15 3 3 1.15-3 1.15-1.15 3-1.15-3-3-1.15 3-1.15 1.15-3Z" fill="#FFF3D6" />
        <path d="M41 21l.9 2.35 2.35.9-2.35.9-.9 2.35-.9-2.35-2.35-.9 2.35-.9.9-2.35Z" fill="#FFF3D6" />
      </svg>
      {!compact && (
        <div className="leading-tight">
          <p className="font-display text-[15px] font-semibold tracking-tight text-white">
            AI Recruiter
          </p>
          <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-neutral-400">
            Resume Intelligence
          </p>
        </div>
      )}
    </div>
  );
}
