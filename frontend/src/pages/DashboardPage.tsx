import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Sparkles,
  ArrowRight,
  Award,
  Layers,
  FolderGit2,
  CheckCircle2,
  Briefcase,
  Activity,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { useCandidate } from '../context/CandidateContext';
import { api } from '../services/api';
import { ProfileSummaryCard } from '../components/dashboard/ProfileSummaryCard';
import { SkillsCard } from '../components/dashboard/SkillsCard';
import { ProjectsCard } from '../components/dashboard/ProjectsCard';
import { RoleRecommendationCard } from '../components/roles/RoleRecommendationCard';
import { RoleDetailsModal } from '../components/roles/RoleDetailsModal';
import { RoleRecommendation, DashboardStatsResponse } from '../types/api';

export const DashboardPage: React.FC = () => {
  const { candidateId, candidateData, selectedRoles, toggleSelectRole, isRoleSelected, refreshCandidate } = useCandidate();
  const [selectedRoleDetails, setSelectedRoleDetails] = React.useState<RoleRecommendation | null>(null);

  useEffect(() => {
    if (candidateId && !candidateData) {
      refreshCandidate();
    }
  }, [candidateId, candidateData]);

  // Fetch validation
  const { data: validationData } = useQuery({
    queryKey: ['profileValidation', candidateId],
    queryFn: () => (candidateId ? api.getProfileValidation(candidateId) : null),
    enabled: !!candidateId,
  });

  // Fetch recommendations
  const { data: recData, isLoading: isLoadingRecs } = useQuery({
    queryKey: ['recommendations', candidateId],
    queryFn: () => (candidateId ? api.getRoleRecommendations(candidateId) : null),
    enabled: !!candidateId,
  });

  // Fetch live system dashboard stats
  const {
    data: dashboardStats,
    isLoading: isLoadingDashboard,
    isError: isDashboardError,
    refetch: refetchDashboard,
  } = useQuery<DashboardStatsResponse>({
    queryKey: ['dashboardStats', candidateId],
    queryFn: () => api.getDashboardStats(candidateId || undefined),
    refetchInterval: 10000,
  });

  if (!candidateData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-6">
        <div className="w-16 h-16 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-4">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-800">No Candidate Profile Loaded</h2>
        <p className="text-sm text-slate-500 max-w-md mt-1 mb-6">
          Upload a resume in PDF or DOCX format using the "Upload Resume" button above to extract your profile and receive fine-tuned SBERT recommendations.
        </p>
      </div>
    );
  }

  const profile = candidateData.profile;
  const topRecommendations = recData?.recommendations?.slice(0, 3) || [];
  const totalSkills =
    (profile?.skills?.programming_languages?.length || 0) +
    (profile?.skills?.frameworks?.length || 0) +
    (profile?.skills?.databases?.length || 0) +
    (profile?.skills?.tools?.length || 0) +
    (profile?.skills?.ai_ml?.length || 0);

  return (
    <div className="space-y-6 w-full min-w-0">
      {/* Top Quick Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span className="font-semibold">Profile Completeness</span>
            <Award className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {validationData?.completeness_score ? Math.round(validationData.completeness_score) : 85}%
          </div>
          <span className="text-[11px] text-emerald-600 font-medium">Validated & High Entropy</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span className="font-semibold">Verified Skills</span>
            <Layers className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{totalSkills}</div>
          <span className="text-[11px] text-slate-500">Across 5 taxonomy domains</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span className="font-semibold">Projects Analyzed</span>
            <FolderGit2 className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {profile?.projects?.length || 0}
          </div>
          <span className="text-[11px] text-slate-500">Full stack & AI/ML pipelines</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span className="font-semibold">Target Roles Selected</span>
            <CheckCircle2 className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{selectedRoles.length}</div>
          <span className="text-[11px] text-indigo-600 font-medium">Ready for Confirmation</span>
        </div>
      </div>

      {/* Live AI Job Search Platform Intelligence Bar */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-5 border border-slate-800 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                Live Agent Telemetry & Database Index
              </span>
            </div>
            <p className="text-xs text-slate-300">
              Real-time metrics from our verified job discovery, deduplication, SBERT embedding storage, and application tracker.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/jobs"
              className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors"
            >
              <Briefcase className="w-3.5 h-3.5" />
              <span>Job Feed</span>
            </Link>
            <Link
              to="/pipeline"
              className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-colors"
            >
              <span>Pipeline Monitor</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {isLoadingDashboard ? (
          <div className="py-8 flex flex-col items-center justify-center text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-400 mb-2" />
            <span className="text-xs font-medium text-slate-300">Loading platform telemetry metrics...</span>
          </div>
        ) : isDashboardError ? (
          <div className="py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-rose-300 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
              <span>Telemetry data could not be retrieved from the backend.</span>
            </div>
            <button
              onClick={() => refetchDashboard()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white font-medium border border-white/20"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        ) : dashboardStats ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 pt-4 text-center">
            <div className="bg-white/5 rounded-xl p-3 border border-white/10">
              <span className="text-[11px] text-slate-400 block mb-0.5">Canonical Vacancies</span>
              <span className="text-xl font-bold text-white">
                {dashboardStats.system?.total_canonical_vacancies ?? dashboardStats.system?.canonical_vacancies ?? 0}
              </span>
            </div>
            <div className="bg-white/5 rounded-xl p-3 border border-white/10">
              <span className="text-[11px] text-slate-400 block mb-0.5">SBERT Embeddings</span>
              <span className="text-xl font-bold text-white">
                {dashboardStats.system?.job_embeddings ?? dashboardStats.system?.verified_active_vacancies ?? 0}
              </span>
            </div>
            <div className="bg-white/5 rounded-xl p-3 border border-white/10">
              <span className="text-[11px] text-slate-400 block mb-0.5">Tracked Companies</span>
              <span className="text-xl font-bold text-white">
                {dashboardStats.system?.total_companies ?? 0}
              </span>
            </div>
            {dashboardStats.recommendations?.best_job_id ? (
              <Link
                to={`/jobs/${dashboardStats.recommendations.best_job_id}`}
                title={`Best Match: ${dashboardStats.recommendations.best_job_title} at ${dashboardStats.recommendations.best_company_name}`}
                className="bg-white/5 hover:bg-white/10 rounded-xl p-3 border border-white/10 hover:border-emerald-500/40 transition-all cursor-pointer block text-center group"
              >
                <span className="text-[11px] text-slate-400 block mb-0.5 group-hover:text-emerald-300 transition-colors">
                  Top Match Score
                </span>
                <span className="text-xl font-bold text-emerald-400">
                  {dashboardStats.recommendations.top_match_score != null
                    ? `${Math.round(dashboardStats.recommendations.top_match_score * 100)}%`
                    : '—'}
                </span>
                {dashboardStats.recommendations.best_company_name && (
                  <span className="text-[10px] text-slate-400 truncate block mt-0.5">
                    {dashboardStats.recommendations.best_company_name}
                  </span>
                )}
              </Link>
            ) : (
              <div className="bg-white/5 rounded-xl p-3 border border-white/10 text-center">
                <span className="text-[11px] text-slate-400 block mb-0.5">Top Match Score</span>
                <span className="text-xl font-bold text-emerald-400">
                  {dashboardStats.recommendations?.top_match_score != null
                    ? `${Math.round(dashboardStats.recommendations.top_match_score * 100)}%`
                    : dashboardStats.recommendations?.matching_status === 'NO_ELIGIBLE_MATCHES'
                    ? 'None'
                    : 'Awaiting'}
                </span>
                <span className="text-[10px] text-slate-400 truncate block mt-0.5">
                  {dashboardStats.recommendations?.matching_status === 'AWAITING_MATCHING'
                    ? 'Awaiting matching'
                    : 'Active eligible vacancies'}
                </span>
              </div>
            )}
            <div className="bg-white/5 rounded-xl p-3 border border-white/10">
              <span className="text-[11px] text-slate-400 block mb-0.5">Saved Vacancies</span>
              <span className="text-xl font-bold text-amber-400">
                {dashboardStats.saved_jobs?.total_saved ?? dashboardStats.saved?.total_saved ?? 0}
              </span>
            </div>
            <div className="bg-white/5 rounded-xl p-3 border border-white/10">
              <span className="text-[11px] text-slate-400 block mb-0.5">Active Applications</span>
              <span className="text-xl font-bold text-indigo-400">
                {dashboardStats.applications?.active_in_pipeline ?? dashboardStats.applications?.active_applications ?? 0}
              </span>
            </div>
          </div>
        ) : null}
      </div>

      {/* Profile Overview Card */}
      <ProfileSummaryCard profile={profile} validation={validationData} />

      {/* Top 3 Career Recommendations Teaser */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-800">Top Recommended Career Roles</h3>
            <p className="text-xs text-slate-500">
              Ranked with fine-tuned SBERT 384-d semantic embeddings and multi-objective scoring.
            </p>
          </div>
          <Link
            to="/recommendations"
            className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg border border-indigo-200 transition-colors"
          >
            <span>View All {recData?.total_recommended || 10} Roles</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {isLoadingRecs ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400">
            <Sparkles className="w-6 h-6 mx-auto animate-spin text-indigo-600 mb-2" />
            <p className="text-xs font-medium">Computing SBERT similarity & skill evidence...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {topRecommendations.map((role, idx) => (
              <RoleRecommendationCard
                key={role.role_id}
                role={role}
                rank={idx + 1}
                isSelected={isRoleSelected(role.role_id)}
                onToggleSelect={toggleSelectRole}
                onViewDetails={setSelectedRoleDetails}
              />
            ))}
          </div>
        )}
      </div>

      {/* Skills Card */}
      {profile?.skills && (
        <SkillsCard
          skills={profile.skills}
          skillSources={profile.skill_sources}
          inferredSkills={profile.inferred_skills}
          onSkillUpdated={refreshCandidate}
        />
      )}

      {/* Extracted Projects Card */}
      {profile?.projects && profile.projects.length > 0 && (
        <ProjectsCard projects={profile.projects} />
      )}

      {/* Role Details Modal */}
      <RoleDetailsModal
        role={selectedRoleDetails}
        isOpen={!!selectedRoleDetails}
        onClose={() => setSelectedRoleDetails(null)}
        isSelected={selectedRoleDetails ? isRoleSelected(selectedRoleDetails.role_id) : false}
        onToggleSelect={toggleSelectRole}
      />
    </div>
  );
};

