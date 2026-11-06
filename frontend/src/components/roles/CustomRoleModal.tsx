import React, { useState } from 'react';
import { X, Plus, Sparkles, AlertCircle } from 'lucide-react';
import { CustomRolePayload, ConfirmedRoleItem } from '../../types/api';
import { api } from '../../services/api';
import { useCandidate } from '../../context/CandidateContext';

interface CustomRoleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRoleAdded?: (role: ConfirmedRoleItem) => void;
}

export const CustomRoleModal: React.FC<CustomRoleModalProps> = ({ isOpen, onClose, onRoleAdded }) => {
  const { candidateId, toggleSelectRole, addToast } = useCandidate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [skillInput, setSkillInput] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddSkill = () => {
    const trimmed = skillInput.trim();
    if (!trimmed) return;
    if (!skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
    }
    setSkillInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleRemoveSkill = (idx: number) => {
    setSkills(skills.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Please provide a role title.');
      return;
    }
    if (!candidateId) {
      setError('No active candidate profile found. Please upload a resume first.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const payload: CustomRolePayload = {
        role_title: title.trim(),
        role_description: description.trim() || undefined,
        skills: skills.length > 0 ? skills : undefined,
      };

      const customRole = await api.addCustomRole(candidateId, payload);
      toggleSelectRole(customRole);
      addToast('success', `Added custom role "${customRole.role_title}" to selected roles!`);

      if (onRoleAdded) {
        onRoleAdded(customRole);
      }

      // Reset form and close
      setTitle('');
      setDescription('');
      setSkills([]);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to add custom role';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-100/80 text-indigo-700">
              <Plus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800">Add Custom Career Role</h3>
              <p className="text-xs text-slate-500">Target a specialized role outside standard recommendations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 text-xs bg-rose-50 border border-rose-200 text-rose-700 rounded-lg">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Role Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. AI Workflow Architect, Platform Reliability Engineer"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Description / Target Focus
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Describe your ideal focus areas, target team, or technical domains..."
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Specific Skills Required
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type skill & press Enter (e.g. LangChain, Kubernetes)"
                className="flex-1 px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={handleAddSkill}
                className="px-3 py-2 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg border border-slate-200"
              >
                Add
              </button>
            </div>

            {skills.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {skills.map((s, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-md border border-indigo-200"
                  >
                    <span>{s}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(idx)}
                      className="text-indigo-400 hover:text-indigo-700 ml-0.5"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="p-3 bg-amber-50 rounded-lg border border-amber-200/80 text-[11px] text-amber-800 flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <span>
              Custom roles will be saved to your confirmed roles catalogue and analyzed against your resume without fabricating synthetic match scores.
            </span>
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-all disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>{isSubmitting ? 'Saving...' : 'Add Custom Role'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

