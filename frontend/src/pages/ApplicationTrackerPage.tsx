import React, { useState, useEffect } from 'react';
import {
  ClipboardList,
  Plus,
  Search,
  Clock,
  Trash2,
  ExternalLink,
  Edit2,
} from 'lucide-react';
import { api } from '../services/api';
import { useCandidate } from '../context/CandidateContext';
import { ApplicationItem, ApplicationStatsResponse } from '../types/api';

const STATUS_COLUMNS = [
  { id: 'ALL', label: 'All Stages' },
  { id: 'APPLIED', label: 'Applied', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  { id: 'ASSESSMENT', label: 'Assessment', color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  { id: 'INTERVIEW', label: 'Interview', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  { id: 'OFFER', label: 'Offer', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  { id: 'REJECTED', label: 'Rejected', color: 'bg-slate-100 text-slate-600 border-slate-200' },
];

export const ApplicationTrackerPage: React.FC = () => {
  const { candidateId, addToast } = useCandidate();

  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [stats, setStats] = useState<ApplicationStatsResponse | null>(null);
  const [activeStatus, setActiveStatus] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // New Application Modal State
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [companyName, setCompanyName] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [applicationUrl, setApplicationUrl] = useState('');
  const [initialStatus, setInitialStatus] = useState('APPLIED');
  const [notes, setNotes] = useState('');

  // Status Change State
  const [updatingApp, setUpdatingApp] = useState<ApplicationItem | null>(null);
  const [newStatus, setNewStatus] = useState('');
  const [statusNotes, setStatusNotes] = useState('');

  const fetchApplications = async () => {
    setIsLoading(true);
    try {
      const activeCandId = candidateId || 3;
      const [listRes, statsRes] = await Promise.all([
        api.getApplications(activeCandId, activeStatus, searchQuery),
        api.getApplicationStats(activeCandId),
      ]);
      setApplications(listRes.items || []);
      setStats(statsRes);
    } catch (err) {
      addToast('error', 'Failed to load applications.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [candidateId, activeStatus, searchQuery]);

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || !jobTitle.trim()) {
      addToast('error', 'Company name and job title are required.');
      return;
    }

    try {
      const activeCandId = candidateId || 3;
      await api.createApplication({
        candidate_id: activeCandId,
        company_name: companyName.trim(),
        job_title: jobTitle.trim(),
        application_url: applicationUrl.trim() || undefined,
        status: initialStatus,
        notes: notes.trim() || undefined,
      });
      addToast('success', `Application for ${jobTitle} at ${companyName} created!`);
      setIsNewModalOpen(false);
      setCompanyName('');
      setJobTitle('');
      setApplicationUrl('');
      setNotes('');
      fetchApplications();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to create application.';
      addToast('error', msg);
    }
  };

  const handleUpdateStatusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!updatingApp) return;

    try {
      await api.updateApplicationStatus(updatingApp.id, newStatus, statusNotes);
      addToast('success', `Status updated to ${newStatus}!`);
      setUpdatingApp(null);
      fetchApplications();
    } catch (err) {
      addToast('error', 'Failed to update application status.');
    }
  };

  const handleDelete = async (appId: number) => {
    try {
      await api.deleteApplication(appId);
      addToast('info', 'Application record removed.');
      setApplications(applications.filter((a) => a.id !== appId));
    } catch (err) {
      addToast('error', 'Failed to delete application.');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'OFFER':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">Offer Received 🎉</span>;
      case 'INTERVIEW':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">Interview Stage 🎙️</span>;
      case 'ASSESSMENT':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800">Assessment 📝</span>;
      case 'REJECTED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-600">Archived / Rejected</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800">Applied</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-xs font-bold mb-1.5">
            <ClipboardList className="w-3.5 h-3.5 text-indigo-600" /> Pipeline Management
          </div>
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">Application Tracker</h2>
          <p className="text-xs text-slate-500 mt-1">
            Track interview rounds, follow-up deadlines, notes, and overall recruiter response rate.
          </p>
        </div>

        <button
          onClick={() => setIsNewModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition"
        >
          <Plus className="w-4 h-4" /> Add Application
        </button>
      </div>

      {/* KPI Stats Grid */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
              {stats.total_applications}
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-semibold uppercase">Total Tracked</span>
              <span className="text-sm font-bold text-slate-900 block">{stats.total_applications} Roles</span>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
              {stats.interviews_scheduled}
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-semibold uppercase">Interviews</span>
              <span className="text-sm font-bold text-slate-900 block">{stats.interviews_scheduled} Scheduled</span>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
              {stats.offers_received}
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-semibold uppercase">Offers</span>
              <span className="text-sm font-bold text-emerald-700 block">{stats.offers_received} Received</span>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
              {stats.response_rate_percent}%
            </div>
            <div>
              <span className="text-[11px] text-slate-500 font-semibold uppercase">Response Rate</span>
              <span className="text-sm font-bold text-indigo-700 block">{stats.response_rate_percent}% Yield</span>
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          {STATUS_COLUMNS.map((col) => (
            <button
              key={col.id}
              onClick={() => setActiveStatus(col.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeStatus === col.id
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {col.label}
            </button>
          ))}
        </div>
        <div className="relative min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search company or title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Applications List */}
      {isLoading ? (
        <div className="bg-white rounded-xl p-16 text-center border border-slate-200">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-600 font-medium text-sm">Loading applications pipeline...</p>
        </div>
      ) : applications.length === 0 ? (
        <div className="bg-white rounded-xl p-16 text-center border border-slate-200 space-y-3">
          <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto text-slate-400">
            <ClipboardList className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-800">No applications in this stage</h3>
          <p className="text-slate-500 text-xs max-w-sm mx-auto">
            Apply to recommended vacancies from the Job Feed and record your submissions here to monitor your progress.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {applications.map((app) => (
            <div
              key={app.id}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:border-slate-300 transition flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
            >
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider">
                    {app.company_name}
                  </span>
                  <span className="text-slate-300">•</span>
                  <span className="text-xs text-slate-400">
                    Applied: {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : 'Recent'}
                  </span>
                  <div>{getStatusBadge(app.status)}</div>
                </div>

                <h3 className="text-base font-bold text-slate-900">{app.job_title}</h3>

                {app.notes && (
                  <p className="text-xs text-slate-600 italic bg-slate-50 p-2.5 rounded-lg border border-slate-100 max-w-2xl">
                    "{app.notes}"
                  </p>
                )}

                {/* History Snippet */}
                {app.status_history && app.status_history.length > 1 && (
                  <div className="text-[11px] text-slate-400 flex items-center gap-1.5 pt-1">
                    <Clock className="w-3 h-3" />
                    <span>
                      Last transitioned to {app.status} on{' '}
                      {new Date(app.status_history[0].changed_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 self-end md:self-center">
                <button
                  onClick={() => {
                    setUpdatingApp(app);
                    setNewStatus(app.status);
                    setStatusNotes('');
                  }}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1"
                >
                  <Edit2 className="w-3.5 h-3.5" /> Update Status
                </button>

                {app.application_url && (
                  <a
                    href={app.application_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 text-slate-400 hover:text-indigo-600 rounded-lg border border-slate-200"
                    title="Open application URL"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}

                <button
                  onClick={() => handleDelete(app.id)}
                  className="p-2 text-slate-400 hover:text-rose-600 rounded-lg border border-slate-200"
                  title="Delete application"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New Application Modal */}
      {isNewModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateApplication}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4"
          >
            <h3 className="text-lg font-bold text-slate-900">Record Job Application</h3>
            <p className="text-xs text-slate-500">
              Only log applications that have actually been submitted on the company career portal.
            </p>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Company Name *</label>
              <input
                type="text"
                required
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Swiggy, Cred, Groww"
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Position / Job Title *</label>
              <input
                type="text"
                required
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g. Backend Software Engineer"
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Application URL (optional)</label>
              <input
                type="url"
                value={applicationUrl}
                onChange={(e) => setApplicationUrl(e.target.value)}
                placeholder="https://..."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Initial Stage</label>
              <select
                value={initialStatus}
                onChange={(e) => setInitialStatus(e.target.value)}
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="APPLIED">Applied</option>
                <option value="ASSESSMENT">Assessment</option>
                <option value="INTERVIEW">Interview</option>
                <option value="OFFER">Offer</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Application notes, referral contact, or interview details..."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                rows={2}
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsNewModalOpen(false)}
                className="px-4 py-2 border border-slate-200 text-xs font-semibold rounded-lg text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm"
              >
                Save Record
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Update Status Dialog */}
      {updatingApp && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleUpdateStatusSubmit}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4"
          >
            <h3 className="text-lg font-bold text-slate-900">
              Update Stage: {updatingApp.job_title}
            </h3>
            <p className="text-xs text-slate-500">{updatingApp.company_name}</p>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">New Stage</label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="APPLIED">Applied</option>
                <option value="ASSESSMENT">Assessment / Coding Round</option>
                <option value="INTERVIEW">Interview Round</option>
                <option value="OFFER">Offer Extended</option>
                <option value="REJECTED">Rejected / Closed</option>
                <option value="WITHDRAWN">Withdrawn</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Transition Notes / Feedback
              </label>
              <textarea
                value={statusNotes}
                onChange={(e) => setStatusNotes(e.target.value)}
                placeholder="e.g. Cleared technical screening; scheduled system design on Friday."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                rows={3}
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setUpdatingApp(null)}
                className="px-4 py-2 border border-slate-200 text-xs font-semibold rounded-lg text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm"
              >
                Update Stage
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
