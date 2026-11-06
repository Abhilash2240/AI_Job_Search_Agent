import React, { createContext, useContext, useState, useEffect } from 'react';
import { ConfirmedRoleItem, ResumeUploadResponse } from '../types/api';
import { api } from '../services/api';

interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

interface CandidateContextType {
  candidateId: number | null;
  setCandidateId: (id: number | null) => void;
  candidateData: ResumeUploadResponse | null;
  setCandidateData: (data: ResumeUploadResponse | null) => void;
  selectedRoles: ConfirmedRoleItem[];
  setSelectedRoles: React.Dispatch<React.SetStateAction<ConfirmedRoleItem[]>>;
  toggleSelectRole: (role: ConfirmedRoleItem) => void;
  isRoleSelected: (roleId: string) => boolean;
  selectAllRoles: (roles: ConfirmedRoleItem[]) => void;
  deselectAllRoles: () => void;
  toasts: ToastMessage[];
  addToast: (type: 'success' | 'error' | 'info', message: string) => void;
  removeToast: (id: string) => void;
  refreshCandidate: () => Promise<void>;
}

const CandidateContext = createContext<CandidateContextType | undefined>(undefined);

export const CandidateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Check if existing candidateId was saved in session or default to 1
  const [candidateId, setCandidateIdState] = useState<number | null>(() => {
    const saved = sessionStorage.getItem('ai_job_search_candidate_id');
    return saved ? parseInt(saved, 10) : 1;
  });

  const [candidateData, setCandidateData] = useState<ResumeUploadResponse | null>(null);
  
  // Initialize selectedRoles from sessionStorage for persistence across browser refresh
  const [selectedRoles, setSelectedRolesState] = useState<ConfirmedRoleItem[]>(() => {
    const savedId = sessionStorage.getItem('ai_job_search_candidate_id') || '1';
    const savedRoles = sessionStorage.getItem(`ai_job_search_selected_roles_${savedId}`);
    if (savedRoles) {
      try {
        return JSON.parse(savedRoles);
      } catch (e) {
        return [];
      }
    }
    return [];
  });

  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const setSelectedRoles: React.Dispatch<React.SetStateAction<ConfirmedRoleItem[]>> = (action) => {
    setSelectedRolesState((prev) => {
      const next = typeof action === 'function' ? action(prev) : action;
      if (candidateId) {
        sessionStorage.setItem(`ai_job_search_selected_roles_${candidateId}`, JSON.stringify(next));
      }
      return next;
    });
  };

  const setCandidateId = (id: number | null) => {
    setCandidateIdState(id);
    if (id !== null) {
      sessionStorage.setItem('ai_job_search_candidate_id', id.toString());
      // Load candidate-specific saved roles
      const savedRoles = sessionStorage.getItem(`ai_job_search_selected_roles_${id}`);
      if (savedRoles) {
        try {
          setSelectedRolesState(JSON.parse(savedRoles));
        } catch (e) {
          setSelectedRolesState([]);
        }
      } else {
        setSelectedRolesState([]);
      }
    } else {
      sessionStorage.removeItem('ai_job_search_candidate_id');
      setSelectedRolesState([]);
    }
  };

  const addToast = (type: 'success' | 'error' | 'info', message: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => removeToast(id), 4000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const isRoleSelected = (roleId: string) => {
    return selectedRoles.some((r) => r.role_id === roleId);
  };

  const toggleSelectRole = (role: ConfirmedRoleItem) => {
    setSelectedRoles((prev) => {
      const exists = prev.some((r) => r.role_id === role.role_id);
      if (exists) {
        return prev.filter((r) => r.role_id !== role.role_id);
      } else {
        return [...prev, role];
      }
    });
  };

  const selectAllRoles = (roles: ConfirmedRoleItem[]) => {
    setSelectedRoles((prev) => {
      const prevIds = new Set(prev.map((r) => r.role_id));
      const newItems = roles.filter((r) => !prevIds.has(r.role_id));
      return [...prev, ...newItems];
    });
  };

  const deselectAllRoles = () => {
    setSelectedRoles([]);
  };

  const refreshCandidate = async () => {
    if (!candidateId) return;
    try {
      const data = await api.getCandidateProfile(candidateId);
      setCandidateData(data);
      // Fetch confirmed roles from DB to keep UI synchronized with database records
      const confRes = await api.getConfirmedRoles(candidateId);
      if (confRes.roles && confRes.roles.length > 0) {
        setSelectedRolesState(confRes.roles);
        sessionStorage.setItem(`ai_job_search_selected_roles_${candidateId}`, JSON.stringify(confRes.roles));
      }
    } catch (err) {
      console.warn('Candidate data could not be retrieved:', err);
      // If the candidate doesn't exist (e.g. purged/deleted invalid document), fall back to primary candidate
      if (candidateId !== 1) {
        setCandidateId(1);
      }
    }
  };

  useEffect(() => {
    refreshCandidate();
  }, [candidateId]);

  return (
    <CandidateContext.Provider
      value={{
        candidateId,
        setCandidateId,
        candidateData,
        setCandidateData,
        selectedRoles,
        setSelectedRoles,
        toggleSelectRole,
        isRoleSelected,
        selectAllRoles,
        deselectAllRoles,
        toasts,
        addToast,
        removeToast,
        refreshCandidate,
      }}
    >
      {children}
    </CandidateContext.Provider>
  );
};

export const useCandidate = () => {
  const context = useContext(CandidateContext);
  if (!context) {
    throw new Error('useCandidate must be used within a CandidateProvider');
  }
  return context;
};
