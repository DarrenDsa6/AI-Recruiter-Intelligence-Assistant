import { Routes, Route } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<UploadPage />} />
      <Route path="/dashboard" element={<Dashboard />} />
    </Routes>
  );
}
