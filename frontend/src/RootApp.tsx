import { Navigate, Route, Routes } from "react-router-dom";
import { Spin } from "antd";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { AppLayout } from "./components/AppLayout";
import { AccountsPage } from "./pages/AccountsPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { CostsPage } from "./pages/CostsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EvaluationsPage } from "./pages/EvaluationsPage";
import { LoginPage } from "./pages/LoginPage";
import { OperationsPlatformsPage } from "./pages/OperationsPlatformsPage";
import { ProxyPoolsPage } from "./pages/ProxyPoolsPage";
import { PurchasesPage } from "./pages/PurchasesPage";
import { ReportsPage } from "./pages/ReportsPage";
import { RevenuesPage } from "./pages/RevenuesPage";
import { ServersPage } from "./pages/ServersPage";
import { ShopMonitorsPage } from "./pages/ShopMonitorsPage";
import { Sub2APIInstancesPage } from "./pages/Sub2APIInstancesPage";
import { SuppliersPage } from "./pages/SuppliersPage";
import { SystemMaintenancePage } from "./pages/SystemMaintenancePage";
import { UsersPage } from "./pages/UsersPage";

function ProtectedApp() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "grid", minHeight: "100vh", placeItems: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/suppliers" element={<SuppliersPage />} />
        <Route path="/purchases" element={<PurchasesPage />} />
        <Route path="/accounts" element={<AccountsPage />} />
        <Route path="/sub2api-instances" element={<Sub2APIInstancesPage />} />
        <Route path="/operations-platforms" element={<OperationsPlatformsPage />} />
        <Route path="/servers" element={<ServersPage />} />
        <Route path="/proxy-pools" element={<ProxyPoolsPage />} />
        <Route path="/shop-monitors" element={<ShopMonitorsPage />} />
        <Route path="/evaluations" element={<EvaluationsPage />} />
        <Route path="/revenues" element={<RevenuesPage />} />
        <Route path="/costs" element={<CostsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/audit-logs" element={<AuditLogsPage />} />
        <Route path="/system-maintenance" element={<SystemMaintenancePage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  );
}

function PublicLogin() {
  const { user, loading } = useAuth();
  if (loading) {
    return null;
  }
  if (user) {
    return <Navigate to="/" replace />;
  }
  return <LoginPage />;
}

export function RootApp() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<PublicLogin />} />
        <Route path="/*" element={<ProtectedApp />} />
      </Routes>
    </AuthProvider>
  );
}
