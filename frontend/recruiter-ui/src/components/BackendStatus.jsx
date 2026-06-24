export default function BackendStatus({ status }) {
  const color =
    status === "connected"
      ? "bg-green-500"
      : status === "connecting"
      ? "bg-yellow-500"
      : "bg-red-500";

  const text =
    status === "connected"
      ? "Connected"
      : status === "connecting"
      ? "Connecting..."
      : "Disconnected";

  return (
    <div className="fixed top-4 right-4 flex items-center gap-2 bg-black/60 backdrop-blur-md px-4 py-2 rounded-full text-white shadow-lg">
      <span className={`w-3 h-3 rounded-full ${color}`}></span>
      <span className="text-sm">{text}</span>
    </div>
  );
}