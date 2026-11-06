import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Compass,
  Briefcase,
  MapPin,
  Bookmark,
  BookmarkCheck,
  ChevronRight,
  SlidersHorizontal,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ArrowUpDown,
} from 'lucide-react';
import { api } from '../services/api';
import { useCandidate } from '../context/CandidateContext';
import { JobFeedItem } from '../types/api';
import { SkillBadge } from '../components/common/SkillBadge';

export const JobFeedPage: React.FC = () => {
  const navigate = useNavigate();
  const { candidateId, addToast } = useCandidate();

  const [jobs, setJobs] = useState<JobFeedItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [workModeFilter, setWorkModeFilter] = useState('');
  const [employmentTypeFilter, setEmploymentTypeFilter] = useState('');
  const [eligibilityFilter, setEligibilityFilter] = useState('');
  const [relevanceFilter, setRelevanceFilter] = useState<'RELEVANT' | 'ALL' | 'IRRELEVANT'>('RELEVANT');
  const [minScore, setMinScore] = useState<number>(0);
  const [sortBy, setSortBy] = useState('score');

  const fetchJobs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = {
        candidate_id: candidateId || 3,
        page,
        page_size: 12,
        sort_by: sortBy,
        relevance: relevanceFilter,
      };
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (locationFilter) params.location = locationFilter;
      if (workModeFilter) params.work_mode = workModeFilter;
      if (employmentTypeFilter) params.employment_type = employmentTypeFilter;
      if (eligibilityFilter) params.eligibility = eligibilityFilter;
      if (minScore > 0) params.min_score = minScore;

      const data = await api.getJobsFeed(params);
      setJobs(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to load jobs feed. Please check backend connection.';
      setError(msg);
      addToast('error', msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [page, sortBy, locationFilter, workModeFilter, employmentTypeFilter, eligibilityFilter, relevanceFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchJobs();
  };

  const handleToggleSave = async (job: JobFeedItem, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const activeCandId = candidateId || 3;
      if (job.is_saved) {
        await api.unsaveJob(activeCandId, job.id);
        addToast('info', `Removed ${job.title} from saved jobs.`);
        setJobs(jobs.map((j) => (j.id === job.id ? { ...j, is_saved: false } : j)));
      } else {
        await api.saveJob(activeCandId, job.id, 'Bookmarked from Job Feed');
        addToast('success', `Saved ${job.title} at ${job.company_name}!`);
        setJobs(jobs.map((j) => (j.id === job.id ? { ...j, is_saved: true } : j)));
      }
    } catch (err) {
      addToast('error', 'Failed to update saved job status.');
    }
  };

  const getEligibilityBadge = (status: string) => {
    switch (status) {
      case 'ELIGIBLE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Eligible
          </span>
        );
      case 'ELIGIBLE_WITH_CONDITIONS':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" /> Conditions
          </span>
        );
      case 'NEEDS_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <Clock className="w-3 h-3 text-blue-600" /> Review
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-5 sm:space-y-6 w-full min-w-0">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-5 sm:p-6 text-white shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-96 bg-gradient-to-l from-indigo-500/10 to-transparent pointer-events-none" />
        <div className="relative z-10 max-w-3xl min-w-0">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-semibold uppercase tracking-wider mb-2.5 sm:mb-3 border border-indigo-500/30">
            <Compass className="w-3.5 h-3.5" />
            AI-Ranked Vacancies
          </div>
          <h2 className="text-xl sm:text-2xl md:text-3xl font-extrabold tracking-tight break-words">
            Intelligent Job Feed & Recommendations
          </h2>
          <p className="text-slate-300 text-xs sm:text-sm mt-1.5 sm:mt-2 leading-relaxed">
            Multi-component evaluation using fine-tuned SBERT embeddings, verified skills provenance,
            and confirmed career targets across verified Indian and remote tech employers.
          </p>
        </div>
      </div>

      {/* Category Tabs: Recommended (Relevant) vs All vs Out-of-Scope */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => { setRelevanceFilter('RELEVANT'); setPage(1); }}
          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition ${
            relevanceFilter === 'RELEVANT'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
              : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <span>🎯</span> Recommended Technical Roles
        </button>
        <button
          onClick={() => { setRelevanceFilter('ALL'); setPage(1); }}
          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition ${
            relevanceFilter === 'ALL'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
              : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <span>🌐</span> All Discovered Vacancies
        </button>
        <button
          onClick={() => { setRelevanceFilter('IRRELEVANT'); setPage(1); }}
          className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition ${
            relevanceFilter === 'IRRELEVANT'
              ? 'bg-amber-600 text-white shadow-md shadow-amber-500/20'
              : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <span>⛔</span> Filtered Non-Technical Roles
        </button>
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-3.5 sm:p-4 space-y-3.5">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex-1 min-w-0">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by job title, employer, or technical keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 sm:px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold rounded-lg shadow-sm transition flex items-center justify-center gap-2 flex-shrink-0"
          >
            <Search className="w-4 h-4" /> Search
          </button>
        </form>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider mr-1">
            <SlidersHorizontal className="w-3.5 h-3.5" /> Filters:
          </div>

          {/* Work Mode */}
          <select
            value={workModeFilter}
            onChange={(e) => {
              setWorkModeFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs rounded-lg border border-slate-200 px-2.5 py-1.5 bg-slate-50 text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Work Modes</option>
            <option value="REMOTE">Remote</option>
            <option value="HYBRID">Hybrid</option>
            <option value="ON_SITE">On-site</option>
          </select>

          {/* Location */}
          <select
            value={locationFilter}
            onChange={(e) => {
              setLocationFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs rounded-lg border border-slate-200 px-2.5 py-1.5 bg-slate-50 text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Locations</option>
            <option value="Bengaluru">Bengaluru</option>
            <option value="Hyderabad">Hyderabad</option>
            <option value="Pune">Pune</option>
            <option value="Mumbai">Mumbai</option>
            <option value="Gurugram">Gurugram</option>
            <option value="Noida">Noida</option>
          </select>

          {/* Employment Type */}
          <select
            value={employmentTypeFilter}
            onChange={(e) => {
              setEmploymentTypeFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs rounded-lg border border-slate-200 px-2.5 py-1.5 bg-slate-50 text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Employment Types</option>
            <option value="FULL_TIME">Full-Time</option>
            <option value="INTERNSHIP">Internship</option>
            <option value="CONTRACT">Contract</option>
          </select>

          {/* Eligibility */}
          <select
            value={eligibilityFilter}
            onChange={(e) => {
              setEligibilityFilter(e.target.value);
              setPage(1);
            }}
            className="text-xs rounded-lg border border-slate-200 px-2.5 py-1.5 bg-slate-50 text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Eligibility</option>
            <option value="ELIGIBLE">Eligible</option>
            <option value="ELIGIBLE_WITH_CONDITIONS">Eligible with Conditions</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
          </select>

          {/* Sort By */}
          <div className="w-full sm:w-auto sm:ml-auto flex items-center justify-between sm:justify-start gap-2 pt-1 sm:pt-0">
            <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
              <ArrowUpDown className="w-3 h-3" /> Sort:
            </span>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="text-xs rounded-lg border border-slate-200 px-2.5 py-1.5 bg-slate-50 text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="score">Match Score (High to Low)</option>
              <option value="date">Date Discovered (Newest)</option>
              <option value="company">Employer (A-Z)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between px-1">
        <p className="text-sm font-medium text-slate-600">
          Showing <span className="font-bold text-slate-900">{jobs.length}</span> of{' '}
          <span className="font-bold text-slate-900">{total}</span> canonical vacancies
        </p>
      </div>

      {/* Job Cards Grid */}
      {isLoading ? (
        <div className="bg-white rounded-xl p-16 text-center border border-slate-200">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-600 font-medium text-sm">Evaluating live canonical job matches...</p>
        </div>
      ) : error ? (
        <div className="bg-white rounded-xl p-12 text-center border border-rose-200 space-y-4">
          <div className="w-12 h-12 bg-rose-50 text-rose-600 rounded-full flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-800">Failed to Load Job Feed</h3>
          <p className="text-slate-500 text-xs max-w-md mx-auto">{error}</p>
          <button
            onClick={() => fetchJobs()}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition"
          >
            Retry Connection
          </button>
        </div>
      ) : jobs.length === 0 ? (
        <div className="bg-white rounded-xl p-16 text-center border border-slate-200 space-y-3">
          <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto text-slate-400">
            <Briefcase className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-800">No vacancies match your active filters</h3>
          <p className="text-slate-500 text-xs max-w-md mx-auto">
            Try adjusting your search criteria, clearing location filters, or running discovery to pull
            fresh postings from integrated sources.
          </p>
          <button
            onClick={() => {
              setSearchQuery('');
              setLocationFilter('');
              setWorkModeFilter('');
              setEmploymentTypeFilter('');
              setEligibilityFilter('');
              setMinScore(0);
              fetchJobs();
            }}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
          >
            Clear All Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-5">
          {jobs.map((job) => (
            <div
              key={job.id}
              onClick={() => navigate(`/jobs/${job.id}`)}
              className="bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition cursor-pointer flex flex-col p-4 sm:p-5 relative group min-w-0 overflow-hidden"
            >
              {/* Top Row: Company & Bookmark */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-base flex-shrink-0">
                    {job.company_name?.charAt(0) || 'J'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider truncate">
                      {job.company_name}
                    </h4>
                    <h3 className="text-sm sm:text-base font-bold text-slate-900 group-hover:text-indigo-600 transition truncate">
                      {job.title}
                    </h3>
                  </div>
                </div>

                <button
                  onClick={(e) => handleToggleSave(job, e)}
                  title={job.is_saved ? 'Remove bookmark' : 'Bookmark job'}
                  className={`p-1.5 rounded-lg border transition flex-shrink-0 ${
                    job.is_saved
                      ? 'bg-indigo-50 border-indigo-200 text-indigo-600'
                      : 'border-slate-200 text-slate-400 hover:text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {job.is_saved ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
                </button>
              </div>

              {/* Tags: Location, Mode, Type */}
              <div className="flex flex-wrap items-center gap-1.5 mb-4 text-xs text-slate-600">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 font-medium">
                  <MapPin className="w-3 h-3 text-slate-500" />
                  {job.location || 'India'}
                </span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 font-medium">
                  <Layers className="w-3 h-3 text-slate-500" />
                  {job.work_mode || 'ON_SITE'}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-100 font-medium">
                  {job.employment_type?.replace('_', ' ') || 'Full Time'}
                </span>
                {job.is_relevant === false ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                    ⛔ Out-of-Scope ({job.role_family?.replace(/_/g, ' ')})
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">
                    🎯 {job.role_family?.replace(/_/g, ' ') || 'Technical'}
                  </span>
                )}
              </div>

              {/* Match Score & Eligibility Badge */}
              <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 mb-4 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">
                    Composite Match
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-lg font-extrabold text-indigo-600">
                      {Math.round(job.match_score)}%
                    </span>
                    <span className="text-xs text-slate-400 font-medium">SBERT Rank</span>
                  </div>
                </div>
                <div>{getEligibilityBadge(job.eligibility_status)}</div>
              </div>

              {/* Matched Skills Snippet */}
              {job.matched_skills && job.matched_skills.length > 0 && (
                <div className="mb-4 flex-1">
                  <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
                    Verified Competencies
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {job.matched_skills.slice(0, 3).map((skill, idx) => (
                      <SkillBadge
                        key={idx}
                        skill={skill}
                        variant="matched"
                        size="xs"
                      />
                    ))}
                    {job.matched_skills.length > 3 && (
                      <span className="text-[11px] text-slate-400 font-medium self-center pl-1">
                        +{job.matched_skills.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Footer */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 mt-auto">
                {job.salary_range ? (
                  <span className="font-semibold text-slate-800">{job.salary_range}</span>
                ) : (
                  <span className="text-slate-400">Competitive salary</span>
                )}

                <div className="flex items-center gap-1 text-indigo-600 font-semibold group-hover:translate-x-0.5 transition">
                  Details <ChevronRight className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white px-4 py-3 border border-slate-200 rounded-xl">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-xs font-medium text-slate-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};
