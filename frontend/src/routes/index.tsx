import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { lazy, Suspense, useTransition } from "react";
import { useAuthStore } from "@/store/auth";
import type { UserRole } from "@/types";
import { PublicLayout } from "@/layouts/PublicLayout";
import { AppLayout } from "@/layouts/AppLayout";
import { Skeleton } from "@/components/ui/feedback";
import { AnimatePresence, motion } from "framer-motion";

const LandingPage = lazy(() => import("@/pages/public/LandingPage").then((m) => ({ default: m.LandingPage })));
const AboutPage = lazy(() => import("@/pages/public/AboutPage").then((m) => ({ default: m.AboutPage })));
const PublicMapPage = lazy(() => import("@/pages/public/PublicMapPage").then((m) => ({ default: m.PublicMapPage })));
const TrackIncidentPage = lazy(() => import("@/pages/public/TrackIncidentPage").then((m) => ({ default: m.TrackIncidentPage })));
const AnnouncementsPage = lazy(() => import("@/pages/public/AnnouncementsPage").then((m) => ({ default: m.AnnouncementsPage })));
const LoginPage = lazy(() => import("@/pages/public/LoginPage").then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import("@/pages/public/RegisterPage").then((m) => ({ default: m.RegisterPage })));
const ForgotPasswordPage = lazy(() => import("@/pages/public/ForgotPasswordPage").then((m) => ({ default: m.ForgotPasswordPage })));
const TwoFactorSetupPage = lazy(() => import("@/pages/public/TwoFactorSetupPage").then((m) => ({ default: m.TwoFactorSetupPage })));
const TwoFactorVerifyPage = lazy(() => import("@/pages/public/TwoFactorVerifyPage").then((m) => ({ default: m.TwoFactorVerifyPage })));

const CitizenDashboard = lazy(() => import("@/pages/citizen/CitizenDashboard").then((m) => ({ default: m.CitizenDashboard })));
const CreateIncidentPage = lazy(() => import("@/pages/citizen/CreateIncidentPage").then((m) => ({ default: m.CreateIncidentPage })));
const MyIncidentsPage = lazy(() => import("@/pages/citizen/MyIncidentsPage").then((m) => ({ default: m.MyIncidentsPage })));
const IncidentDetailPage = lazy(() => import("@/pages/shared/IncidentDetailPage").then((m) => ({ default: m.IncidentDetailPage })));
const NotificationsPage = lazy(() => import("@/pages/shared/NotificationsPage").then((m) => ({ default: m.NotificationsPage })));
const ProfilePage = lazy(() => import("@/pages/shared/ProfilePage").then((m) => ({ default: m.ProfilePage })));

const AuthorityDashboard = lazy(() => import("@/pages/authority/AuthorityDashboard").then((m) => ({ default: m.AuthorityDashboard })));
const IncidentQueuePage = lazy(() => import("@/pages/authority/IncidentQueuePage").then((m) => ({ default: m.IncidentQueuePage })));
const AnalyticsPage = lazy(() => import("@/pages/authority/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })));
const UserManagementPage = lazy(() => import("@/pages/authority/UserManagementPage").then((m) => ({ default: m.UserManagementPage })));
const AuditLogsPage = lazy(() => import("@/pages/authority/AuditLogsPage").then((m) => ({ default: m.AuditLogsPage })));
const AdminOverviewPage = lazy(() => import("@/pages/authority/AdminOverviewPage").then((m) => ({ default: m.AdminOverviewPage })));
const AnnouncementAdminPage = lazy(() => import("@/pages/authority/AnnouncementAdminPage").then((m) => ({ default: m.AnnouncementAdminPage })));
const DemoDataAdminPage = lazy(() => import("@/pages/authority/DemoDataAdminPage").then((m) => ({ default: m.DemoDataAdminPage })));

const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.25, ease: "easeOut" },
};

function PageShell({ children }: { children: React.ReactNode }) {
  useTransition();
  
  return (
    <Suspense
      fallback={
        <div className="animate-pulse space-y-4">
          <Skeleton className="h-8 w-1/4" />
          <Skeleton className="h-4 w-1/2" />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={useLocation().pathname}
          initial="initial"
          animate="animate"
          exit="exit"
          variants={pageVariants}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </Suspense>
  );
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("safecity.access");
  const location = useLocation();
  if (!token) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

function RequireRole({ allowed, children }: { allowed: UserRole[]; children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  if (!allowed.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<PageShell><LandingPage /></PageShell>} />
        <Route path="/about" element={<PageShell><AboutPage /></PageShell>} />
        <Route path="/map" element={<PageShell><PublicMapPage /></PageShell>} />
        <Route path="/track" element={<PageShell><TrackIncidentPage /></PageShell>} />
        <Route path="/announcements" element={<PageShell><AnnouncementsPage /></PageShell>} />
        <Route path="/login" element={<PageShell><LoginPage /></PageShell>} />
        <Route path="/2fa/setup" element={<PageShell><TwoFactorSetupPage /></PageShell>} />
        <Route path="/2fa/verify" element={<PageShell><TwoFactorVerifyPage /></PageShell>} />
        <Route path="/register" element={<PageShell><RegisterPage /></PageShell>} />
        <Route path="/forgot-password" element={<PageShell><ForgotPasswordPage /></PageShell>} />
      </Route>

      {/* Authenticated (citizen + authority share AppLayout) */}
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<PageShell><CitizenDashboard /></PageShell>} />
        <Route path="/incidents" element={<PageShell><MyIncidentsPage /></PageShell>} />
        <Route path="/incidents/:id" element={<PageShell><IncidentDetailPage /></PageShell>} />
        <Route path="/notifications" element={<PageShell><NotificationsPage /></PageShell>} />
        <Route path="/profile" element={<PageShell><ProfilePage /></PageShell>} />

        {/* Citizen only */}
        <Route
          path="/report"
          element={
            <RequireRole allowed={["citizen", "city_admin", "superuser", "department_staff"]}>
              <PageShell><CreateIncidentPage /></PageShell>
            </RequireRole>
          }
        />

        {/* Admin */}
        <Route
          path="/admin"
          element={
            <RequireRole allowed={["city_admin", "superuser"]}>
              <PageShell><AdminOverviewPage /></PageShell>
            </RequireRole>
          }
        />
        <Route
          path="/admin/announcements"
          element={
            <RequireRole allowed={["city_admin", "superuser"]}>
              <PageShell><AnnouncementAdminPage /></PageShell>
            </RequireRole>
          }
        />
        <Route
          path="/admin/demo-data"
          element={
            <RequireRole allowed={["city_admin", "superuser"]}>
              <PageShell><DemoDataAdminPage /></PageShell>
            </RequireRole>
          }
        />

        {/* Authority */}
        <Route
          path="/operations"
          element={
            <RequireRole allowed={["department_staff", "city_admin", "superuser", "emergency_responder"]}>
              <PageShell><AuthorityDashboard /></PageShell>
            </RequireRole>
          }
        />
        <Route
          path="/queue"
          element={
            <RequireRole allowed={["department_staff", "city_admin", "superuser", "emergency_responder"]}>
              <PageShell><IncidentQueuePage /></PageShell>
            </RequireRole>
          }
        />
        <Route
          path="/analytics"
          element={
            <RequireRole allowed={["department_staff", "city_admin", "superuser"]}>
              <PageShell><AnalyticsPage /></PageShell>
            </RequireRole>
          }
        />
        <Route
          path="/admin/users"
          element={
            <RequireRole allowed={["city_admin", "superuser"]}>
              <PageShell><UserManagementPage /></PageShell>
            </RequireRole>
          }
        />
        <Route
          path="/admin/audit"
          element={
            <RequireRole allowed={["city_admin", "superuser"]}>
              <PageShell><AuditLogsPage /></PageShell>
            </RequireRole>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}