import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { requestOTP, verifyOTP } from "../services/api";
import Brand from "../components/Brand";

const FEATURES = [
  {
    icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    title: "ATS Compatibility Score",
    desc: "See exactly how well your resume matches the role",
  },
  {
    icon: "M11.42 15.17l-5.1-5.1m0 0L11.42 4.97m-5.1 5.1H21M3 3v18",
    title: "Actionable Resume Rewrites",
    desc: "Turn weak bullet points into interview-winning lines",
  },
  {
    icon: "M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12",
    title: "Gap-Focused Interview Prep",
    desc: "Practice the questions your skill gaps are most likely to trigger",
  },
];

function StepDot({ state }) {
  if (state === "done") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full border border-primary-400/50 bg-primary-500/10 text-primary-300">
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </span>
    );
  }
  return (
    <span
      className={`flex h-6 w-6 items-center justify-center rounded-full border text-[11px] font-semibold ${
        state === "active"
          ? "border-primary-400/60 bg-primary-500/10 text-primary-300"
          : "border-white/10 text-neutral-500"
      }`}
    >
      {2}
    </span>
  );
}

function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-danger-500/25 bg-danger-500/10 px-3.5 py-2.5">
      <svg className="mt-0.5 h-4 w-4 shrink-0 text-danger-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      <p className="text-sm text-danger-300">{message}</p>
    </div>
  );
}

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [step, setStep] = useState("email");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(0);
  const navigate = useNavigate();
  const inputRefs = useRef([]);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const handleRequestOTP = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError("");
    try {
      await requestOTP(email);
      setStep("otp");
      setCountdown(60);
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    } catch (err) {
      setError(err.message || "Failed to send code");
    } finally {
      setLoading(false);
    }
  };

  const handleCodeChange = (index, value) => {
    if (!/^\d*$/.test(value)) return;
    const newCode = [...code];
    newCode[index] = value.slice(-1);
    setCode(newCode);
    setError("");
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
    if (newCode.every((d) => d !== "")) {
      handleVerifyOTP(newCode.join(""));
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length === 6) {
      const newCode = pasted.split("");
      setCode(newCode);
      inputRefs.current[5]?.focus();
      setTimeout(() => handleVerifyOTP(pasted), 100);
    }
  };

  const handleVerifyOTP = async (codeStr) => {
    const fullCode = codeStr || code.join("");
    if (fullCode.length !== 6) return;
    setLoading(true);
    setError("");
    try {
      await verifyOTP(email, fullCode);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Invalid code");
      setCode(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[42rem] -translate-x-1/2 rounded-full bg-primary-500/[0.07] blur-3xl" />
      <div className="pointer-events-none absolute -bottom-48 -right-32 h-96 w-96 rounded-full bg-primary-600/[0.05] blur-3xl" />

      <div className="relative w-full max-w-md animate-fade-in">
        <div className="mb-8 flex flex-col items-center gap-4 text-center">
          <Brand size={52} />
          <div>
            <h1 className="font-display text-[26px] font-semibold tracking-tight text-white">
              Sign in to AI Recruiter
            </h1>
            <p className="mt-1 text-sm text-neutral-400">
              {step === "email"
                ? "We'll send a one-time code to your inbox"
                : `We sent a 6-digit code to ${email}`}
            </p>
          </div>
        </div>

        <div className="card p-6 sm:p-7">
          <div className="mb-6 flex items-center justify-center gap-3">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full border border-primary-400/60 bg-primary-500/10 text-[11px] font-semibold text-primary-300">
                1
              </span>
              <span className="text-xs font-medium text-neutral-300">Email</span>
            </div>
            <span className="h-px w-8 bg-primary-400/40" />
            <div className="flex items-center gap-2">
              <StepDot state={step === "otp" ? "active" : "pending"} />
              <span className={`text-xs font-medium ${step === "otp" ? "text-neutral-200" : "text-neutral-500"}`}>Verify</span>
            </div>
          </div>

          {step === "email" ? (
            <form onSubmit={handleRequestOTP} className="space-y-4">
              <div>
                <label className="label" htmlFor="auth-email">Email address</label>
                <input
                  id="auth-email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setError(""); }}
                  className="input"
                  autoFocus
                />
              </div>
              <ErrorBanner message={error} />
              <button
                type="submit"
                disabled={loading || !email.trim()}
                className="btn-primary w-full"
              >
                {loading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Sending...
                  </>
                ) : (
                  "Send code"
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); handleVerifyOTP(); }} className="space-y-5">
              <div>
                <label className="label text-center sm:text-left">Verification code</label>
                <div className="flex justify-center gap-2" onPaste={handlePaste}>
                  {code.map((digit, i) => (
                    <input
                      key={i}
                      ref={(el) => (inputRefs.current[i] = el)}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleCodeChange(i, e.target.value)}
                      onKeyDown={(e) => handleKeyDown(i, e)}
                      className={`h-12 w-10 rounded-xl border text-center text-lg font-semibold transition-all outline-none sm:w-11 ${
                        digit
                          ? "border-primary-400/50 bg-primary-500/10 text-primary-300"
                          : "border-white/10 bg-white/[0.03] text-neutral-100"
                      } focus:border-primary-400/60 focus:ring-2 focus:ring-primary-400/20`}
                      autoFocus={i === 0}
                    />
                  ))}
                </div>
              </div>
              <ErrorBanner message={error} />
              <button
                type="submit"
                disabled={loading || code.some((d) => !d)}
                className="btn-primary w-full"
              >
                {loading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Verifying...
                  </>
                ) : (
                  "Verify & continue"
                )}
              </button>
              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={() => { setStep("email"); setCode(["", "", "", "", "", ""]); setError(""); }}
                  className="btn-ghost"
                >
                  Change email
                </button>
                <button
                  type="button"
                  disabled={countdown > 0}
                  onClick={() => {
                    setCountdown(60);
                    setError("");
                    requestOTP(email).catch((err) => {
                      setCountdown(0);
                      setError(err?.message || "Couldn't resend the code. Please try again.");
                    });
                  }}
                  className={`text-xs font-medium transition disabled:pointer-events-none ${countdown > 0 ? "text-neutral-500" : "text-primary-300 hover:text-primary-200"}`}
                >
                  {countdown > 0 ? `Resend in ${countdown}s` : "Resend code"}
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="mt-8 grid gap-2.5">
          {FEATURES.map((f, i) => (
            <div key={i} className={`flex items-center gap-3 rounded-xl border border-white/[0.05] bg-white/[0.02] px-4 py-3 animate-fade-in stagger-${i + 1}`}>
              <div className="icon-tile">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                </svg>
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-neutral-200">{f.title}</p>
                <p className="text-xs text-neutral-400">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
