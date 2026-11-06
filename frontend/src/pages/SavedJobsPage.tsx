import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bookmark,
  Search,
  MapPin,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Edit3,
  ChevronRight,
  Briefcase,
} from 'lucide-react';
import { api } from '../services/api';
import { useCandidate } from '../context/CandidateContext';
import { SavedJobItem } from '../types/api';

export const SavedJobsPage: React.FC = () => {
  const navigate = useNavigate();
  const { candidateId, addToast } = useCandidate();

  const [savedJobs, setSavedJobs] = useState<SavedJobItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingNotes, setEditingNotes] = useState('');

  const fetchSavedJobs = async () => {
    setIsLoading(true);
    try {
      const activeCandId = candidateId || 3;
      const data = await api.getSavedJobs(activeCandId, searchQuery);
      setSavedJobs(data.items || []);
    } catch (err) {
      addToast('error', 'Failed to load saved jobs.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSavedJobs();
  }, [candidateId]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchSavedJobs();
  };

  const handleUnsave = async (canonicalJobId: number, title?: string) => {
    try {
      const activeCandId = candidateId || 3;
      await api.unsaveJob(activeCandId, canonicalJobId);
      addToast('info', `Removed ${title || 'job'} from saved list.`);
      setSavedJobs(savedJobs.filter((s) => s.canonical_job_id !== canonicalJobId));
    } catch (err) {
      addToast('error', 'Failed to remove saved job.');
    }
  };

  const handleSaveNotes = async (savedJobId: number) => {
    try {
      await api.updateSavedJob(savedJobId, { notes: editingNotes });
      addToast('success', 'Updated notes.');
      setSavedJobs(
        savedJobs.map((s) => (s.id === savedJobId ? { ...s, notes: editingNotes } : s))
      );
      setEditingId(null);
    } catch (err) {
      addToast('error', 'Failed to update notes.');
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold mb-1.5">
            <Bookmark className="w-3.5 h-3.5 text-indigo-600" /> Bookmarked Opportunities
          </div>
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">Saved Jobs Management</h2>
          <p className="text-xs text-slate-500 mt-1">
            Track high-priority roles, keep personal interview notes, and receive real-time vacancy availability warnings.
          </p>
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search saved jobs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="text-xs pl-9 pr-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-64"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg"
          >
            Filter
          </button>
        </form>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="bg-white rounded-xl p-16 text-center border border-slate-200">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-600 font-medium text-sm">Loading saved bookmarks...</p>
        </div>
      ) : savedJobs.length === 0 ? (
        <div className="bg-white rounded-xl p-16 text-center border border-slate-200 space-y-3">
          <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto text-slate-400">
            <Bookmark className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-800">No saved jobs yet</h3>
          <p className="text-slate-500 text-xs max-w-sm mx-auto">
            Browse the AI-Ranked Job Feed and click the bookmark button on any vacancy you wish to track.
          </p>
          <button
            onClick={() => navigate('/jobs')}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition"
          >
            Explore Job Feed
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {savedJobs.map((item) => {
            const job = item.job;
            const isClosed = job && job.vacancy_status !== 'ACTIVE';

            return (
              <div
                key={item.id}
                className={`bg-white rounded-xl border p-5 transition shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
                  isClosed ? 'border-amber-200 bg-amber-50/20' : 'border-slate-200 hover:border-indigo-200'
                }`}
              >
                <div className="flex-1 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider">
                      {job?.company_name || 'Employer'}
                    </span>
                    <span className="text-slate-300">•</span>
                    <span className="text-xs font-mono text-slate-400">{job?.canonical_job_id}</span>

                    {/* Status Badge */}
                    {isClosed ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                        <AlertTriangle className="w-3 h-3 text-amber-600" /> Vacancy {job?.vacancy_status}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Active Vacancy
                      </span>
                    )}
                  </div>

                  <h3
                    onClick={() => navigate(`/jobs/${item.canonical_job_id}`)}
                    className="text-base font-bold text-slate-900 hover:text-indigo-600 cursor-pointer transition line-clamp-1"
                  >
                    {job?.title || `Canonical Job #${item.canonical_job_id}`}
                  </h3>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" /> {job?.location || 'India'}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Briefcase className="w-3.5 h-3.5 text-slate-400" /> {job?.workplace_type || 'Full Time'}
                    </span>
                    <span>Saved {new Date(item.created_at).toLocaleDateString()}</span>
                  </div>

                  {/* Notes Section */}
                  {editingId === item.id ? (
                    <div className="pt-2 flex items-center gap-2">
                      <input
                        type="text"
                        value={editingNotes}
                        onChange={(e) => setEditingNotes(e.target.value)}
                        placeholder="Add private note..."
                        className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 flex-1"
                      />
                      <button
                        onClick={() => handleSaveNotes(item.id)}
                        className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1.5 border border-slate-200 text-xs font-semibold text-slate-600 rounded-lg"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="pt-1 flex items-center gap-2">
                      <p className="text-xs text-slate-600 italic">
                        {item.notes ? `Note: "${item.notes}"` : 'No notes added.'}
                      </p>
                      <button
                        onClick={() => {
                          setEditingId(item.id);
                          setEditingNotes(item.notes || '');
                        }}
                        className="p-1 text-slate-400 hover:text-slate-600"
                        title="Edit note"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 self-end md:self-center">
                  <button
                    onClick={() => navigate(`/jobs/${item.canonical_job_id}`)}
                    className="px-3.5 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-lg transition flex items-center gap-1"
                  >
                    View Details <ChevronRight className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => handleUnsave(item.canonical_job_id, job?.title)}
                    className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                    title="Remove from saved"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
