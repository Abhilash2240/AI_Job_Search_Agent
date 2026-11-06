import React from 'react';
import {
  X,
  Sparkles,
  Check,
  HelpCircle,
  Calculator,
  Tag,
  CheckCircle2,
} from 'lucide-react';
import { RoleRecommendation, ConfirmedRoleItem } from '../../types/api';
import { ScoreBadge } from '../common/ScoreBadge';
import { ProgressBar } from '../common/ProgressBar';

interface RoleDetailsModalProps {
  role: RoleRecommendation | null;
  isOpen: boolean;
  onClose: () => void;
  isSelected: boolean;
  onToggleSelect: (role: ConfirmedRoleItem) => void;
}

export const RoleDetailsModal: React.FC<RoleDetailsModalProps> = ({
  role,
  isOpen,
  onClose,
  isSelected,
  onToggleSelect,
}) => {
  if (!isOpen || !role) return null;

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

  const components = [
    {
      label: 'SBERT Semantic Similarity',
      weight: '45%',
      score: role.similarity_score,
      desc: 'Fine-tuned 384-dimensional dense vector similarity between candidate experience & target role domain',
      color: 'bg-indigo-500',
    },
    {
      label: 'Skill Overlap & Coverage',
      weight: '35%',
      score: role.skill_match_score,
      desc: `Matched ${role.matching_skills.length} out of ${
        role.matching_skills.length + role.missing_skills.length
      } core competencies`,
      color: 'bg-emerald-500',
    },
    {
      label: 'Project Alignment',
      weight: '15%',
      score: role.project_alignment_score,
      desc: 'Relevance of verified projects, technical implementations, and tooling to role requirements',
      color: 'bg-amber-500',
    },
    {
      label: 'Education Alignment',
      weight: '5%',
      score: role.education_alignment_score,
      desc: 'Degree field, engineering specialization, and foundational academic coursework',
      color: 'bg-cyan-500',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-100/80 text-indigo-700">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">{role.role_title}</h2>
              <p className="text-xs text-slate-500">Fine-Tuned SBERT Hybrid Recommendation Analysis</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Top Score Summary Banner */}
          <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-xl p-4 flex items-center justify-between shadow-md">
            <div>
              <div className="text-xs uppercase tracking-wider text-indigo-300 font-semibold">
                Composite Career Match
              </div>
              <div className="text-2xl font-black mt-0.5">
                {Math.round(role.composite_match_score * 100)}%
              </div>
              <div className="text-[11px] text-slate-300 mt-1 max-w-md">
                {role.explanation}
              </div>
            </div>
            <ScoreBadge score={role.composite_match_score} size="lg" />
          </div>

          {/* Mathematical Scoring Formula */}
          <div>
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 mb-2">
              <Calculator className="w-4 h-4 text-indigo-600" />
              <span>Multi-Objective Scoring Formula</span>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs font-mono text-slate-700">
              Score = 0.45·SBERT + 0.35·Skills + 0.15·Projects + 0.05·Education
            </div>
          </div>

          {/* Component Scores Breakdown */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Scoring Components
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {components.map((c) => (
                <div key={c.label} className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-semibold text-slate-800">{c.label}</span>
                    <span className="font-bold text-indigo-600">
                      {Math.round(c.score * 100)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 mb-2">
                    <span>Weight: {c.weight}</span>
                    <span>Contribution: {(c.score * parseFloat(c.weight) / 100 * 100).toFixed(1)}%</span>
                  </div>
                  <ProgressBar value={c.score * 100} size="sm" />
                  <p className="text-[10px] text-slate-500 mt-1.5">{c.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Matching Skills with Provenance */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>Matching Skills ({role.matching_skills.length})</span>
              </div>
              <span className="text-[11px] text-slate-500">Verified with evidence</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {role.matching_skills.map((skill, idx) => {
                const name = typeof skill === 'string' ? skill : ((skill as any)?.skill_name || (skill as any)?.canonical_name || 'Skill');
                const evidenceList = role.skill_evidence?.[name.toLowerCase()] || (skill && typeof skill === 'object' && Array.isArray((skill as any).candidate_evidence) ? (skill as any).candidate_evidence : []);
                return (
                  <div
                    key={idx}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200"
                    title={
                      evidenceList.length > 0
                        ? `Evidence: ${evidenceList.join(', ')}`
                        : 'Verified from candidate profile'
                    }
                  >
                    <span>{name}</span>
                    {evidenceList.length > 0 && (
                      <span className="text-[10px] bg-emerald-200/60 px-1 rounded text-emerald-900">
                        {String(evidenceList[0]).split(':')[0]}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Missing / Unmentioned Skills */}
          {role.missing_skills.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                  <HelpCircle className="w-4 h-4 text-slate-500" />
                  <span>Not Found in Resume ({role.missing_skills.length})</span>
                </div>
                <span className="text-[11px] text-slate-400">
                  Common for role, consider adding if known
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {role.missing_skills.map((skill, idx) => {
                  const name = typeof skill === 'string' ? skill : ((skill as any)?.skill_name || (skill as any)?.canonical_name || 'Skill');
                  return (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg text-xs font-normal bg-slate-100 text-slate-600 border border-slate-200"
                    >
                      {name}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Alternative Titles */}
          {role.alternative_titles.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 mb-2">
                <Tag className="w-4 h-4 text-indigo-600" />
                <span>Alternative Job Titles</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {role.alternative_titles.map((t) => (
                  <span
                    key={t}
                    className="px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200/60 rounded-lg transition-colors"
          >
            Close
          </button>

          <button
            onClick={() => onToggleSelect(confirmedItem)}
            className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg shadow-sm transition-all ${
              isSelected
                ? 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100'
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            {isSelected ? (
              <>
                <X className="w-4 h-4" />
                <span>Remove from Selection</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                <span>Select this Career Role</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
