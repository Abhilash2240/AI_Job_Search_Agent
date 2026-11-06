import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
  Search,
  CheckSquare,
  Square,
  Plus,
  RefreshCw,
  ArrowRight,
  Filter,
  SlidersHorizontal,
} from 'lucide-react';
import { useCandidate } from '../context/CandidateContext';
import { api } from '../services/api';
import { RoleRecommendationCard } from '../components/roles/RoleRecommendationCard';
import { RoleDetailsModal } from '../components/roles/RoleDetailsModal';
import { CustomRoleModal } from '../components/roles/CustomRoleModal';
import { RoleRecommendation, ConfirmedRoleItem } from '../types/api';

export const CareerRecommendationsPage: React.FC = () => {
  const {
    candidateId,
    selectedRoles,
    toggleSelectRole,
    selectAllRoles,
    deselectAllRoles,
    isRoleSelected,
    addToast,
  } = useCandidate();

  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'composite' | 'sbert' | 'skills' | 'projects'>('composite');
  const [selectedRoleDetails, setSelectedRoleDetails] = useState<RoleRecommendation | null>(null);
  const [isCustomRoleOpen, setIsCustomRoleOpen] = useState(false);

  // Fetch recommendations
  const { data: recData, isLoading, isFetching } = useQuery({
    queryKey: ['recommendations', candidateId],
    queryFn: () => (candidateId ? api.getRoleRecommendations(candidateId) : null),
    enabled: !!candidateId,
  });

  // Re-generate recommendations mutation
  const regenerateMutation = useMutation({
    mutationFn: () => (candidateId ? api.generateRoleRecommendations(candidateId, 10) : Promise.reject()),
    onSuccess: (data) => {
      queryClient.setQueryData(['recommendations', candidateId], data);
      addToast('success', 'Recalculated recommendations with fine-tuned SBERT!');
    },
    onError: (err: any) => {
      addToast('error', `Failed to recalculate: ${err.message}`);
    },
  });

  const recommendations = recData?.recommendations || [];

  // Filter & sort
  const filteredAndSortedRoles = useMemo(() => {
    let result = [...recommendations];

    // Filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (r) =>
          r.role_title.toLowerCase().includes(q) ||
          r.matching_skills.some((s) => s.toLowerCase().includes(q)) ||
          r.alternative_titles.some((t) => t.toLowerCase().includes(q))
      );
    }

    // Sort
    result.sort((a, b) => {
      if (sortBy === 'composite') return b.composite_match_score - a.composite_match_score;
      if (sortBy === 'sbert') return b.similarity_score - a.similarity_score;
      if (sortBy === 'skills') return b.skill_match_score - a.skill_match_score;
      if (sortBy === 'projects') return b.project_alignment_score - a.project_alignment_score;
      return 0;
    });

    return result;
  }, [recommendations, searchQuery, sortBy]);

  const handleSelectAll = () => {
    const items: ConfirmedRoleItem[] = filteredAndSortedRoles.map((r) => ({
      role_id: r.role_id,
      role_title: r.role_title,
      is_custom: false,
      matching_skills: r.matching_skills,
      missing_skills: r.missing_skills,
      alternative_titles: r.alternative_titles,
      composite_match_score: r.composite_match_score,
      similarity_score: r.similarity_score,
    }));
    selectAllRoles(items);
    addToast('info', `Selected ${items.length} roles.`);
  };

  const handleDeselectAll = () => {
    deselectAllRoles();
    addToast('info', 'Deselected all roles.');
  };

  return (
    <div className="space-y-6 pb-20">
      {/* Page Title & SBERT Info */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 shadow-md border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 mb-2">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Model: {recData?.model_version || 'fine-tuned-sbert-384d'}</span>
            </div>
            <h2 className="text-xl font-bold tracking-tight">AI Career Role Recommendations</h2>
            <p className="text-xs text-slate-300 max-w-2xl mt-1 leading-relaxed">
              Synthesized using multi-objective hybrid scoring (0.45·SBERT + 0.35·Skills + 0.15·Projects + 0.05·Education).
              Select target roles to confirm or add your own custom specialization.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-shrink-0">
            <button
              onClick={() => setIsCustomRoleOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-white/10 hover:bg-white/20 text-white rounded-xl border border-white/20 transition-all backdrop-blur-xs"
            >
              <Plus className="w-4 h-4" />
              <span>Add Custom Role</span>
            </button>

            <button
              onClick={() => regenerateMutation.mutate()}
              disabled={regenerateMutation.isPending || isFetching}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-sm transition-all disabled:opacity-50"
            >
              <RefreshCw
                className={`w-4 h-4 ${
                  regenerateMutation.isPending || isFetching ? 'animate-spin' : ''
                }`}
              />
              <span>Recalculate</span>
            </button>
          </div>
        </div>
      </div>

      {/* Control Bar: Search, Sort, Select All / Deselect All */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search roles, skills, or alternative titles..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
          />
        </div>

        {/* Sort & Select controls */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 bg-slate-100 px-2.5 py-1 rounded-lg text-slate-600 border border-slate-200/80">
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-[11px] font-medium text-slate-500">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent text-xs font-semibold text-slate-700 focus:outline-hidden cursor-pointer"
            >
              <option value="composite">Overall Match</option>
              <option value="sbert">SBERT Similarity</option>
              <option value="skills">Skill Coverage</option>
              <option value="projects">Project Alignment</option>
            </select>
          </div>

          <div className="h-5 w-px bg-slate-200 mx-1 hidden sm:block" />

          <button
            onClick={handleSelectAll}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg border border-slate-200 font-medium transition-colors"
          >
            <CheckSquare className="w-3.5 h-3.5 text-indigo-600" />
            <span>Select All</span>
          </button>

          <button
            onClick={handleDeselectAll}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg border border-slate-200 font-medium transition-colors"
          >
            <Square className="w-3.5 h-3.5 text-slate-400" />
            <span>Deselect All</span>
          </button>
        </div>
      </div>

      {/* Recommendations Cards Grid */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400">
          <Sparkles className="w-8 h-8 mx-auto animate-spin text-indigo-600 mb-3" />
          <p className="text-sm font-semibold text-slate-700">Loading fine-tuned SBERT career rankings...</p>
          <p className="text-xs text-slate-400 mt-1">Analyzing candidate resume against 10 specialized engineering roles</p>
        </div>
      ) : filteredAndSortedRoles.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
          <Filter className="w-8 h-8 mx-auto text-slate-300 mb-2" />
          <p className="text-sm font-semibold">No career roles matching "{searchQuery}"</p>
          <button
            onClick={() => setSearchQuery('')}
            className="mt-2 text-xs font-semibold text-indigo-600 hover:underline"
          >
            Clear Search
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredAndSortedRoles.map((role, idx) => (
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

      {/* Sticky Bottom Confirmation Bar if any role is selected */}
      {selectedRoles.length > 0 && (
        <div className="fixed bottom-6 left-64 right-6 z-40 px-6">
          <div className="max-w-4xl mx-auto bg-slate-900/95 backdrop-blur-md text-white px-5 py-3.5 rounded-2xl shadow-2xl border border-slate-700/80 flex items-center justify-between gap-4 animate-in fade-in slide-in-from-bottom-3 duration-200">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs border border-emerald-500/30">
                {selectedRoles.length}
              </div>
              <div>
                <p className="text-xs font-bold text-slate-100">
                  {selectedRoles.length} Career Role{selectedRoles.length > 1 ? 's' : ''} Selected
                </p>
                <p className="text-[11px] text-slate-400">
                  Ready to review, finalize, and confirm to candidate profile
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <Link
                to="/selected-roles"
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-600/30 transition-all hover:scale-102"
              >
                <span>Review & Confirm Selection</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Role Details Modal */}
      <RoleDetailsModal
        role={selectedRoleDetails}
        isOpen={!!selectedRoleDetails}
        onClose={() => setSelectedRoleDetails(null)}
        isSelected={selectedRoleDetails ? isRoleSelected(selectedRoleDetails.role_id) : false}
        onToggleSelect={toggleSelectRole}
      />

      {/* Custom Role Modal */}
      <CustomRoleModal
        isOpen={isCustomRoleOpen}
        onClose={() => setIsCustomRoleOpen(false)}
      />
    </div>
  );
};
