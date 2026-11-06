import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { ToastContainer } from './components/common/Toast';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { DashboardPage } from './pages/DashboardPage';
import { ProfilePage } from './pages/ProfilePage';
import { CareerRecommendationsPage } from './pages/CareerRecommendationsPage';
import { SelectedRolesPage } from './pages/SelectedRolesPage';
import { JobFeedPage } from './pages/JobFeedPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { SavedJobsPage } from './pages/SavedJobsPage';
import { ApplicationTrackerPage } from './pages/ApplicationTrackerPage';
import { CompanyResearchPage } from './pages/CompanyResearchPage';
import { PipelineMonitorPage } from './pages/PipelineMonitorPage';
import { SettingsPage } from './pages/SettingsPage';

const AppLayout: React.FC = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = React.useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const location = useLocation();

  // Automatically close mobile navigation drawer upon route transition
  React.useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const getPageInfo = () => {
    const path = location.pathname;
    if (path === '/') {
      return {
        title: 'Candidate Career Dashboard',
        subtitle: 'Profile completeness, skill evidence, and fine-tuned SBERT career intelligence',
      };
    }
    if (path === '/profile') {
      return {
        title: 'Candidate Profile & Validation',
        subtitle: 'Detailed parsed sections, entropy checks, and structured resume information',
      };
    }
    if (path === '/recommendations') {
      return {
        title: 'Fine-Tuned SBERT Career Role Recommendations',
        subtitle: 'Multi-objective hybrid matching across top engineering and tech roles',
      };
    }
    if (path === '/selected-roles') {
      return {
        title: 'Selected Career Target Roles',
        subtitle: 'Review, finalize, and confirm your targeted roles for intelligent job discovery',
      };
    }
    if (path === '/jobs') {
      return {
        title: 'Verified Job Postings Feed',
        subtitle: 'Browse canonical vacancies ranked with SBERT match scores & eligibility',
      };
    }
    if (path.startsWith('/jobs/')) {
      return {
        title: 'Job Vacancy Details & Match Analysis',
        subtitle: 'In-depth SBERT semantic breakdown, verified requirements, and application link',
      };
    }
    if (path === '/saved-jobs') {
      return {
        title: 'Saved & Bookmarked Vacancies',
        subtitle: 'Track prospective vacancies with status monitoring and personal notes',
      };
    }
    if (path === '/applications') {
      return {
        title: 'Candidate Application Tracker',
        subtitle: 'Manage candidate applications across interview stages with status tracking',
      };
    }
    if (path === '/companies') {
      return {
        title: 'Company Research & Sourcing Channels',
        subtitle: 'Verified employers, ATS portals, contact points, and outreach authorization',
      };
    }
    if (path === '/pipeline') {
      return {
        title: 'Data Ingestion & Pipeline Orchestration',
        subtitle: 'Monitor discovery, extraction, deduplication, vector storage, and matching runs',
      };
    }
    if (path === '/settings') {
      return {
        title: 'Application & Model Settings',
        subtitle: 'Fine-tuned SBERT hyperparameters, scoring matrix, and candidate management',
      };
    }
    return {
      title: 'AI Job Search Agent',
      subtitle: 'Intelligent Career Intelligence & Matching Platform',
    };
  };

  const { title, subtitle } = getPageInfo();

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden font-sans">
      {/* Responsive In-Flow Sidebar & Mobile Drawer */}
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        isMobileOpen={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* Main Content Layout Container */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header
          title={title}
          subtitle={subtitle}
          onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          isSidebarCollapsed={isSidebarCollapsed}
        />
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-3.5 sm:p-5 md:p-8 min-w-0">
          <div className="max-w-7xl mx-auto w-full min-w-0">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/recommendations" element={<CareerRecommendationsPage />} />
                <Route path="/selected-roles" element={<SelectedRolesPage />} />
                <Route path="/jobs" element={<JobFeedPage />} />
                <Route path="/jobs/:id" element={<JobDetailPage />} />
                <Route path="/saved-jobs" element={<SavedJobsPage />} />
                <Route path="/applications" element={<ApplicationTrackerPage />} />
                <Route path="/companies" element={<CompanyResearchPage />} />
                <Route path="/pipeline" element={<PipelineMonitorPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ErrorBoundary>
          </div>
        </main>
      </div>
      <ToastContainer />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
};

export default App;
