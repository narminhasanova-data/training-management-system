import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext.jsx";
import Layout from "./components/Layout.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import AgendaPage from "./pages/agenda/AgendaPage.jsx";
import ChecklistPrototype from "./pages/ChecklistPrototype.jsx";
import ClassroomPage from "./pages/classroom/ClassroomPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ReportsPrototype from "./pages/ReportsPrototype.jsx";
import SurveyPage from "./pages/survey/SurveyPage.jsx";
import TrackerPage from "./pages/TrackerPage.jsx";

function Routed() {
  const { user } = useAuth();
  if (!user) return <LoginPage />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/agenda" element={<AgendaPage />} />
        <Route path="/surveys" element={<SurveyPage />} />
        <Route path="/tracker" element={<TrackerPage />} />
        <Route path="/classroom" element={<ClassroomPage />} />
        <Route path="/checklist" element={<ChecklistPrototype />} />
        <Route path="/reports" element={<ReportsPrototype />} />
        <Route path="*" element={<Navigate to="/agenda" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Routed />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
