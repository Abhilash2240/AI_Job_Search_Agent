import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  Play,
  RotateCw,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Database,
  Filter,
  Cpu,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import { PipelineExecutionItem } from '../types/api';

const STAGE_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  extraction: 'Extraction',
  deduplication: 'Deduplication',
  verification: 'Verification',
  embeddings: 'Embeddings',
  matching: 'Matching',
};

export const PipelineMonitorPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedStages, setSelectedStages] = useState<string[]>([
    'discovery',
    'extraction',
    'deduplication',
    'verification',
    'embeddings',
    'matching',
  ]);
  const [executionMessage, setExecutionMessage] = useState<string | null>(null);

  // Status & history queries
  const { data: statusData } = useQuery({
    queryKey: ['pipelineStatus'],
    queryFn: () => api.getPipelineStatus(),
    refetchInterval: 5000,
  });

  const { data: historyData, isLoading: isLoadingHistory } = useQuery({
    queryKey: ['pipelineHistory'],
    queryFn: () => api.getPipelineHistory(20),
    refetchInterval: 5000,
  });

  const { data: statsData } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: () => api.getDashboardStats(),
  });

  // Run pipeline mutation
  const runMutation = useMutation({
    mutationFn: () =>
      api.runPipeline({
        trigger_type: 'MANUAL',
        stages: selectedStages,
        force_matching: false,
      }),
    onSuccess: (res) => {
      setExecutionMessage(`Pipeline execution started: Run ID ${res.run_id}`);
      queryClient.invalidateQueries({ queryKey: ['pipelineStatus'] });
      queryClient.invalidateQueries({ queryKey: ['pipelineHistory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardStats'] });
    },
    onError: (err: any) => {
      setExecutionMessage(`Execution failed: ${err?.response?.data?.detail || err?.message || 'Error'}`);
    },
  });

  const toggleStage = (stage: string) => {
    setSelectedStages((prev) =>
      prev.includes(stage) ? prev.filter((s) => s !== stage) : [...prev, stage]
    );
  };

  const isRunning = statusData?.is_running;
  const history: PipelineExecutionItem[] = historyData?.executions || historyData?.items || [];

  const renderStagesBadges = (stagesRaw: any) => {
    if (!stagesRaw) return <span className="text-slate-400">All stages</span>;

    let stagesObj: Record<string, any> = {};
    if (typeof stagesRaw === 'string') {
      try {
        stagesObj = JSON.parse(stagesRaw);
      } catch {
        return <span className="font-mono text-[11px] text-slate-500">{stagesRaw}</span>;
      }
    } else if (typeof stagesRaw === 'object') {
      stagesObj = stagesRaw;
    }

    const keys = Object.keys(stagesObj);
    if (keys.length === 0) return <span className="text-slate-400">Standard</span>;

    return (
      <div className="flex flex-wrap gap-1 max-w-[220px]">
        {keys.map((key) => {
          const info = stagesObj[key];
          const st = (typeof info === 'object' && info?.status ? info.status : 'COMPLETED').toUpperCase();
          const label = STAGE_LABELS[key.toLowerCase()] || key;

          let badgeCls = 'bg-slate-50 text-slate-600 border-slate-200';
          if (st === 'COMPLETED') {
            badgeCls = 'bg-emerald-50 text-emerald-700 border-emerald-200';
          } else if (st === 'RUNNING') {
            badgeCls = 'bg-amber-50 text-amber-700 border-amber-200';
          } else if (st === 'FAILED') {
            badgeCls = 'bg-rose-50 text-rose-700 border-rose-200';
          } else if (st === 'SKIPPED') {
            badgeCls = 'bg-slate-50 text-slate-400 border-slate-200';
          }

          return (
            <span
              key={key}
              title={`${label}: ${st}`}
              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${badgeCls}`}
            >
              {label}
            </span>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6 w-full min-w-0">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-5 sm:p-6 rounded-2xl shadow-sm border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-5 h-5 text-indigo-400 flex-shrink-0" />
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                Pipeline Orchestration & Monitoring
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight break-words">Data Ingestion & AI Matching Lifecycle</h1>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
              Monitor discovery, extraction, cross-provider deduplication, fine-tuned SBERT vector embeddings, and candidate matching.
            </p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0 self-start md:self-auto">
            <div
              className={`px-3.5 sm:px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 border ${
                isRunning
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse'
                  : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-amber-400' : 'bg-emerald-400'}`} />
              <span>{isRunning ? 'PIPELINE ACTIVE' : 'PIPELINE IDLE / READY'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span className="font-semibold">Tracked Companies</span>
            <Database className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{statsData?.system?.total_companies ?? 819}</div>
          <span className="text-[11px] text-slate-500">Greenhouse, Lever & Career sites</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span className="font-semibold">Canonical Vacancies</span>
            <Layers className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{statsData?.system?.total_canonical_vacancies ?? 136}</div>
          <span className="text-[11px] text-emerald-600 font-medium">Deduplicated & Verified</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span className="font-semibold">Job Embeddings</span>
            <Cpu className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {statsData?.system?.job_embeddings ?? statsData?.system?.verified_active_vacancies ?? 136}
          </div>
          <span className="text-[11px] text-slate-500">384-d fine-tuned SBERT</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span className="font-semibold">Matches Evaluated</span>
            <Filter className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{statsData?.recommendations?.total_matches_evaluated ?? 136}</div>
          <span className="text-[11px] text-slate-500">Ranked with explanations</span>
        </div>
      </div>

      {/* Pipeline Trigger & Execution Controls */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <h3 className="text-base font-bold text-slate-900 mb-1">Pipeline Execution Controls</h3>
        <p className="text-xs text-slate-500 mb-4">
          Trigger controlled execution of specific stages or the full end-to-end ingestion pipeline.
        </p>

        {executionMessage && (
          <div className="mb-4 p-3 rounded-xl bg-indigo-50 border border-indigo-200 text-xs text-indigo-700 flex items-center justify-between">
            <span>{executionMessage}</span>
            <button onClick={() => setExecutionMessage(null)} className="text-indigo-500 font-bold hover:underline">
              Dismiss
            </button>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">Select Stages to Execute</label>
            <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
              {[
                { id: 'discovery', label: '1. Discovery' },
                { id: 'extraction', label: '2. Extraction' },
                { id: 'deduplication', label: '3. Deduplication' },
                { id: 'verification', label: '4. Verification' },
                { id: 'embeddings', label: '5. Embeddings' },
                { id: 'matching', label: '6. Matching' },
              ].map((stage) => {
                const active = selectedStages.includes(stage.id);
                return (
                  <button
                    key={stage.id}
                    type="button"
                    onClick={() => toggleStage(stage.id)}
                    className={`py-2 px-3 text-xs font-semibold rounded-xl border text-center transition-all ${
                      active
                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs'
                        : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    {stage.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="pt-2 flex items-center gap-3">
            <button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || isRunning || selectedStages.length === 0}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl transition-all shadow-xs"
            >
              {runMutation.isPending || isRunning ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Pipeline Executing...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Execute Pipeline Stages</span>
                </>
              )}
            </button>
            {isRunning && (
              <span className="text-xs text-amber-600 font-medium flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 animate-spin" />
                Active run in progress...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Execution History Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900">Pipeline Execution History</h3>
          </div>
          <span className="text-xs text-slate-500">{history.length} logged runs</span>
        </div>

        {isLoadingHistory ? (
          <div className="p-8 text-center text-slate-400 text-xs">Loading execution history...</div>
        ) : history.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No pipeline executions recorded yet. Run the pipeline above to trigger an ingestion cycle.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Run ID</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Stages</th>
                  <th className="py-3 px-4">Discovered</th>
                  <th className="py-3 px-4">Extracted</th>
                  <th className="py-3 px-4">Matches</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Started At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {history.map((run) => {
                  const duration =
                    run.completed_at && run.started_at
                      ? `${((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000).toFixed(1)}s`
                      : '—';

                  return (
                    <tr key={run.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-slate-900">
                        {run.run_id ? `${run.run_id.slice(0, 12)}...` : '—'}
                      </td>
                      <td className="py-3 px-4">
                        {run.status === 'COMPLETED' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" />
                            COMPLETED
                          </span>
                        ) : run.status === 'RUNNING' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase bg-amber-50 text-amber-700 border border-amber-200">
                            <RotateCw className="w-3 h-3 animate-spin" />
                            RUNNING
                          </span>
                        ) : (
                          <div className="flex flex-col gap-0.5">
                            <span
                              title={run.error_message || 'Pipeline stage failure'}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase bg-rose-50 text-rose-700 border border-rose-200 cursor-help w-fit"
                            >
                              <XCircle className="w-3 h-3" />
                              FAILED
                            </span>
                            {run.error_message && (
                              <span
                                title={run.error_message}
                                className="text-[10px] text-rose-500 font-normal truncate max-w-[150px] inline-flex items-center gap-0.5"
                              >
                                <AlertTriangle className="w-2.5 h-2.5 flex-shrink-0" />
                                {run.error_message}
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {renderStagesBadges(run.stages_executed)}
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-800">
                        {run.jobs_discovered ?? 0}
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-800">
                        {run.jobs_extracted ?? 0}
                      </td>
                      <td className="py-3 px-4 font-medium text-indigo-700">
                        {run.matches_computed ?? 0}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {duration}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
