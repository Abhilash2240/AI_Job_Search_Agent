import axios from 'axios';
import {
  ResumeUploadResponse,
  CandidateProfile,
  DetailedProfileValidation,
  RecommendationsResponse,
  ConfirmedRolesResponse,
  ConfirmedRoleItem,
  CustomRolePayload,
} from '../types/api';

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000,
});

export const api = {
  // Resume upload & parsing
  uploadResume: async (file: File): Promise<ResumeUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<ResumeUploadResponse>('/resume/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Get profile
  getCandidateProfile: async (candidateId: number): Promise<ResumeUploadResponse> => {
    const res = await apiClient.get<ResumeUploadResponse>(`/resume/${candidateId}`);
    return res.data;
  },

  // In-depth profile validation
  getProfileValidation: async (candidateId: number): Promise<DetailedProfileValidation> => {
    const res = await apiClient.get<DetailedProfileValidation>(`/profile/${candidateId}/validation`);
    return res.data;
  },

  // Get recommendations (cached or compute)
  getRoleRecommendations: async (candidateId: number): Promise<RecommendationsResponse> => {
    const res = await apiClient.get<RecommendationsResponse>(`/profile/${candidateId}/recommendations`);
    return res.data;
  },

  // Re-generate recommendations with fresh weights/N
  generateRoleRecommendations: async (candidateId: number, topN = 10): Promise<RecommendationsResponse> => {
    const res = await apiClient.post<RecommendationsResponse>(`/profile/${candidateId}/recommendations?top_n=${topN}`);
    return res.data;
  },

  // Confirmed / selected roles
  getConfirmedRoles: async (candidateId: number): Promise<ConfirmedRolesResponse> => {
    const res = await apiClient.get<ConfirmedRolesResponse>(`/profile/${candidateId}/confirmed-roles`);
    return res.data;
  },

  saveConfirmedRoles: async (
    candidateId: number,
    roles: ConfirmedRoleItem[]
  ): Promise<ConfirmedRolesResponse> => {
    const res = await apiClient.post<ConfirmedRolesResponse>(`/profile/${candidateId}/confirmed-roles`, {
      roles,
    });
    return res.data;
  },

  deleteConfirmedRole: async (
    candidateId: number,
    roleId: string
  ): Promise<ConfirmedRolesResponse> => {
    const res = await apiClient.delete<ConfirmedRolesResponse>(
      `/profile/${candidateId}/confirmed-roles/${encodeURIComponent(roleId)}`
    );
    return res.data;
  },

  addCustomRole: async (
    candidateId: number,
    custom: CustomRolePayload
  ): Promise<ConfirmedRoleItem> => {
    const res = await apiClient.post<ConfirmedRoleItem>(`/profile/${candidateId}/custom-role`, custom);
    return res.data;
  },

  confirmSkill: async (
    candidateId: number,
    skill: string,
    category?: string
  ): Promise<CandidateProfile> => {
    const res = await apiClient.post<CandidateProfile>(`/profile/${candidateId}/skills/confirm`, {
      skill,
      category,
    });
    return res.data;
  },

  rejectSkill: async (
    candidateId: number,
    skill: string
  ): Promise<CandidateProfile> => {
    const res = await apiClient.post<CandidateProfile>(`/profile/${candidateId}/skills/reject`, {
      skill,
    });
    return res.data;
  },

  // ==========================================
  // Phase 8: Final Master Capabilities
  // ==========================================

  getDashboardStats: async (candidateId?: number) => {
    const params = candidateId ? { candidate_id: candidateId } : {};
    const res = await apiClient.get('/dashboard/stats', { params });
    return res.data;
  },

  getJobsFeed: async (params: Record<string, any> = {}) => {
    const res = await apiClient.get('/jobs/feed', { params });
    return res.data;
  },

  getJobDetail: async (jobId: string | number, candidateId?: number) => {
    const params = candidateId ? { candidate_id: candidateId } : {};
    const res = await apiClient.get(`/jobs/${jobId}`, { params });
    return res.data;
  },

  getSavedJobs: async (candidateId: number, search?: string) => {
    const params: Record<string, any> = {};
    if (search) params.search = search;
    const res = await apiClient.get(`/saved-jobs/candidate/${candidateId}`, { params });
    return res.data;
  },

  saveJob: async (candidateId: number, canonicalJobId: number, notes?: string) => {
    const res = await apiClient.post('/saved-jobs', {
      candidate_id: candidateId,
      canonical_job_id: canonicalJobId,
      notes,
    });
    return res.data;
  },

  unsaveJob: async (candidateId: number, canonicalJobId: number) => {
    const res = await apiClient.delete(`/saved-jobs/candidate/${candidateId}/job/${canonicalJobId}`);
    return res.data;
  },

  updateSavedJob: async (savedJobId: number, payload: { notes?: string; is_active?: boolean }) => {
    const res = await apiClient.patch(`/saved-jobs/${savedJobId}`, payload);
    return res.data;
  },

  getApplications: async (candidateId: number, status?: string, search?: string) => {
    const params: Record<string, any> = {};
    if (status && status !== 'ALL') params.status = status;
    if (search) params.search = search;
    const res = await apiClient.get(`/applications/candidate/${candidateId}`, { params });
    return res.data;
  },

  getApplicationStats: async (candidateId: number) => {
    const res = await apiClient.get(`/applications/candidate/${candidateId}/stats`);
    return res.data;
  },

  createApplication: async (payload: {
    candidate_id: number;
    canonical_job_id?: number | null;
    company_name: string;
    job_title: string;
    application_url?: string | null;
    status?: string;
    notes?: string | null;
    interview_date?: string | null;
    follow_up_date?: string | null;
    salary_offered?: string | null;
  }) => {
    const res = await apiClient.post('/applications', payload);
    return res.data;
  },

  updateApplicationStatus: async (applicationId: number, status: string, notes?: string) => {
    const res = await apiClient.patch(`/applications/${applicationId}/status`, { status, notes });
    return res.data;
  },

  updateApplication: async (applicationId: number, payload: Record<string, any>) => {
    const res = await apiClient.put(`/applications/${applicationId}`, payload);
    return res.data;
  },

  deleteApplication: async (applicationId: number) => {
    const res = await apiClient.delete(`/applications/${applicationId}`);
    return res.data;
  },

  getCompanies: async (params: Record<string, any> = {}) => {
    const res = await apiClient.get('/companies', { params });
    return res.data;
  },

  getCompanyResearch: async (companyId: number) => {
    const res = await apiClient.get(`/companies/${companyId}/research`);
    return res.data;
  },

  getCompanyVacancies: async (companyId: number) => {
    const res = await apiClient.get(`/companies/${companyId}/vacancies`);
    return res.data;
  },

  getPipelineStatus: async () => {
    const res = await apiClient.get('/pipeline/status');
    return res.data;
  },

  getPipelineHistory: async (limit = 20) => {
    const res = await apiClient.get('/pipeline/history', { params: { limit } });
    return res.data;
  },

  runPipeline: async (payload: {
    trigger_type?: string;
    stages?: string[];
    candidate_id?: number;
    force_matching?: boolean;
  } = {}) => {
    const res = await apiClient.post('/pipeline/run', payload);
    return res.data;
  },

  getUserPreferences: async (candidateId: number) => {
    const res = await apiClient.get(`/preferences/candidate/${candidateId}`);
    return res.data;
  },

  updateUserPreferences: async (candidateId: number, payload: Record<string, any>) => {
    const res = await apiClient.put(`/preferences/candidate/${candidateId}`, payload);
    return res.data;
  },
};

