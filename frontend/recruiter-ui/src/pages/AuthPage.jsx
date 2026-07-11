import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { requestOTP, verifyOTP } from "../services/api";

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
      const { token, user_id } = await verifyOTP(email, fullCode);
      localStorage.setItem("auth_token", token);
      localStorage.setItem("user_id", user_id);
      localStorage.setItem("user_email", email);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Invalid code");
      setCode(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z", label: "ATS Compatibility Score" },
    { icon: "M11.42 15.17l-5.1-5.1m0 0L11.42 4.97m-5.1 5.1H21M3 3v18", label: "Actionable Resume Rewrites" },
    { icon: "M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12", label: "Gap-Focused Interview Prep" },
  ];

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8 animate-fade-in">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-purple-600 shadow-lg shadow-blue-600/20">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold">AI Resume Tailor</h1>
            <p className="text-sm text-gray-500 mt-1">
              {step === "email" ? "Sign in to optimize your resume" : `We sent a code to ${email}`}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-center gap-2">
          <div className={`flex items-center gap-1.5 ${step === "email" ? "text-blue-400" : "text-gray-500"}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium border ${
              step === "email" ? "border-blue-500 bg-blue-500/10" : "border-green-500 bg-green-500/10 text-green-400"
            }`}>
              {step === "otp" ? (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              ) : "1"}
            </div>
            <span className="text-xs font-medium">Email</span>
          </div>
          <div className="w-8 h-px bg-white/10" />
          <div className={`flex items-center gap-1.5 ${step === "otp" ? "text-blue-400" : "text-gray-600"}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium border ${
              step === "otp" ? "border-blue-500 bg-blue-500/10" : "border-white/10"
            }`}>2</div>
            <span className="text-xs font-medium">Verify</span>
          </div>
        </div>

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
          {step === "email" ? (
            <form onSubmit={handleRequestOTP} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 mb-1.5 block">Email address</label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setError(""); }}
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 text-sm transition placeholder:text-gray-600"
                  autoFocus
                />
              </div>
              {error && (
                <div className="bg-red-900/20 border border-red-800/30 rounded-xl px-4 py-2.5 flex items-center gap-2">
                  <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                  </svg>
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}
              <button
                type="submit"
                disabled={loading || !email.trim()}
                className="w-full py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-white/10 disabled:to-white/5 disabled:text-gray-600 transition-all disabled:cursor-not-allowed shadow-lg shadow-blue-600/10"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Sending...
                  </span>
                ) : "Send Code"}
              </button>
            </form>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); handleVerifyOTP(); }} className="space-y-5">
              <div>
                <label className="text-xs font-medium text-gray-400 mb-3 block">Verification code</label>
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
                      className={`w-11 h-12 rounded-xl bg-white/5 border text-center text-lg font-mono font-semibold transition-all focus:outline-none ${
                        digit
                          ? "border-blue-500/50 bg-blue-500/5 text-white"
                          : "border-white/10 text-gray-300"
                      } focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20`}
                      autoFocus={i === 0}
                    />
                  ))}
                </div>
              </div>
              {error && (
                <div className="bg-red-900/20 border border-red-800/30 rounded-xl px-4 py-2.5 flex items-center gap-2">
                  <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                  </svg>
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}
              <button
                type="submit"
                disabled={loading || code.some((d) => !d)}
                className="w-full py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-white/10 disabled:to-white/5 disabled:text-gray-600 transition-all disabled:cursor-not-allowed shadow-lg shadow-blue-600/10"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Verifying...
                  </span>
                ) : "Verify"}
              </button>
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => { setStep("email"); setCode(["", "", "", "", "", ""]); setError(""); }}
                  className="text-xs text-gray-500 hover:text-gray-300 transition"
                >
                  Change email
                </button>
                <button
                  type="button"
                  disabled={countdown > 0}
                  onClick={() => { setCountdown(60); requestOTP(email); }}
                  className="text-xs text-blue-400 hover:text-blue-300 transition disabled:text-gray-600 disabled:cursor-not-allowed"
                >
                  {countdown > 0 ? `Resend in ${countdown}s` : "Resend code"}
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="space-y-3">
          {features.map((f, i) => (
            <div key={i} className={`flex items-center gap-3 text-sm text-gray-500 animate-slide-up stagger-${i + 1}`}>
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center shrink-0">
                <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                </svg>
              </div>
              <span>{f.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
