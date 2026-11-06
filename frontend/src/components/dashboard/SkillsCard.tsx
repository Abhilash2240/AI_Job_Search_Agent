import React, { useState } from 'react';
import {
  Code2,
  Layers,
  Database,
  Wrench,
  Sparkles,
  Check,
  HelpCircle,
  X,
  ShieldCheck,
} from 'lucide-react';
import { SkillsCategorized } from '../../types/api';
import { useCandidate } from '../../context/CandidateContext';
import { api } from '../../services/api';

interface SkillsCardProps {
  skills: SkillsCategorized;
  skillSources?: Record<string, string[]>;
  inferredSkills?: string[];
  onSkillUpdated?: () => void;
}

export const SkillsCard: React.FC<SkillsCardProps> = ({
  skills,
  skillSources = {},
  inferredSkills = [],
  onSkillUpdated,
}) => {
  const { candidateId, addToast, refreshCandidate } = useCandidate();
  const [activeTab, setActiveTab] = useState<'all' | 'languages' | 'frameworks' | 'databases' | 'tools' | 'aiml'>('all');
  const [isProcessing, setIsProcessing] = useState(false);

  const categories = [
    {
      key: 'languages',
      label: 'Languages',
      icon: Code2,
      items: skills.programming_languages || [],
      color: 'bg-blue-50 text-blue-700 border-blue-200',
    },
    {
      key: 'frameworks',
      label: 'Frameworks',
      icon: Layers,
      items: skills.frameworks || [],
      color: 'bg-purple-50 text-purple-700 border-purple-200',
    },
    {
      key: 'databases',
      label: 'Databases',
      icon: Database,
      items: skills.databases || [],
      color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    },
    {
      key: 'aiml',
      label: 'AI & Data',
      icon: Sparkles,
      items: skills.ai_ml || [],
      color: 'bg-amber-50 text-amber-700 border-amber-200',
    },
    {
      key: 'tools',
      label: 'Tools & DevOps',
      icon: Wrench,
      items: skills.tools || [],
      color: 'bg-slate-100 text-slate-700 border-slate-300',
    },
  ];

  const totalSkills = categories.reduce((sum, c) => sum + c.items.length, 0);

  const handleConfirmSkill = async (skill: string) => {
    if (!candidateId) return;
    try {
      setIsProcessing(true);
      await api.confirmSkill(candidateId, skill);
      addToast('success', `Confirmed "${skill}" as verified skill.`);
      await refreshCandidate();
      onSkillUpdated?.();
    } catch (err: any) {
      addToast('error', `Failed to confirm skill: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRejectSkill = async (skill: string) => {
    if (!candidateId) return;
    try {
      setIsProcessing(true);
      await api.rejectSkill(candidateId, skill);
      addToast('info', `Removed "${skill}" from profile.`);
      await refreshCandidate();
      onSkillUpdated?.();
    } catch (err: any) {
      addToast('error', `Failed to remove skill: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-800">Verified Technical Skills</h3>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              {totalSkills} Skills Verified
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Strictly verified against candidate resume text, project code, and documented experience.
          </p>
        </div>

        {/* Tab Filters */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-100 rounded-lg text-xs font-medium">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-2.5 py-1 rounded-md transition-all ${
              activeTab === 'all'
                ? 'bg-white text-indigo-700 shadow-sm font-semibold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            All ({totalSkills})
          </button>
          {categories.map((c) => (
            <button
              key={c.key}
              onClick={() => setActiveTab(c.key as any)}
              className={`px-2.5 py-1 rounded-md transition-all ${
                activeTab === c.key
                  ? 'bg-white text-indigo-700 shadow-sm font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {c.label} ({c.items.length})
            </button>
          ))}
        </div>
      </div>

      {/* Skills Grid */}
      <div className="space-y-4">
        {categories
          .filter((cat) => activeTab === 'all' || activeTab === cat.key)
          .map((cat) => {
            if (cat.items.length === 0) return null;
            const Icon = cat.icon;

            return (
              <div key={cat.key} className="space-y-2">
                {activeTab === 'all' && (
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    <Icon className="w-3.5 h-3.5" />
                    <span>{cat.label}</span>
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {cat.items.map((skill, sIdx) => {
                    const skillName = typeof skill === 'string' ? skill : ((skill as any)?.skill_name || (skill as any)?.canonical_name || 'Skill');
                    const sources = skillSources[skillName.toLowerCase()] || [];
                    const isFromProject = sources.some((s) => s.includes('project'));
                    const isFromExp = sources.some((s) => s.includes('experience'));
                    const isFromCert = sources.some((s) => s.includes('certification'));

                    return (
                      <span
                        key={sIdx}
                        title={
                          sources.length > 0
                            ? `Evidence: ${sources.join(' • ')}`
                            : `Verified skill`
                        }
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border ${cat.color} group transition-all`}
                      >
                        <Check className="w-3 h-3 flex-shrink-0 text-emerald-600" />
                        <span>{skillName}</span>
                        {isFromProject && (
                          <span
                            className="w-1.5 h-1.5 rounded-full bg-indigo-500 flex-shrink-0"
                            title="Proven in project code"
                          />
                        )}
                        {isFromExp && (
                          <span
                            className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0"
                            title="Proven in professional experience"
                          />
                        )}
                        {isFromCert && (
                          <span
                            className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0"
                            title="Validated by certification"
                          />
                        )}
                        {/* Optional removal button for candidate refinement */}
                        <button
                          type="button"
                          onClick={() => handleRejectSkill(skillName)}
                          disabled={isProcessing}
                          title={`Remove ${skillName} from verified skills`}
                          className="opacity-0 group-hover:opacity-100 hover:text-rose-600 transition-opacity ml-1"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    );
                  })}
                </div>
              </div>
            );
          })}
      </div>

      {/* Inferred & Uncertain Skills Review Section */}
      {inferredSkills && inferredSkills.length > 0 && (
        <div className="mt-5 pt-4 border-t border-slate-100">
          <div className="p-3.5 bg-amber-50/80 rounded-xl border border-amber-200">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-amber-600" />
                <h4 className="text-xs font-bold text-amber-900">
                  Inferred Skills Awaiting Candidate Confirmation ({inferredSkills.length})
                </h4>
              </div>
              <span className="text-[11px] text-amber-700">Not included in verified count until confirmed</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {inferredSkills.map((infSkill, iIdx) => {
                const infName = typeof infSkill === 'string' ? infSkill : ((infSkill as any)?.skill_name || (infSkill as any)?.canonical_name || 'Skill');
                return (
                  <div
                    key={iIdx}
                    className="inline-flex items-center gap-2 px-3 py-1 rounded-lg text-xs bg-white text-slate-800 border border-amber-300 shadow-2xs"
                  >
                    <span className="font-medium">{infName}</span>
                    <div className="flex items-center gap-1 border-l border-slate-200 pl-1.5">
                      <button
                        type="button"
                        onClick={() => handleConfirmSkill(infName)}
                        disabled={isProcessing}
                        title="Confirm this skill"
                        className="p-0.5 text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 rounded"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRejectSkill(infName)}
                        disabled={isProcessing}
                        title="Reject this skill"
                        className="p-0.5 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Legend & Provenance Footer */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" /> Project Evidence
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Experience Evidence
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> Certification Evidence
          </span>
        </div>
        <div className="flex items-center gap-1 text-emerald-700 font-medium">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Zero Fabricated Skills</span>
        </div>
      </div>
    </div>
  );
};
