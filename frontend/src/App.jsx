import { lazy, Suspense } from "react";
import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/useAuth";
import { useLocation } from "react-router-dom";
import { ToastProvider } from "./ui/Toast";
import ErrorBoundary from "./ui/ErrorBoundary";
import HelpBot from "./components/HelpBot";

const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const MockExam = lazy(() => import("./pages/MockExam"));
const Plan = lazy(() => import("./pages/Plan"));
const Daily = lazy(() => import("./pages/Daily"));
const Profile = lazy(() => import("./pages/Profile"));

function ProtectedRoute({ children }) {
  const { user, checking } = useAuth();

  if (checking) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <span className="w-2.5 h-2.5 rounded-full bg-helix-teal inline-block animate-pulse" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

// Each page is its own error boundary, keyed by the path, so one broken page never blanks the app.
function RouteBoundary({ children }) {
  const location = useLocation();
  return <ErrorBoundary resetKey={location.pathname}>{children}</ErrorBoundary>;
}

export default function App() {
  return (
    <HashRouter>
      <ToastProvider>
      <AuthProvider>
        <Suspense
          fallback={
            <div className="min-h-screen bg-paper flex items-center justify-center">
              <span className="w-2.5 h-2.5 rounded-full bg-helix-teal inline-block animate-pulse" />
            </div>
          }
        >
          <RouteBoundary>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route
              path="/app"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/app/mock"
              element={
                <ProtectedRoute>
                  <MockExam />
                </ProtectedRoute>
              }
            />
            <Route
              path="/app/plan"
              element={
                <ProtectedRoute>
                  <Plan />
                </ProtectedRoute>
              }
            />
            <Route
              path="/app/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
            <Route
              path="/app/daily"
              element={
                <ProtectedRoute>
                  <Daily />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </RouteBoundary>
          <HelpBot />
        </Suspense>
      </AuthProvider>
      </ToastProvider>
    </HashRouter>
  );
}
