import React, { useState } from 'react';
import {
  Cpu,
  Database,
  Sliders,
} from 'lucide-react';
import { useCandidate } from '../context/CandidateContext';

export const SettingsPage: React.FC = () => {
  const { candidateId, setCandidateId, refreshCandidate, addToast } = useCandidate();
  const [tempId, setTempId] = useState(candidateId ? candidateId.toString() : '1');

  const handleUpdateCandidateId = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(tempId, 10);
    if (isNaN(parsed) || parsed < 1) {
      addToast('error', 'Please enter a valid positive candidate ID.');
      return;
    }
    setCandidateId(parsed);
    addToast('success', `Switched active candidate to ID #${parsed}`);
    setTimeout(() => {
      refreshCandidate();
    }, 100);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Application Settings</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Configure active candidate context, model hyperparameters, and scoring weights.
        </p>
      </div>

      {/* Candidate Profile Switcher */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex items-center gap-2.5 mb-2">
          <Database className="w-5 h-5 text-indigo-600" />
          <h3 className="text-base font-bold text-slate-800">Active Candidate Profile</h3>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Switch between candidate profiles stored in the local SQLite database (`ai_job_search.db`).
        </p>

        <form onSubmit={handleUpdateCandidateId} className="flex items-center gap-3 max-w-md">
          <div className="flex-1">
            <input
              type="number"
              min="1"
              value={tempId}
              onChange={(e) => setTempId(e.target.value)}
              placeholder="Candidate ID (e.g. 1)"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-2xs transition-all"
          >
            Switch Profile
          </button>
        </form>
      </div>

      {/* SBERT Model Information */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex items-center gap-2.5 mb-2">
          <Cpu className="w-5 h-5 text-indigo-600" />
          <h3 className="text-base font-bold text-slate-800">SBERT Model Engine</h3>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Runtime checkpoint and architecture specifications.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500 block">Checkpoint Architecture</span>
            <span className="font-mono font-bold text-slate-800 block mt-0.5">
              fine-tuned-sbert-384d (all-MiniLM-L6-v2)
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500 block">Embedding Dimensions</span>
            <span className="font-mono font-bold text-slate-800 block mt-0.5">
              384 Dense Float32 Embeddings
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500 block">Local Path</span>
            <span className="font-mono text-slate-700 block mt-0.5 truncate">
              backend/models/trained_sbert/
            </span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500 block">Deployment Type</span>
            <span className="font-semibold text-emerald-700 block mt-0.5">
              Local Singleton in Process (Zero External API Calls)
            </span>
          </div>
        </div>
      </div>

      {/* Multi-Objective Scoring Weights */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex items-center gap-2.5 mb-2">
          <Sliders className="w-5 h-5 text-indigo-600" />
          <h3 className="text-base font-bold text-slate-800">Scoring Weights Matrix</h3>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Normalized component weights used to compute candidate career role rankings.
        </p>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <div>
              <span className="font-bold text-slate-800 block">Semantic Vector Similarity</span>
              <span className="text-slate-500 text-[11px]">SBERT dense cosine similarity</span>
            </div>
            <span className="font-mono font-bold text-indigo-600 text-sm">45% (0.45)</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <div>
              <span className="font-bold text-slate-800 block">Hard Skill Coverage</span>
              <span className="text-slate-500 text-[11px]">Verified skills in resume & projects</span>
            </div>
            <span className="font-mono font-bold text-emerald-600 text-sm">35% (0.35)</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <div>
              <span className="font-bold text-slate-800 block">Project Domain Alignment</span>
              <span className="text-slate-500 text-[11px]">Relevance of engineered projects</span>
            </div>
            <span className="font-mono font-bold text-amber-600 text-sm">15% (0.15)</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <div>
              <span className="font-bold text-slate-800 block">Education Alignment</span>
              <span className="text-slate-500 text-[11px]">Degree discipline & coursework</span>
            </div>
            <span className="font-mono font-bold text-cyan-600 text-sm">5% (0.05)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
