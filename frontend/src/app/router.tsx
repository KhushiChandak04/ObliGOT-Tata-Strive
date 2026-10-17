import SignInPage from "../pages/SignInPage";
import { Navigate, Route, Routes } from "react-router-dom";
import DashboardPage from "../pages/DashboardPage";
import PartnersPage from "../pages/PartnersPage";
import PartnerDetailsPage from "../pages/PartnerDetailsPage";
import PipelinePage from "../pages/PipelinePage";
import AgreementsPage from "../pages/AgreementsPage";
import ProjectsPage from "../pages/ProjectsPage";
import FinancePage from "../pages/FinancePage";
import ReportsPage from "../pages/ReportsPage";
import ActionCenterPage from "../pages/ActionCenterPage";
import ImportPage from "../pages/ImportPage";
export default function AppRouter() {
  return <Routes>
      <Route path="/signin" element={<SignInPage />} />
    <Route path="/" element={<DashboardPage />} />
    <Route path="/partners" element={<PartnersPage />} />
    <Route path="/partners/:partnerId" element={<PartnerDetailsPage />} />
    <Route path="/pipeline" element={<PipelinePage />} />
    <Route path="/agreements" element={<AgreementsPage />} />
    <Route path="/projects" element={<ProjectsPage />} />
    <Route path="/finance" element={<FinancePage />} />
    <Route path="/reports" element={<ReportsPage />} />
    <Route path="/actions" element={<ActionCenterPage />} />
    <Route path="/import" element={<ImportPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}
