import React from 'react';
import { CheckCircle2, ShieldCheck, AlertCircle } from 'lucide-react';
import { SkillItem, StructuredSkill } from '../../types/api';

interface SkillBadgeProps {
  skill: SkillItem | any;
  variant?: 'matched' | 'missing' | 'neutral' | 'required' | 'preferred';
  size?: 'xs' | 'sm' | 'md';
  showEvidence?: boolean;
  className?: string;
}

export const SkillBadge: React.FC<SkillBadgeProps> = ({
  skill,
  variant = 'neutral',
  size = 'sm',
  showEvidence = false,
  className = '',
}) => {
  if (!skill) return null;

  let displayName = '';
  let canonicalName: string | undefined;
  let isVerified = false;
  let evidenceText: string | undefined;

  if (typeof skill === 'string') {
    displayName = skill;
  } else if (typeof skill === 'object' && skill !== null) {
    const s = skill as StructuredSkill;
    displayName = s.skill_name || s.canonical_name || 'Skill';
    canonicalName = s.canonical_name;
    isVerified = Boolean(s.is_verified);

    if (Array.isArray(s.candidate_evidence)) {
      evidenceText = s.candidate_evidence.filter(Boolean).join(' • ');
    } else if (typeof s.candidate_evidence === 'string') {
      evidenceText = s.candidate_evidence;
    } else if (s.evidence_snippet) {
      evidenceText = s.evidence_snippet;
    }
  } else {
    displayName = String(skill);
  }

  // Determine styling variant
  const effectiveVariant = isVerified && variant === 'neutral' ? 'matched' : variant;

  const getVariantStyles = () => {
    switch (effectiveVariant) {
      case 'matched':
        return 'bg-emerald-50 text-emerald-800 border-emerald-200/80 hover:bg-emerald-100/70';
      case 'missing':
        return 'bg-amber-50 text-amber-800 border-amber-200/80 hover:bg-amber-100/70';
      case 'required':
        return 'bg-indigo-50 text-indigo-800 border-indigo-200/80 hover:bg-indigo-100/70';
      case 'preferred':
        return 'bg-purple-50 text-purple-800 border-purple-200/80 hover:bg-purple-100/70';
      case 'neutral':
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100/80';
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case 'xs':
        return 'text-[10px] px-1.5 py-0.5 gap-1';
      case 'md':
        return 'text-xs px-3 py-1 gap-1.5';
      case 'sm':
      default:
        return 'text-[11px] px-2 py-0.5 gap-1';
    }
  };

  // Build descriptive tooltip
  const tooltipParts: string[] = [];
  if (canonicalName && canonicalName.toLowerCase() !== displayName.toLowerCase()) {
    tooltipParts.push(`Taxonomy: ${canonicalName}`);
  }
  if (isVerified) {
    tooltipParts.push('Verified Candidate Skill (Resume Provenance)');
  }
  if (evidenceText) {
    tooltipParts.push(`Evidence: ${evidenceText}`);
  }
  const tooltip = tooltipParts.length > 0 ? tooltipParts.join('\n') : undefined;

  return (
    <span
      title={tooltip}
      className={`inline-flex items-center font-medium rounded-md border transition-colors select-none ${getVariantStyles()} ${getSizeStyles()} ${className}`}
    >
      {effectiveVariant === 'matched' && (
        isVerified ? (
          <ShieldCheck className="w-3 h-3 text-emerald-600 flex-shrink-0" />
        ) : (
          <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
        )
      )}
      {effectiveVariant === 'missing' && (
        <AlertCircle className="w-3 h-3 text-amber-600 flex-shrink-0" />
      )}

      <span className="truncate max-w-[180px]">{displayName}</span>

      {showEvidence && evidenceText && (
        <span className="text-[10px] bg-emerald-200/50 text-emerald-900 px-1 rounded ml-0.5 font-normal truncate max-w-[120px]">
          {evidenceText.split('•')[0].trim()}
        </span>
      )}
    </span>
  );
};

