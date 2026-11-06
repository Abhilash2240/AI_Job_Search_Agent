import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  MapPin,
  Briefcase,
  Layers,
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  Send,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../services/api';
import { useCandidate } from '../context/CandidateContext';
import { JobDetailResponse } from '../types/api';
import { SkillBadge } from '../components/common/SkillBadge';

export const JobDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { candidateId, addToast } = useCandidate();

  const [job, setJob] = useState<JobDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isApplyingModalOpen, setIsApplyingModalOpen] = useState(false);
  const [applicationNotes, setApplicationNotes] = useState('');
  const [isSubmittingApp, setIsSubmittingApp] = useState(false);

  const fetchJobDetail = async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const activeCandId = candidateId || 3;
      const data = await api.getJobDetail(id, activeCandId);
      setJob(data);
    } catch (err) {
      addToast('error', 'Failed to load canonical job details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobDetail();
  }, [id, candidateId]);

  const handleToggleSave = async () => {
    if (!job) return;
    const activeCandId = candidateId || 3;
    try {
      if (job.is_saved) {
        await api.unsaveJob(activeCandId, job.id);
        addToast('info', `Removed ${job.title} from saved jobs.`);
        setJob({ ...job, is_saved: false });
      } else {
        await api.saveJob(activeCandId, job.id, 'Saved from detail page');
        addToast('success', `Saved ${job.title} at ${job.company_name}!`);
        setJob({ ...job, is_saved: true });
      }
    } catch (err) {
      addToast('error', 'Failed to update saved job status.');
    }
  };

  const handleCreateApplication = async () => {
    if (!job) return;
    setIsSubmittingApp(true);
    try {
      const activeCandId = candidateId || 3;
      await api.createApplication({
        candidate_id: activeCandId,
        canonical_job_id: job.id,
        company_name: job.company_name,
        job_title: job.title,
        application_url: job.canonical_application_url || job.canonical_source_url,
        status: 'APPLIED',
        notes: applicationNotes || 'Logged from job detail view',
      });
      addToast('success', `Application for ${job.title} recorded in Tracker!`);
      setIsApplyingModalOpen(false);
      setJob({ ...job, application_status: 'APPLIED' });
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to record application.';
      addToast('error', msg);
    } finally {
      setIsSubmittingApp(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl p-16 text-center border border-slate-200">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-600 font-medium text-sm">Loading canonical job specifications & matching data...</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="bg-white rounded-xl p-16 text-center border border-slate-200 space-y-4">
        <h3 className="text-lg font-bold text-slate-800">Job Not Found</h3>
        <p className="text-slate-500 text-sm">The requested canonical vacancy could not be located.</p>
        <button
          onClick={() => navigate('/jobs')}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg"
        >
          Back to Job Feed
        </button>
      </div>
    );
  }

  const match = job.match_details;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 w-full min-w-0">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Feed
      </button>

      {/* Main Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 sm:p-6 md:p-8 shadow-sm overflow-hidden">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-5 pb-6 border-b border-slate-100">
          <div className="flex items-start gap-3.5 sm:gap-4 min-w-0 flex-1 w-full">
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-xl sm:text-2xl flex-shrink-0">
              {job.company_name?.charAt(0) || 'J'}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider truncate max-w-[200px]">
                  {job.company_name}
                </span>
                <span className="text-slate-300">•</span>
                <span className="text-xs font-mono text-slate-400 truncate">{job.canonical_job_id}</span>
              </div>
              <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight break-words">
                {job.title}
              </h1>
              {job.canonical_job_title && job.canonical_job_title !== job.title && (
                <p className="text-xs text-slate-500 mt-1 font-medium break-words">
                  Normalized Title: <span className="text-slate-700 font-semibold">{job.canonical_job_title}</span>
                </p>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 w-full lg:w-auto flex-shrink-0">
            <button
              onClick={handleToggleSave}
              className={`flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl border text-xs sm:text-sm font-semibold transition shadow-sm ${
                job.is_saved
                  ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              {job.is_saved ? (
                <>
                  <BookmarkCheck className="w-4 h-4" /> Bookmarked
                </>
              ) : (
                <>
                  <Bookmark className="w-4 h-4" /> Bookmark
                </>
              )}
            </button>

            {job.application_status ? (
              <span className="inline-flex items-center gap-1.5 px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs sm:text-sm font-bold">
                <CheckCircle2 className="w-4 h-4" /> {job.application_status}
              </span>
            ) : (
              <button
                onClick={() => setIsApplyingModalOpen(true)}
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2 sm:py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold transition shadow-md shadow-indigo-600/20"
              >
                <Send className="w-4 h-4" /> Track Application
              </button>
            )}

            {(job.canonical_application_url || job.canonical_source_url) && (
              <a
                href={job.canonical_application_url || job.canonical_source_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs sm:text-sm font-semibold transition"
              >
                Apply Direct <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>

        {/* Specifications Pills */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-5">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100 min-w-0 overflow-hidden">
            <MapPin className="w-5 h-5 text-indigo-500 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Location</span>
              <span className="text-xs font-bold text-slate-800 truncate block">{job.location || 'India'}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100 min-w-0 overflow-hidden">
            <Layers className="w-5 h-5 text-indigo-500 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Workplace Mode</span>
              <span className="text-xs font-bold text-slate-800 truncate block">{job.workplace_type || 'ON_SITE'}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100 min-w-0 overflow-hidden">
            <Briefcase className="w-5 h-5 text-indigo-500 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Employment Type</span>
              <span className="text-xs font-bold text-slate-800 truncate block">{job.employment_type?.replace('_', ' ') || 'Full Time'}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100 min-w-0 overflow-hidden">
            <ShieldCheck className="w-5 h-5 text-emerald-500 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Verification</span>
              <span className="text-xs font-bold text-emerald-700 truncate block">{job.vacancy_status}</span>
            </div>
          </div>
        </div>
      </div>

      {/* AI Matching Breakdown Card */}
      {match && (
        <div className="bg-white rounded-2xl border border-indigo-100 p-4 sm:p-6 md:p-8 shadow-sm space-y-5 sm:space-y-6 overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100">
            <div className="min-w-0">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold mb-2">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" /> Explainable SBERT Match
              </div>
              <h3 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight break-words">
                Candidate-to-Job Compatibility Analysis
              </h3>
            </div>

            <div className="flex items-center gap-3 sm:gap-4 bg-slate-50 px-4 sm:px-5 py-2.5 sm:py-3 rounded-xl border border-slate-200 flex-shrink-0 self-start sm:self-auto">
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">Composite Score</span>
                <span className="text-xl sm:text-2xl font-black text-indigo-600">{Math.round(match.composite_score)}/100</span>
              </div>
              <div className="h-8 w-px bg-slate-200" />
              <div>
                <span className="text-[10px] text-slate-500 uppercase font-semibold block">Score Coverage</span>
                <span className="text-xs sm:text-sm font-bold text-slate-800">
                  {Math.round((match.score_coverage || 0.95) * 100)}%
                </span>
              </div>
            </div>
          </div>

          {/* Technical Relevance Status Banner */}
          {match.is_relevant === false ? (
            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3 text-amber-900">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-xs uppercase tracking-wider block">Career Direction Relevance: Out-of-Scope</span>
                <p className="text-xs text-amber-800 mt-0.5">
                  This role belongs to the <strong>{match.role_family?.replace(/_/g, ' ')}</strong> family. It is excluded from your personalized recommended feed.
                  {match.rejection_reasons && match.rejection_reasons.length > 0 && ` Reason: ${match.rejection_reasons.join('; ')}`}
                </p>
              </div>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3 text-emerald-900">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-xs uppercase tracking-wider block">Career Direction Relevance: Verified Technical Match</span>
                <p className="text-xs text-emerald-800 mt-0.5">
                  Verified alignment with your confirmed target roles in <strong>{match.role_family?.replace(/_/g, ' ') || 'Software Engineering'}</strong>.
                </p>
              </div>
            </div>
          )}

          {/* Component Score Progress Bars */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1.5">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-slate-600">Semantic Fit (35%)</span>
                <span className="text-indigo-600">{Math.round(match.semantic_score * 100)}%</span>
              </div>
              <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full bg-indigo-600 rounded-full" style={{ width: `${match.semantic_score * 100}%` }} />
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1.5">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-slate-600">Skills Alignment (30%)</span>
                <span className="text-emerald-600">{Math.round(match.skill_score * 100)}%</span>
              </div>
              <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${match.skill_score * 100}%` }} />
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-1.5">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-slate-600">Role Target (15%)</span>
                <span className="text-blue-600">{Math.round(match.role_score * 100)}%</span>
              </div>
              <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${match.role_score * 100}%` }} />
              </div>
            </div>
          </div>

          {/* Natural Language Explanation */}
          <div className="p-4 rounded-xl bg-indigo-50/60 border border-indigo-100 text-xs text-slate-700 leading-relaxed space-y-2">
            <span className="font-bold text-indigo-900 block uppercase tracking-wider text-[11px]">
              Evaluation Verdict:
            </span>
            <p className="whitespace-pre-line">{match.explanation}</p>
          </div>

          {/* Skills Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div>
              <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider block mb-2">
                ✓ Verified Matched Skills ({match.matched_skills?.length || 0})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {match.matched_skills && match.matched_skills.length > 0 ? (
                  match.matched_skills.map((s, i) => (
                    <SkillBadge
                      key={i}
                      skill={s}
                      variant="matched"
                      size="sm"
                      showEvidence={true}
                    />
                  ))
                ) : (
                  <span className="text-xs text-slate-400">No direct required skill overlap found.</span>
                )}
              </div>
            </div>

            <div>
              <span className="text-xs font-bold text-amber-800 uppercase tracking-wider block mb-2">
                ⚠ Missing Required Skills ({match.missing_skills?.length || 0})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {match.missing_skills && match.missing_skills.length > 0 ? (
                  match.missing_skills.map((s, i) => (
                    <SkillBadge
                      key={i}
                      skill={s}
                      variant="missing"
                      size="sm"
                    />
                  ))
                ) : (
                  <span className="text-xs text-emerald-600 font-medium">All explicit skills matched!</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Description & Responsibilities */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-8">
        {job.description && (
          <div>
            <h3 className="text-base font-bold text-slate-900 mb-3">Role Overview</h3>
            <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {job.description}
            </div>
          </div>
        )}

        {job.responsibilities && job.responsibilities.length > 0 && (
          <div>
            <h3 className="text-base font-bold text-slate-900 mb-3">Key Responsibilities</h3>
            <ul className="space-y-2 text-sm text-slate-700 list-disc list-inside">
              {job.responsibilities.map((r: any, i: number) => (
                <li key={i} className="leading-relaxed">
                  {typeof r === 'string' ? r : (r?.text || JSON.stringify(r))}
                </li>
              ))}
            </ul>
          </div>
        )}

        {job.qualifications && job.qualifications.length > 0 && (
          <div>
            <h3 className="text-base font-bold text-slate-900 mb-3">Qualifications & Requirements</h3>
            <ul className="space-y-2 text-sm text-slate-700 list-disc list-inside">
              {job.qualifications.map((q: any, i: number) => (
                <li key={i} className="leading-relaxed">
                  {typeof q === 'string' ? q : (q?.text || JSON.stringify(q))}
                </li>
              ))}
            </ul>
          </div>
        )}

        {((job.required_skills && job.required_skills.length > 0) ||
          (job.preferred_skills && job.preferred_skills.length > 0)) && (
          <div>
            <h3 className="text-base font-bold text-slate-900 mb-3">Extracted Skills Specification</h3>
            <div className="space-y-3">
              {job.required_skills && job.required_skills.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-slate-600 block mb-1.5">Required Skills:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {job.required_skills.map((s: any, idx: number) => (
                      <SkillBadge key={idx} skill={s} variant="required" size="sm" />
                    ))}
                  </div>
                </div>
              )}
              {job.preferred_skills && job.preferred_skills.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-slate-600 block mb-1.5">Preferred Skills:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {job.preferred_skills.map((s: any, idx: number) => (
                      <SkillBadge key={idx} skill={s} variant="preferred" size="sm" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Application Tracking Modal */}
      {isApplyingModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-5">
            <h3 className="text-lg font-bold text-slate-900">Track Application for {job.title}</h3>
            <p className="text-xs text-slate-500">
              Confirm that you have submitted an application on the employer's official website.
            </p>
            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Application Notes (optional)
              </label>
              <textarea
                value={applicationNotes}
                onChange={(e) => setApplicationNotes(e.target.value)}
                placeholder="e.g. Applied via Lever link with portfolio resume; referral by hiring manager."
                className="w-full text-xs p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                rows={3}
              />
            </div>
            <div className="flex items-center justify-end gap-3 pt-3">
              <button
                onClick={() => setIsApplyingModalOpen(false)}
                className="px-4 py-2 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateApplication}
                disabled={isSubmittingApp}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition"
              >
                {isSubmittingApp ? 'Saving...' : 'Confirm & Track'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
