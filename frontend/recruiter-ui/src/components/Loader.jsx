export default function Loader({ text = "Processing..." }) {
  return (
    <div className="flex flex-col items-center mt-6">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      <p className="mt-3 text-gray-300">{text}</p>
    </div>
  );
}