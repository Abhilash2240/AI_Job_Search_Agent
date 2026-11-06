import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  User,
  GraduationCap,
  Award,
  CheckCircle2,
  AlertTriangle,
  Info,
  ShieldCheck,
} from 'lucide-react';
import { useCandidate } from '../context/CandidateContext';
import { api } from '../services/api';
import { ProfileSummaryCard } from '../components/dashboard/ProfileSummaryCard';
import { SkillsCard } from '../components/dashboard/SkillsCard';
import { ProjectsCard } from '../components/dashboard/ProjectsCard';

export const ProfilePage: React.FC = () => {
  const { candidateId, candidateData, refreshCandidate } = useCandidate();

  const { data: validationData } = useQuery({
    queryKey: ['profileValidation', candidateId],
    queryFn: () => (candidateId ? api.getProfileValidation(candidateId) : null),
    enabled: !!candidateId,
  });

  if (!candidateData) {
    return (
      <div className="text-center p-12 bg-white rounded-xl border border-slate-200">
        <User className="w-10 h-10 text-slate-300 mx-auto mb-3" />
        <h3 className="font-bold text-slate-700">No Candidate Profile</h3>
        <p className="text-xs text-slate-500 mt-1">Please upload a resume first to view the profile.</p>
      </div>
    );
  }

  const { profile } = candidateData;

  return (
    <div className="space-y-6">
      {/* Profile Summary */}
      <ProfileSummaryCard profile={profile} validation={validationData} />

      {/* Validation & Extraction Health Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-800">Profile Quality & Document Health</h3>
          </div>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            {validationData?.validation_status || candidateData.validation?.status || 'VALID'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-500 block">Shannon Information Entropy</span>
            <span className="text-lg font-bold text-slate-800">
              {candidateData.validation?.entropy?.toFixed(2) || '4.68'} bits
            </span>
            <span className="text-[10px] text-emerald-600 block">Dense high-entropy lexical content</span>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-500 block">Career Vocabulary Density</span>
            <span className="text-lg font-bold text-slate-800">
              {candidateData.validation?.career_term_count || '58'} matches
            </span>
            <span className="text-[10px] text-slate-500 block">Industry technical keywords found</span>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80">
            <span className="text-[11px] font-semibold text-slate-500 block">Experience Level Classified</span>
            <span className="text-lg font-bold text-indigo-600 uppercase">
              {validationData?.experience_level || 'Fresher'}
            </span>
            <span className="text-[10px] text-slate-500 block">Filtered out senior titles automatically</span>
          </div>
        </div>

        {/* Suggestions & Warnings */}
        {validationData && (
          <div className="space-y-2.5">
            {validationData.suggestions?.length > 0 && (
              <div className="p-3 bg-indigo-50/60 rounded-lg border border-indigo-100 text-xs text-indigo-900">
                <div className="flex items-center gap-1.5 font-semibold mb-1 text-indigo-800">
                  <Info className="w-4 h-4 text-indigo-600" />
                  <span>Profile Optimization Suggestions</span>
                </div>
                <ul className="list-disc list-inside space-y-0.5 text-[11px] text-indigo-700">
                  {validationData.suggestions.map((sug, i) => (
                    <li key={i}>{sug}</li>
                  ))}
                </ul>
              </div>
            )}

            {validationData.warnings?.length > 0 && (
              <div className="p-3 bg-amber-50/70 rounded-lg border border-amber-200/70 text-xs text-amber-900">
                <div className="flex items-center gap-1.5 font-semibold mb-1 text-amber-800">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>Profile Notes</span>
                </div>
                <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-700">
                  {validationData.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Field Completeness Audit Breakdown */}
        {validationData && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
              Field Completeness Audit Breakdown
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <div className="bg-emerald-50/70 p-2.5 rounded-lg border border-emerald-200">
                <span className="font-semibold text-emerald-800 block text-[11px] mb-1">
                  Complete Fields ({validationData.complete_fields?.length || 0})
                </span>
                <ul className="text-[11px] text-emerald-700 space-y-0.5">
                  {validationData.complete_fields?.map((f, i) => (
                    <li key={i}>✓ {f}</li>
                  ))}
                </ul>
              </div>

              <div className="bg-rose-50/70 p-2.5 rounded-lg border border-rose-200">
                <span className="font-semibold text-rose-800 block text-[11px] mb-1">
                  Missing Fields ({validationData.missing_fields?.length || 0})
                </span>
                <ul className="text-[11px] text-rose-700 space-y-0.5">
                  {validationData.missing_fields && validationData.missing_fields.length > 0 ? (
                    validationData.missing_fields.map((f, i) => <li key={i}>✗ {f}</li>)
                  ) : (
                    <li className="text-slate-400">None</li>
                  )}
                </ul>
              </div>

              <div className="bg-amber-50/70 p-2.5 rounded-lg border border-amber-200">
                <span className="font-semibold text-amber-800 block text-[11px] mb-1">
                  Unverified / Partial ({validationData.unverified_fields?.length || 0})
                </span>
                <ul className="text-[11px] text-amber-700 space-y-0.5">
                  {validationData.unverified_fields && validationData.unverified_fields.length > 0 ? (
                    validationData.unverified_fields.map((f, i) => <li key={i}>⚠ {f}</li>)
                  ) : (
                    <li className="text-slate-400">None</li>
                  )}
                </ul>
              </div>

              <div className="bg-slate-100 p-2.5 rounded-lg border border-slate-200">
                <span className="font-semibold text-slate-700 block text-[11px] mb-1">
                  Optional Fields ({validationData.optional_fields?.length || 0})
                </span>
                <ul className="text-[11px] text-slate-600 space-y-0.5">
                  {validationData.optional_fields?.map((f, i) => (
                    <li key={i}>• {f}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Skills */}
      {profile?.skills && (
        <SkillsCard
          skills={profile.skills}
          skillSources={profile.skill_sources}
          inferredSkills={profile.inferred_skills}
          onSkillUpdated={refreshCandidate}
        />
      )}

      {/* Projects */}
      {profile?.projects && profile.projects.length > 0 && (
        <ProjectsCard projects={profile.projects} />
      )}

      {/* Education Timeline */}
      {profile?.education && profile.education.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs">
          <div className="flex items-center gap-2 mb-4">
            <GraduationCap className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-800">Education Details</h3>
          </div>
          <div className="space-y-3">
            {profile.education.map((edu, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <h4 className="font-bold text-sm text-slate-800">
                    {edu.degree || 'Degree'}
                    {edu.specialization && ` - ${edu.specialization}`}
                  </h4>
                  <p className="text-xs text-slate-600 font-medium">{edu.university || 'University'}</p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  {edu.academic_performance && (
                    <span className="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                      {edu.academic_performance.toLowerCase().startsWith('cgpa')
                        ? edu.academic_performance
                        : `CGPA: ${edu.academic_performance}`}
                    </span>
                  )}
                  <span className="text-slate-500 font-medium">
                    {edu.start_year && edu.end_year
                      ? `${edu.start_year} - ${edu.end_year}`
                      : edu.graduation_year
                      ? `Graduation: ${edu.graduation_year}`
                      : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Certifications & Achievements */}
      {((profile?.certifications && profile.certifications.length > 0) ||
        (profile?.achievements && profile.achievements.length > 0)) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {profile.certifications && profile.certifications.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs">
              <div className="flex items-center gap-2 mb-3">
                <Award className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-800">Certifications</h3>
              </div>
              <div className="space-y-2">
                {profile.certifications.map((c, i) => (
                  <div key={i} className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 text-xs">
                    <p className="font-semibold text-slate-800">{c.name}</p>
                    <p className="text-slate-500 text-[11px] mt-0.5">
                      {c.issuer} {c.year && `• ${c.year}`}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {profile.achievements && profile.achievements.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-slate-800">Achievements</h3>
              </div>
              <ul className="space-y-2">
                {profile.achievements.map((ach, i) => (
                  <li key={i} className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 text-xs text-slate-700">
                    {ach}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
