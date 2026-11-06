import React from 'react';
import {
  CheckCircle2,
  Circle,
  Eye,
  Sparkles,
  Code2,
  FolderGit2,
  GraduationCap,
  Check,
  HelpCircle,
  Tag,
} from 'lucide-react';
import { RoleRecommendation, ConfirmedRoleItem } from '../../types/api';
import { ScoreBadge } from '../common/ScoreBadge';
import { ProgressBar } from '../common/ProgressBar';

interface RoleRecommendationCardProps {
  role: RoleRecommendation;
  rank: number;
  isSelected: boolean;
  onToggleSelect: (role: ConfirmedRoleItem) => void;
  onViewDetails: (role: RoleRecommendation) => void;
}

export const RoleRecommendationCard: React.FC<RoleRecommendationCardProps> = ({
  role,
  rank,
  isSelected,
  onToggleSelect,
  onViewDetails,
}) => {
  const confirmedItem: ConfirmedRoleItem = {
    role_id: role.role_id,
    role_title: role.role_title,
    is_custom: false,
    matching_skills: role.matching_skills,
    missing_skills: role.missing_skills,
    alternative_titles: role.alternative_titles,
    composite_match_score: role.composite_match_score,
    similarity_score: role.similarity_score,
  };

  const sbertPct = Math.round(role.similarity_score * 100);
  const skillPct = Math.round(role.skill_match_score * 100);
  const projectPct = Math.round(role.project_alignment_score * 100);
  const eduPct = Math.round((role.education_alignment_score || 0) * 100);

  return (
    <div
      className={`rounded-xl border transition-all duration-200 bg-white overflow-hidden shadow-xs hover:shadow-md ${
        isSelected
          ? 'border-indigo-600 ring-2 ring-indigo-500/20'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      <div className="p-5">
        {/* Top Header: Rank, Title, Select Button, Match Badge */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <button
              type="button"
              onClick={() => onToggleSelect(confirmedItem)}
              className="mt-0.5 text-slate-400 hover:text-indigo-600 focus:outline-hidden transition-colors"
              title={isSelected ? 'Deselect role' : 'Select role'}
            >
              {isSelected ? (
                <CheckCircle2 className="w-5 h-5 text-indigo-600 fill-indigo-100" />
              ) : (
                <Circle className="w-5 h-5" />
              )}
            </button>

            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 font-mono">#{rank}</span>
                <h3 className="font-bold text-base text-slate-900 hover:text-indigo-600 transition-colors cursor-pointer"
                    onClick={() => onViewDetails(role)}>
                  {role.role_title}
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{role.explanation}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <ScoreBadge score={role.composite_match_score} label="Match" size="md" />
          </div>
        </div>

        {/* 4-Component Multi-Objective Metrics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 pt-3 border-t border-slate-100 text-xs">
          <div className="bg-slate-50 rounded-lg p-2 border border-slate-100">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="flex items-center gap-1 font-medium text-[11px]">
                <Sparkles className="w-3 h-3 text-indigo-500" /> SBERT
              </span>
              <span className="font-bold text-slate-700">{sbertPct}%</span>
            </div>
            <ProgressBar value={sbertPct} size="sm" />
          </div>

          <div className="bg-slate-50 rounded-lg p-2 border border-slate-100">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="flex items-center gap-1 font-medium text-[11px]">
                <Code2 className="w-3 h-3 text-emerald-500" /> Skills
              </span>
              <span className="font-bold text-slate-700">{skillPct}%</span>
            </div>
            <ProgressBar value={skillPct} size="sm" />
          </div>

          <div className="bg-slate-50 rounded-lg p-2 border border-slate-100">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="flex items-center gap-1 font-medium text-[11px]">
                <FolderGit2 className="w-3 h-3 text-amber-500" /> Projects
              </span>
              <span className="font-bold text-slate-700">{projectPct}%</span>
            </div>
            <ProgressBar value={projectPct} size="sm" />
          </div>

          <div className="bg-slate-50 rounded-lg p-2 border border-slate-100">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="flex items-center gap-1 font-medium text-[11px]">
                <GraduationCap className="w-3 h-3 text-cyan-600" /> Edu
              </span>
              <span className="font-bold text-slate-700">{eduPct}%</span>
            </div>
            <ProgressBar value={eduPct} size="sm" />
          </div>
        </div>

        {/* Skills Snippets */}
        <div className="mt-3.5 space-y-2">
          {/* Matching Skills */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-semibold text-emerald-700 inline-flex items-center gap-1 mr-1">
              <Check className="w-3 h-3" /> Matching ({role.matching_skills.length}):
            </span>
            {role.matching_skills.slice(0, 5).map((skill, idx) => {
              const name = typeof skill === 'string' ? skill : ((skill as any)?.skill_name || (skill as any)?.canonical_name || 'Skill');
              return (
                <span
                  key={idx}
                  className="px-2 py-0.5 text-[11px] font-medium bg-emerald-50 text-emerald-700 rounded-md border border-emerald-200/80"
                >
                  {name}
                </span>
              );
            })}
            {role.matching_skills.length > 5 && (
              <span className="text-[11px] text-slate-500 font-medium">
                +{role.matching_skills.length - 5} more
              </span>
            )}
          </div>

          {/* Missing / Unmentioned Skills */}
          {role.missing_skills.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px] font-semibold text-slate-500 inline-flex items-center gap-1 mr-1">
                <HelpCircle className="w-3 h-3" /> Not in Resume ({role.missing_skills.length}):
              </span>
              {role.missing_skills.slice(0, 3).map((skill, idx) => {
                const name = typeof skill === 'string' ? skill : ((skill as any)?.skill_name || (skill as any)?.canonical_name || 'Skill');
                return (
                  <span
                    key={idx}
                    className="px-2 py-0.5 text-[11px] font-normal bg-slate-100 text-slate-600 rounded-md border border-slate-200"
                  >
                    {name}
                  </span>
                );
              })}
              {role.missing_skills.length > 3 && (
                <span className="text-[11px] text-slate-400">
                  +{role.missing_skills.length - 3} more
                </span>
              )}
            </div>
          )}
        </div>

        {/* Alternative Titles & Actions Footer */}
        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-1.5 overflow-hidden">
            <Tag className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
            <span className="text-slate-400 text-[11px] flex-shrink-0">Titles:</span>
            <span className="text-slate-600 text-[11px] truncate">
              {role.alternative_titles.slice(0, 2).join(', ')}
            </span>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => onViewDetails(role)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-slate-600 hover:text-indigo-600 font-medium text-xs rounded-lg hover:bg-slate-100 transition-colors"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Details</span>
            </button>
            <button
              onClick={() => onToggleSelect(confirmedItem)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                isSelected
                  ? 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-2xs'
              }`}
            >
              {isSelected ? 'Selected' : 'Select Role'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
