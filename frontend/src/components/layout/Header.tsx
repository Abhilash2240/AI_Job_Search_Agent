import React, { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  UploadCloud,
  RefreshCw,
  Cpu,
  CheckCircle,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { useCandidate } from '../../context/CandidateContext';
import { api } from '../../services/api';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  onToggleMobileMenu?: () => void;
  onToggleCollapse?: () => void;
  isSidebarCollapsed?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  onToggleMobileMenu,
  onToggleCollapse,
  isSidebarCollapsed = false,
}) => {
  const { candidateId, setCandidateId, setCandidateData, addToast, refreshCandidate } = useCandidate();
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
      addToast('error', 'Only PDF and DOCX resume formats are supported.');
      return;
    }

    try {
      setIsUploading(true);
      addToast('info', `Uploading & parsing ${file.name}...`);
      const res = await api.uploadResume(file);
      setCandidateId(res.candidate_id);
      setCandidateData(res);
      await queryClient.invalidateQueries();
      addToast('success', `Resume parsed successfully! Active Candidate #${res.candidate_id}`);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Upload failed';
      addToast('error', `Failed to parse resume: ${msg}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refreshCandidate();
      await queryClient.invalidateQueries();
      addToast('info', 'Refreshed candidate profile, recommendations, and dashboard.');
    } catch (err) {
      addToast('error', 'Failed to refresh candidate.');
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between z-10 flex-shrink-0 gap-3">
      {/* Left: Toggles and Page Titles */}
      <div className="flex items-center min-w-0 flex-1">
        {/* Mobile Hamburger Menu Toggle */}
        <button
          onClick={onToggleMobileMenu}
          className="md:hidden p-2 -ml-1 mr-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors flex-shrink-0"
          title="Open navigation menu"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Desktop Sidebar Collapse Toggle */}
        <button
          onClick={onToggleCollapse}
          className="hidden md:flex p-1.5 -ml-1 mr-3 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-colors flex-shrink-0"
          title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label="Toggle sidebar collapse"
        >
          {isSidebarCollapsed ? <PanelLeftOpen className="w-5 h-5" /> : <PanelLeftClose className="w-5 h-5" />}
        </button>

        <div className="min-w-0 flex-1">
          <h1 className="text-base sm:text-lg font-bold text-slate-800 tracking-tight leading-tight truncate">
            {title || 'AI Career Discovery'}
          </h1>
          {subtitle && (
            <p className="hidden md:block text-xs text-slate-500 font-medium truncate mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {/* Right: Actions & Indicators */}
      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
        {/* SBERT model status pill */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200/60 flex-shrink-0">
          <Cpu className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
          <span>SBERT Engine Ready</span>
        </div>

        {/* Candidate ID indicator */}
        {candidateId && (
          <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 flex-shrink-0">
            <CheckCircle className="w-3.5 h-3.5 text-indigo-600" />
            <span>ID #{candidateId}</span>
          </div>
        )}

        {/* Refresh button */}
        <button
          onClick={handleManualRefresh}
          disabled={isRefreshing}
          title="Reload candidate data"
          className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors disabled:opacity-50 flex-shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-indigo-600' : ''}`} />
        </button>

        {/* Hidden File Input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileUpload}
          accept=".pdf,.docx"
          className="hidden"
        />

        {/* Upload Resume Button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50 flex-shrink-0"
        >
          <UploadCloud className={`w-4 h-4 ${isUploading ? 'animate-bounce' : ''}`} />
          <span className="hidden sm:inline">{isUploading ? 'Parsing Resume...' : 'Upload Resume'}</span>
          <span className="sm:hidden">{isUploading ? '...' : 'Upload'}</span>
        </button>
      </div>
    </header>
  );
};
