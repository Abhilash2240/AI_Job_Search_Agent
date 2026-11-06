import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2,
  Trash2,
  Plus,
  ArrowLeft,
  Sparkles,
  Check,
  HelpCircle,
  Briefcase,
  FileCheck,
} from 'lucide-react';
import { useCandidate } from '../context/CandidateContext';
import { api } from '../services/api';
import { ScoreBadge } from '../components/common/ScoreBadge';
import { CustomRoleModal } from '../components/roles/CustomRoleModal';
import { ConfirmedRoleItem } from '../types/api';

export const SelectedRolesPage: React.FC = () => {
  const { candidateId, selectedRoles, toggleSelectRole, deselectAllRoles, addToast } = useCandidate();
  const queryClient = useQueryClient();
  const [isCustomModalOpen, setIsCustomModalOpen] = useState(false);
  const [confirmedAtTimestamp, setConfirmedAtTimestamp] = useState<string | null>(null);

  // Fetch confirmed roles from backend
  const { data: dbConfirmed } = useQuery({
    queryKey: ['confirmedRoles', candidateId],
    queryFn: async () => {
      if (!candidateId) return null;
      const res = await api.getConfirmedRoles(candidateId);
      if (res.confirmed_at) {
        setConfirmedAtTimestamp(res.confirmed_at);
      }
      return res;
    },
    enabled: !!candidateId,
  });

  // Save/Confirm mutation
  const saveMutation = useMutation({
    mutationFn: () => {
      if (!candidateId) throw new Error('No candidate ID');
      return api.saveConfirmedRoles(candidateId, selectedRoles);
    },
    onSuccess: (data) => {
      setConfirmedAtTimestamp(data.confirmed_at);
      queryClient.setQueryData(['confirmedRoles', candidateId], data);
      queryClient.invalidateQueries({ queryKey: ['confirmedRoles', candidateId] });
      addToast('success', `Confirmed and saved ${selectedRoles.length} target career roles!`);
    },
    onError: (err: any) => {
      addToast('error', `Failed to save confirmed roles: ${err.message}`);
    },
  });

  // Delete single role mutation (if saved in DB)
  const deleteMutation = useMutation({
    mutationFn: (roleId: string) => {
      if (!candidateId) throw new Error('No candidate ID');
      return api.deleteConfirmedRole(candidateId, roleId);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['confirmedRoles', candidateId], data);
      queryClient.invalidateQueries({ queryKey: ['confirmedRoles', candidateId] });
      addToast('info', 'Role removed from confirmed list.');
    },
  });

  const handleRemoveRole = (role: ConfirmedRoleItem) => {
    toggleSelectRole(role);
    if (dbConfirmed?.confirmed) {
      deleteMutation.mutate(role.role_id);
    }
  };

  // Aggregated skills calculations
  const aggregatedMatchingSkills = Array.from(
    new Set(selectedRoles.flatMap((r) => r.matching_skills || []))
  );

  const aggregatedMissingSkills = Array.from(
    new Set(selectedRoles.flatMap((r) => r.missing_skills || []))
  ).filter((skill) => !aggregatedMatchingSkills.includes(skill));

  if (selectedRoles.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center max-w-xl mx-auto my-8 shadow-xs">
        <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mx-auto mb-4">
          <Briefcase className="w-7 h-7" />
        </div>
        <h3 className="text-lg font-bold text-slate-800">No Career Roles Selected</h3>
        <p className="text-xs text-slate-500 mt-1.5 mb-6 max-w-sm mx-auto leading-relaxed">
          You haven't selected any career roles yet. Review your SBERT recommendations or add a custom role to build your target list.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            to="/recommendations"
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition-all shadow-sm"
          >
            <Sparkles className="w-4 h-4" />
            <span>Browse Recommendations</span>
          </Link>
          <button
            onClick={() => setIsCustomModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold border border-slate-200 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Custom Role</span>
          </button>
        </div>
        <CustomRoleModal
          isOpen={isCustomModalOpen}
          onClose={() => setIsCustomModalOpen(false)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Link
              to="/recommendations"
              className="text-slate-400 hover:text-slate-700 p-1 rounded-md hover:bg-slate-100"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h2 className="text-xl font-bold text-slate-900">Confirm Target Career Roles</h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 ml-7">
            Review and finalize the career paths you want the AI Job Search Agent to track.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setIsCustomModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 rounded-lg border border-slate-200 shadow-2xs transition-all"
          >
            <Plus className="w-4 h-4 text-indigo-600" />
            <span>Add Custom Role</span>
          </button>

          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-1.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm transition-all disabled:opacity-50"
          >
            <FileCheck className="w-4 h-4" />
            <span>{saveMutation.isPending ? 'Saving...' : 'Confirm & Save Selection'}</span>
          </button>
        </div>
      </div>

      {/* Confirmation Status Banner (if confirmed in DB) */}
      {confirmedAtTimestamp && (
        <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 flex items-center justify-between gap-3 text-xs text-emerald-900">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <div>
              <p className="font-bold text-emerald-900">Career Roles Confirmed & Persisted</p>
              <p className="text-[11px] text-emerald-700">
                Saved in candidate profile at {new Date(confirmedAtTimestamp).toLocaleString()}
              </p>
            </div>
          </div>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-200/60 text-emerald-900 border border-emerald-300">
            Active Target Set
          </span>
        </div>
      )}

      {/* Selected Roles List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs text-slate-500 font-medium px-1">
          <span>{selectedRoles.length} Roles Selected</span>
          <button
            onClick={deselectAllRoles}
            className="text-rose-600 hover:text-rose-700 hover:underline"
          >
            Clear All
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {selectedRoles.map((role) => (
            <div
              key={role.role_id}
              className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-slate-300 transition-colors"
            >
              <div className="flex items-start gap-3 flex-1">
                <div
                  className={`p-2 rounded-xl flex-shrink-0 ${
                    role.is_custom
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-indigo-100 text-indigo-700'
                  }`}
                >
                  <Briefcase className="w-5 h-5" />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-bold text-base text-slate-900">{role.role_title}</h4>
                    {role.is_custom ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                        Custom Role
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                        SBERT Recommendation
                      </span>
                    )}
                  </div>

                  {role.custom_description && (
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                      {role.custom_description}
                    </p>
                  )}

                  {/* Skills tags */}
                  <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                    {role.matching_skills.slice(0, 4).map((s, idx) => {
                      const name = typeof s === 'string' ? s : ((s as any)?.skill_name || (s as any)?.canonical_name || 'Skill');
                      return (
                        <span
                          key={idx}
                          className="px-2 py-0.5 text-[10px] font-medium bg-emerald-50 text-emerald-700 rounded border border-emerald-200/80"
                        >
                          {name}
                        </span>
                      );
                    })}
                    {role.matching_skills.length > 4 && (
                      <span className="text-[10px] text-slate-400">
                        +{role.matching_skills.length - 4} matching
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Right side match & delete */}
              <div className="flex items-center gap-4 self-end sm:self-center">
                {role.composite_match_score !== null &&
                  role.composite_match_score !== undefined && (
                    <div className="text-right">
                      <ScoreBadge score={role.composite_match_score} size="md" />
                      <span className="text-[10px] text-slate-400 block mt-0.5">Match Score</span>
                    </div>
                  )}

                <button
                  onClick={() => handleRemoveRole(role)}
                  className="p-2 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                  title="Remove role from selection"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Aggregate Profile Analysis Across Selected Roles */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Core Strengths */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs">
          <div className="flex items-center gap-2 mb-3">
            <Check className="w-4 h-4 text-emerald-600" />
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Candidate Core Strengths ({aggregatedMatchingSkills.length})
            </h4>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Skills supported by your verified experience that directly empower your selected career roles.
          </p>
          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto">
            {aggregatedMatchingSkills.map((s, idx) => {
              const name = typeof s === 'string' ? s : ((s as any)?.skill_name || (s as any)?.canonical_name || 'Skill');
              return (
                <span
                  key={idx}
                  className="px-2.5 py-1 text-xs font-medium bg-emerald-50 text-emerald-800 rounded-md border border-emerald-200"
                >
                  {name}
                </span>
              );
            })}
          </div>
        </div>

        {/* Actionable Upskilling Focus */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs">
          <div className="flex items-center gap-2 mb-3">
            <HelpCircle className="w-4 h-4 text-slate-500" />
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Recommended Focus Areas ({aggregatedMissingSkills.length})
            </h4>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Skills frequently sought across your selected roles that were not found in your current resume.
          </p>
          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto">
            {aggregatedMissingSkills.map((s, idx) => {
              const name = typeof s === 'string' ? s : ((s as any)?.skill_name || (s as any)?.canonical_name || 'Skill');
              return (
                <span
                  key={idx}
                  className="px-2.5 py-1 text-xs font-normal bg-slate-100 text-slate-600 rounded-md border border-slate-200"
                >
                  {name}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Final Action Bar */}
      <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-bold text-slate-800">Ready to save your target career roles?</h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Your selected career roles will guide Phase 4 automated job discovery and relevance filtering.
          </p>
        </div>

        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-sm transition-all disabled:opacity-50"
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>{saveMutation.isPending ? 'Saving...' : 'Confirm Career Role Selection'}</span>
        </button>
      </div>

      {/* Custom Role Modal */}
      <CustomRoleModal
        isOpen={isCustomModalOpen}
        onClose={() => setIsCustomModalOpen(false)}
      />
    </div>
  );
};
