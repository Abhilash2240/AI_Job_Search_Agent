import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Building2,
  Search,
  Globe,
  Briefcase,
  ExternalLink,
  ShieldAlert,
  Users,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Info,
} from 'lucide-react';
import { api } from '../services/api';
import { CompanyListItem, CompanyResearchResponse } from '../types/api';

export const CompanyResearchPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);

  // Fetch companies list
  const { data: companiesData, isLoading: isLoadingCompanies } = useQuery({
    queryKey: ['companiesList', searchQuery],
    queryFn: () => api.getCompanies({ limit: 50, search: searchQuery || undefined }),
  });

  // Fetch detailed research for selected company
  const {
    data: researchData,
    isLoading: isLoadingResearch,
  } = useQuery<CompanyResearchResponse | null>({
    queryKey: ['companyResearch', selectedCompanyId],
    queryFn: () => (selectedCompanyId ? api.getCompanyResearch(selectedCompanyId) : null),
    enabled: !!selectedCompanyId,
  });

  const companies: CompanyListItem[] = companiesData?.items || companiesData?.companies || [];

  return (
    <div className="space-y-6 w-full min-w-0">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-5 sm:p-6 rounded-2xl shadow-sm border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Building2 className="w-5 h-5 text-indigo-400 flex-shrink-0" />
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                Company & Sourcing Intelligence
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight break-words">Company Research & Outreach Directory</h1>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
              Inspect vetted enterprise and startup career boards, verified contact points, and verified canonical job vacancies across 800+ tracked employers.
            </p>
          </div>
          <div className="flex items-center gap-3 bg-white/10 px-4 py-2.5 rounded-xl border border-white/15 backdrop-blur-sm self-start md:self-auto flex-shrink-0">
            <span className="text-xs text-slate-300">Total Tracked Employers:</span>
            <span className="text-lg font-bold text-white">{companiesData?.total || 819}</span>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 items-start w-full min-w-0">
        {/* Left Column: Company Search & List */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col max-h-[800px]">
          {/* Search Box */}
          <div className="p-4 border-b border-slate-200 bg-slate-50">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by company name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>
            <div className="flex justify-between items-center mt-2 text-xs text-slate-500">
              <span>Showing {companies.length} employers</span>
              <span>Click any company to inspect</span>
            </div>
          </div>

          {/* List items */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {isLoadingCompanies ? (
              <div className="p-8 text-center text-slate-400 text-sm">
                Loading companies directory...
              </div>
            ) : companies.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                No employers found matching "{searchQuery}"
              </div>
            ) : (
              companies.map((company) => {
                const isSelected = selectedCompanyId === company.id;
                return (
                  <button
                    key={company.id}
                    onClick={() => setSelectedCompanyId(company.id)}
                    className={`w-full text-left p-4 transition-colors flex items-center justify-between ${
                      isSelected
                        ? 'bg-indigo-50/70 border-l-4 border-indigo-600'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="min-w-0 pr-3">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-slate-900 truncate">
                          {company.canonical_name || company.normalized_name}
                        </span>
                        {company.relevance_category && (
                          <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                            {company.relevance_category}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                        {company.primary_domain ? (
                          <span className="truncate max-w-[200px]">{company.primary_domain}</span>
                        ) : (
                          <span className="text-slate-400">Domain unlisted</span>
                        )}
                        <span>•</span>
                        <span>{company.career_sources_count || 0} career sources</span>
                      </div>
                    </div>
                    <ArrowRight className={`w-4 h-4 shrink-0 ${isSelected ? 'text-indigo-600' : 'text-slate-300'}`} />
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Company Intelligence Detail */}
        <div className="lg:col-span-7">
          {!selectedCompanyId ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500">
              <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-800">Select an Employer</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                Choose a company from the left panel to inspect its verified career pages, ATS integrations, contacts, and active canonical vacancies.
              </p>
            </div>
          ) : isLoadingResearch ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-3" />
              <p className="text-xs font-medium">Aggregating employer intelligence and vacancies...</p>
            </div>
          ) : researchData ? (
            <div className="space-y-6">
              {/* Company Profile Header */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">{researchData.name}</h2>
                    {researchData.primary_domain && (
                      <a
                        href={`https://${researchData.primary_domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-700 hover:underline mt-1"
                      >
                        <Globe className="w-3.5 h-3.5" />
                        <span>{researchData.primary_domain}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Tracked Employer
                    </span>
                    {researchData.relevance_category && (
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                        {researchData.relevance_category.toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>

                {/* Sourcing Channels */}
                <div className="pt-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                    Discovered Career & ATS Sourcing Channels
                  </h4>
                  {(!researchData.career_sources || researchData.career_sources.length === 0) ? (
                    <p className="text-xs text-slate-400 italic">No direct ATS career sources indexed yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {researchData.career_sources.map((src) => (
                        <div
                          key={src.id}
                          className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs"
                        >
                          <div className="min-w-0 pr-3">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-slate-800 uppercase tracking-wide">
                                {src.ats_provider || 'Direct Career Board'}
                              </span>
                              <span className="text-[10px] bg-indigo-50 text-indigo-700 font-medium px-2 py-0.5 rounded border border-indigo-200">
                                {src.source_document || 'Careers Page'}
                              </span>
                            </div>
                            <p className="text-slate-500 truncate mt-0.5">{src.url}</p>
                          </div>
                          <a
                            href={src.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium px-2.5 py-1.5 rounded-lg hover:bg-white border border-transparent hover:border-slate-200 transition-colors"
                          >
                            <span>Visit</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Outreach Authorization Policy Alert */}
              <div className="bg-amber-50 rounded-2xl border border-amber-200 p-5">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-amber-900">
                      Outreach Policy & Candidate Authorization Rule
                    </h4>
                    <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                      Emails and job applications must never be automatically dispatched without candidate approval. Automated mass-emailing is strictly disabled. Candidates must manually review and authorize each contact interaction.
                    </p>
                  </div>
                </div>
              </div>

              {/* Verified vs Unverified Contacts */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-sm font-bold text-slate-900">Contact Points</h3>
                  </div>
                  <span className="text-xs text-slate-500">
                    {(researchData.contacts || []).filter((c) => c.is_verified).length} verified contact(s)
                  </span>
                </div>

                {(!researchData.contacts || researchData.contacts.length === 0) ? (
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
                    <Info className="w-4 h-4 text-slate-400" />
                    <span>No talent acquisition contacts confirmed for this employer yet.</span>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {researchData.contacts.map((contact, idx: number) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl border border-slate-200 bg-white flex items-center justify-between"
                      >
                        <div>
                          <p className="text-xs font-mono font-semibold text-slate-900">{contact.email}</p>
                          <p className="text-[11px] text-slate-500 mt-0.5">{contact.source || 'Company Registry'}</p>
                        </div>
                        {contact.is_verified ? (
                          <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
                            Verified
                          </span>
                        ) : (
                          <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            Unverified
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Active Canonical Vacancies */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-sm font-bold text-slate-900">
                      Active Canonical Vacancies ({researchData.active_vacancies?.length || 0})
                    </h3>
                  </div>
                  <span className="text-xs text-slate-500">Live verified postings</span>
                </div>

                {(!researchData.active_vacancies || researchData.active_vacancies.length === 0) ? (
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 text-center">
                    No active canonical vacancies currently recorded for this company.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {researchData.active_vacancies.map((job) => (
                      <div
                        key={job.id}
                        className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-xs transition-all bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-slate-900">{job.title}</span>
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Active
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                            <span>{job.location || 'Location Not Specified'}</span>
                            <span>•</span>
                            <span>{job.work_mode || job.employment_type || 'Full-time'}</span>
                          </div>
                        </div>
                        <Link
                          to={`/jobs/${job.id}`}
                          className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors self-start sm:self-auto"
                        >
                          <span>Inspect Job & Match</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
