import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  User,
  Sparkles,
  CheckCircle2,
  Settings,
  Briefcase,
  Bookmark,
  ClipboardList,
  Building2,
  Activity,
  Compass,
  FileText,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useCandidate } from '../../context/CandidateContext';

interface SidebarProps {
  isCollapsed?: boolean;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed = false,
  isMobileOpen = false,
  onCloseMobile,
  onToggleCollapse,
}) => {
  const { candidateData, candidateId, selectedRoles } = useCandidate();

  const navItems = [
    {
      name: 'Dashboard',
      to: '/',
      icon: LayoutDashboard,
    },
    {
      name: 'Job Feed & Matches',
      to: '/jobs',
      icon: Compass,
      badge: 'Live',
    },
    {
      name: 'Saved Jobs',
      to: '/saved-jobs',
      icon: Bookmark,
    },
    {
      name: 'Application Tracker',
      to: '/applications',
      icon: ClipboardList,
    },
    {
      name: 'Company Research',
      to: '/companies',
      icon: Building2,
    },
    {
      name: 'Career Roles',
      to: '/recommendations',
      icon: Sparkles,
      badge: 'SBERT',
    },
    {
      name: 'Confirmed Roles',
      to: '/selected-roles',
      icon: CheckCircle2,
      count: selectedRoles.length,
    },
    {
      name: 'Candidate Profile',
      to: '/profile',
      icon: User,
    },
    {
      name: 'Pipeline & Automation',
      to: '/pipeline',
      icon: Activity,
    },
    {
      name: 'Settings',
      to: '/settings',
      icon: Settings,
    },
  ];

  const candidateName = candidateData?.profile?.personal?.name || `Candidate #${candidateId || '1'}`;
  const candidateEmail = candidateData?.profile?.personal?.email || 'No email provided';

  const renderContent = (collapsed: boolean, isMobileDrawer: boolean) => (
    <div className="flex flex-col h-full overflow-hidden select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 flex-shrink-0">
            <Briefcase className="w-5 h-5" />
          </div>
          {!collapsed && (
            <div className="min-w-0 truncate">
              <span className="font-bold text-slate-100 text-sm sm:text-base tracking-tight block truncate">
                AI Job Search Agent
              </span>
              <span className="text-[10px] text-indigo-400 font-semibold uppercase tracking-wider block">
                Production Engine
              </span>
            </div>
          )}
        </div>

        {/* Mobile close button */}
        {isMobileDrawer && (
          <button
            onClick={onCloseMobile}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {!collapsed && (
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-3 mb-2">
            Navigation
          </div>
        )}
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={isMobileDrawer ? onCloseMobile : undefined}
              title={collapsed ? item.name : undefined}
              className={({ isActive }) =>
                `flex items-center ${
                  collapsed ? 'justify-center px-2 py-3' : 'justify-between px-3 py-2.5'
                } rounded-xl text-sm font-medium transition-all group relative ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <div className="flex items-center gap-3 min-w-0">
                <Icon className="w-4 h-4 flex-shrink-0" />
                {!collapsed && <span className="truncate">{item.name}</span>}
              </div>

              {!collapsed && (
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-indigo-500/30 text-indigo-300 rounded border border-indigo-400/20">
                      {item.badge}
                    </span>
                  )}
                  {typeof item.count === 'number' && item.count > 0 && (
                    <span className="px-2 py-0.5 text-xs font-bold bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30">
                      {item.count}
                    </span>
                  )}
                </div>
              )}

              {/* Floating tooltip for collapsed desktop mode */}
              {collapsed && (
                <span className="hidden md:group-hover:flex absolute left-full ml-3 px-2.5 py-1 bg-slate-950 text-white text-xs font-medium rounded-lg shadow-lg whitespace-nowrap z-50 pointer-events-none items-center gap-1.5 border border-slate-700">
                  {item.name}
                  {item.badge && (
                    <span className="text-[9px] px-1 bg-indigo-500/40 text-indigo-300 rounded">
                      {item.badge}
                    </span>
                  )}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Candidate Profile Footer */}
      <div className="p-3 border-t border-slate-800 flex-shrink-0">
        <div className={`bg-slate-800/70 rounded-xl p-2.5 border border-slate-700/60 ${collapsed ? 'flex justify-center' : ''}`}>
          <div className="flex items-center gap-3 min-w-0">
            <div
              title={`${candidateName} (${candidateEmail})`}
              className="w-8 h-8 rounded-full bg-indigo-600/30 text-indigo-300 flex items-center justify-center font-bold text-xs uppercase flex-shrink-0 border border-indigo-500/30"
            >
              {candidateName.charAt(0) || 'C'}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-slate-200 truncate">{candidateName}</p>
                <p className="text-[11px] text-slate-400 truncate">{candidateEmail}</p>
              </div>
            )}
          </div>
          {!collapsed && candidateData?.filename && (
            <div className="mt-2 pt-2 border-t border-slate-700/60 flex items-center gap-1.5 text-[11px] text-slate-400 truncate">
              <FileText className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
              <span className="truncate">{candidateData.filename}</span>
            </div>
          )}
        </div>

        {/* Desktop Collapse Toggle */}
        {!isMobileDrawer && onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="hidden md:flex w-full items-center justify-center gap-2 mt-2 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded-lg transition"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span>Collapse Sidebar</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Drawer (Only visible on small screens when isMobileOpen is true) */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          {/* Dark Backdrop */}
          <div
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          {/* Sliding Drawer */}
          <aside className="relative z-10 w-72 max-w-[85vw] bg-slate-900 text-slate-200 flex flex-col h-full shadow-2xl border-r border-slate-800">
            {renderContent(false, true)}
          </aside>
        </div>
      )}

      {/* Desktop & Tablet In-Flow Sidebar (In regular flex flow, NEVER fixed, NEVER overlaps content) */}
      <aside
        className={`
          hidden md:flex flex-col flex-shrink-0 bg-slate-900 text-slate-200 border-r border-slate-800 select-none
          h-full transition-all duration-300 ease-in-out z-20
          ${isCollapsed ? 'w-20' : 'w-64'}
        `}
      >
        {renderContent(isCollapsed, false)}
      </aside>
    </>
  );
};
