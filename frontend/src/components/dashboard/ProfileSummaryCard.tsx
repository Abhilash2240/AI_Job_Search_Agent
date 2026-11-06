import React from 'react';
import { Mail, Phone, MapPin, GraduationCap, Award, ShieldCheck, User } from 'lucide-react';
import { CandidateProfile, DetailedProfileValidation } from '../../types/api';
import { ProgressBar } from '../common/ProgressBar';

interface ProfileSummaryCardProps {
  profile: CandidateProfile;
  validation?: DetailedProfileValidation | null;
}

export const ProfileSummaryCard: React.FC<ProfileSummaryCardProps> = ({ profile, validation }) => {
  const { personal, education } = profile;
  const completeness = validation?.completeness_score ?? (profile.profile_completeness ? profile.profile_completeness * 100 : 75);
  const expLevel = validation?.experience_level || 'fresher';

  const formatExpLevel = (level: string) => {
    switch (level.toLowerCase()) {
      case 'fresher':
        return 'Fresher (0 Years)';
      case 'entry_level':
        return 'Entry Level (0-2 Years)';
      case 'mid_level':
        return 'Mid Level (2-5 Years)';
      case 'senior':
        return 'Senior (5+ Years)';
      default:
        return level;
    }
  };

  const primaryEdu = education?.[0];

  const formatAcademicPerformance = (val: string | null | undefined) => {
    if (!val) return '';
    const clean = val.trim();
    if (clean.toLowerCase().startsWith('cgpa')) {
      return clean;
    }
    return `CGPA: ${clean}`;
  };

  const isSkillsOrInvalidLoc = (loc: string | null | undefined) => {
    if (!loc) return true;
    const l = loc.toLowerCase();
    return (
      l.includes('python') ||
      l.includes('sql') ||
      l.includes('api') ||
      l.includes('rag') ||
      l.includes('java') ||
      l.includes('aws')
    );
  };
  const validLocation = !isSkillsOrInvalidLoc(personal?.location) ? personal.location : null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
        {/* Avatar & Personal info */}
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xl flex-shrink-0 shadow-sm">
            {personal?.name ? personal.name.charAt(0) : <User className="w-7 h-7" />}
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h2 className="text-xl font-bold text-slate-800">
                {personal?.name || 'Candidate Name Not Found'}
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide bg-indigo-50 text-indigo-700 border border-indigo-200/80">
                {formatExpLevel(expLevel)}
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <ShieldCheck className="w-3.5 h-3.5" />
                Verified
              </span>
            </div>

            {/* Contact details */}
            <div className="flex flex-wrap items-center gap-y-1.5 gap-x-4 mt-2.5 text-xs text-slate-500">
              {personal?.email && (
                <div className="flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  <a href={`mailto:${personal.email}`} className="hover:text-indigo-600">
                    {personal.email}
                  </a>
                </div>
              )}
              {personal?.phone && (
                <div className="flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  <span>{personal.phone}</span>
                </div>
              )}
              {validLocation && (
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  <span>{validLocation}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Profile Completeness Gauge */}
        <div className="w-full md:w-60 bg-slate-50 p-3.5 rounded-xl border border-slate-200/70 flex-shrink-0">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-700 mb-1.5">
            <span>Profile Completeness</span>
            <span className="text-indigo-600 font-bold">{Math.round(completeness)}%</span>
          </div>
          <ProgressBar value={completeness} size="sm" />
          <p className="text-[11px] text-slate-500 mt-1.5">
            {completeness >= 80
              ? 'Complete profile suitable for high-precision SBERT matching.'
              : 'Add more details to increase role recommendation accuracy.'}
          </p>
        </div>
      </div>

      {/* Primary Education Highlight */}
      {primaryEdu && (
        <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs bg-slate-50/50 rounded-lg p-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-indigo-100/70 text-indigo-700 rounded-lg">
              <GraduationCap className="w-4 h-4" />
            </div>
            <div>
              <span className="font-semibold text-slate-800">
                {primaryEdu.degree || 'Degree'}{' '}
                {primaryEdu.specialization && `in ${primaryEdu.specialization}`}
              </span>
              <span className="text-slate-500"> • {primaryEdu.university || 'University'}</span>
            </div>
          </div>
          <div className="flex items-center gap-3 font-medium text-slate-600">
            {primaryEdu.academic_performance && (
              <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                <Award className="w-3.5 h-3.5" />
                {formatAcademicPerformance(primaryEdu.academic_performance)}
              </span>
            )}
            {(primaryEdu.start_year || primaryEdu.end_year || primaryEdu.graduation_year) && (
              <span className="text-slate-500">
                Batch:{' '}
                {primaryEdu.start_year && primaryEdu.end_year
                  ? `${primaryEdu.start_year} - ${primaryEdu.end_year}`
                  : primaryEdu.graduation_year || 'Current'}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
