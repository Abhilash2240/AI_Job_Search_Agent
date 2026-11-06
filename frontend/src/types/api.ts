export type ValidationStatus = 'VALID' | 'INCOMPLETE' | 'INVALID';
export type ExperienceLevel = 'fresher' | 'entry_level' | 'mid_level' | 'senior';

export interface PersonalInfo {
  name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
}

export interface EducationItem {
  degree: string | null;
  specialization: string | null;
  university: string | null;
  graduation_year: string | null;
  start_year: string | null;
  end_year: string | null;
  academic_performance: string | null;
}

export interface SkillsCategorized {
  programming_languages: string[];
  frameworks: string[];
  databases: string[];
  tools: string[];
  ai_ml: string[];
  other: string[];
}

export interface ExperienceItem {
  company: string | null;
  job_title: string | null;
  duration: string | null;
  responsibilities: string | null;
}

export interface ProjectItem {
  name: string | null;
  description: string | null;
  technologies: string[];
}

export interface InternshipItem {
  company: string | null;
  role: string | null;
  duration: string | null;
  responsibilities: string | null;
}

export interface CertificationItem {
  name: string | null;
  issuer: string | null;
  year: string | null;
}

export interface CandidateProfile {
  personal: PersonalInfo;
  education: EducationItem[];
  skills: SkillsCategorized;
  skill_sources?: Record<string, string[]>;
  inferred_skills?: string[];
  experience: ExperienceItem[];
  projects: ProjectItem[];
  internships: InternshipItem[];
  certifications: CertificationItem[];
  achievements: string[];
  profile_completeness: number | null;
}

export interface ValidationResult {
  status: ValidationStatus;
  reasons: string[];
  missing_information: string[];
  entropy: number;
  career_term_count: number;
  char_count: number;
}

export interface ResumeUploadResponse {
  candidate_id: number;
  resume_hash: string;
  filename: string | null;
  validation: ValidationResult;
  profile: CandidateProfile;
}

export interface DetailedProfileValidation {
  candidate_id: number;
  validation_status: ValidationStatus;
  completeness_score: number;
  experience_level: ExperienceLevel;
  years_of_experience_estimated: number;
  warnings: string[];
  suggestions: string[];
  section_analysis: Record<string, any>;
  complete_fields?: string[];
  missing_fields?: string[];
  unverified_fields?: string[];
  optional_fields?: string[];
}

export interface RoleRecommendation {
  role_id: string;
  role_title: string;
  composite_match_score: number;
  similarity_score: number;
  skill_match_score: number;
  project_alignment_score: number;
  education_alignment_score: number;
  matching_skills: string[];
  missing_skills: string[];
  skill_evidence: Record<string, string[]>;
  explanation: string;
  alternative_titles: string[];
}

export interface RecommendationsResponse {
  candidate_id: number;
  candidate_name: string | null;
  experience_level: ExperienceLevel;
  total_recommended: number;
  recommendations: RoleRecommendation[];
  scoring_formula: string;
  scoring_weights: Record<string, number>;
  model_version: string;
}

export interface ConfirmedRoleItem {
  role_id: string;
  role_title: string;
  is_custom: boolean;
  custom_description?: string | null;
  matching_skills: string[];
  missing_skills: string[];
  alternative_titles: string[];
  composite_match_score?: number | null;
  similarity_score?: number | null;
}

export interface ConfirmedRolesResponse {
  candidate_id: number;
  candidate_name: string | null;
  confirmed: boolean;
  confirmed_at: string | null;
  total_confirmed: number;
  roles: ConfirmedRoleItem[];
}

export interface CustomRolePayload {
  role_title: string;
  role_description?: string;
  skills?: string[];
}

// ==========================================
// Phase 8 / Final Project Completion Types
// ==========================================

export interface StructuredSkill {
  skill_name: string;
  canonical_name?: string;
  category?: string;
  candidate_evidence?: string[] | string;
  is_verified?: boolean;
  evidence_snippet?: string;
  is_required?: boolean;
}

export type SkillItem = string | StructuredSkill;

export interface JobFeedItem {
  id: number;
  canonical_job_id: string;
  title: string;
  canonical_job_title: string;
  company_name: string;
  company_id?: number | null;
  location: string;
  city?: string | null;
  country: string;
  work_mode: string;
  workplace_type?: string | null;
  is_remote: boolean;
  employment_type: string;
  experience_level: string;
  experience_min_years?: number | null;
  experience_max_years?: number | null;
  salary_range?: string | null;
  stipend_range?: string | null;
  vacancy_status: string;
  is_active: boolean;
  first_seen_at?: string | null;
  last_verified_at?: string | null;
  original_job_url?: string | null;
  match_score: number;
  eligibility_status: string;
  matched_skills: SkillItem[];
  missing_skills: SkillItem[];
  explanation: string;
  is_relevant?: boolean;
  relevance_status?: string;
  role_family?: string;
  relevance_score?: number;
  rejection_reasons?: string[];
  semantic_score?: number;
  is_saved: boolean;
  application_status?: string | null;
}

export interface JobFeedResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: JobFeedItem[];
}

export interface SkillWithEvidenceItem {
  skill_name: string;
  canonical_name: string;
  category: string;
  evidence_snippet?: string;
  is_required?: boolean;
}

export interface MatchDetailsBreakdown {
  composite_score: number;
  semantic_score: number;
  skill_score: number;
  role_score: number;
  experience_score: number;
  education_score: number;
  location_score: number;
  score_coverage: number;
  eligibility_status: string;
  is_relevant?: boolean;
  role_family?: string;
  relevance_score?: number;
  rejection_reasons?: string[];
  explanation: string;
  matched_skills: SkillItem[];
  missing_skills: SkillItem[];
  disqualification_reasons: string[];
}

export interface JobDetailResponse {
  id: number;
  canonical_job_id: string;
  company_id?: number | null;
  company_name: string;
  title: string;
  canonical_job_title?: string | null;
  location?: string | null;
  city?: string | null;
  state?: string | null;
  country: string;
  is_remote: boolean;
  workplace_type?: string | null;
  employment_type?: string | null;
  seniority_level?: string | null;
  experience_min_years?: number | null;
  experience_max_years?: number | null;
  description?: string | null;
  responsibilities: string[];
  qualifications: string[];
  required_skills: SkillWithEvidenceItem[];
  preferred_skills: SkillWithEvidenceItem[];
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  canonical_application_url?: string | null;
  canonical_source_url?: string | null;
  vacancy_status: string;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  last_verified_at?: string | null;
  match_details?: MatchDetailsBreakdown | null;
  is_saved: boolean;
  application_status?: string | null;
}

export interface SavedJobItem {
  id: number;
  candidate_id: number;
  canonical_job_id: number;
  notes?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  job?: {
    id: number;
    canonical_job_id: string;
    title: string;
    company_name?: string | null;
    location?: string | null;
    workplace_type?: string | null;
    employment_type?: string | null;
    vacancy_status: string;
    is_active: boolean;
    salary_range?: string | null;
    stipend_range?: string | null;
  } | null;
}

export interface SavedJobListResponse {
  total: number;
  items: SavedJobItem[];
}

export interface ApplicationHistoryItem {
  id: number;
  application_id: number;
  from_status?: string | null;
  to_status: string;
  notes?: string | null;
  changed_at: string;
}

export interface ApplicationItem {
  id: number;
  candidate_id: number;
  canonical_job_id?: number | null;
  company_name: string;
  job_title: string;
  application_url?: string | null;
  status: string;
  applied_at?: string | null;
  notes?: string | null;
  interview_date?: string | null;
  follow_up_date?: string | null;
  salary_offered?: string | null;
  created_at: string;
  updated_at: string;
  status_history?: ApplicationHistoryItem[];
}

export interface ApplicationListResponse {
  total: number;
  items: ApplicationItem[];
}

export interface ApplicationStatsResponse {
  total_applications: number;
  by_status: Record<string, number>;
  interviews_scheduled: number;
  offers_received: number;
  active_in_pipeline: number;
  response_rate_percent: number;
}

export interface CompanyListItem {
  id: number;
  canonical_name: string;
  normalized_name: string;
  primary_domain?: string | null;
  country?: string | null;
  industry?: string | null;
  relevance_category?: string | null;
  is_active: boolean;
  career_sources_count: number;
  contacts_count: number;
  created_at: string;
}

export interface CompanyListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: CompanyListItem[];
}

export interface CompanyResearchResponse {
  company_id: number;
  name: string;
  normalized_name: string;
  primary_domain?: string | null;
  country: string;
  industry: string;
  relevance_category?: string | null;
  is_active: boolean;
  career_sources: Array<{
    id: number;
    url: string;
    normalized_url?: string | null;
    source_document?: string | null;
    source_page?: number | null;
    verification_status: string;
    ats_provider?: string | null;
  }>;
  contacts: Array<{
    email: string;
    source: string;
    is_verified: boolean;
    last_verified_at?: string | null;
    notes?: string;
  }>;
  active_vacancies_count: number;
  active_vacancies: Array<{
    id: number;
    canonical_job_id: string;
    title: string;
    location?: string | null;
    work_mode?: string | null;
    employment_type?: string | null;
    url?: string | null;
  }>;
  outreach_policy: {
    requires_explicit_authorization: boolean;
    automated_sending_enabled: boolean;
    guideline: string;
  };
}

export interface PipelineExecutionItem {
  id: number;
  run_id: string;
  trigger_type: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
  stages_executed?: Record<string, any> | null;
  jobs_discovered: number;
  jobs_extracted: number;
  canonical_vacancies_updated: number;
  embeddings_generated: number;
  matches_computed: number;
  error_message?: string | null;
}

export interface PipelineHistoryResponse {
  total: number;
  items: PipelineExecutionItem[];
}

export interface DashboardStatsResponse {
  candidate_id: number;
  system: {
    total_candidates: number;
    total_companies: number;
    total_sources: number;
    total_discovered_jobs: number;
    total_canonical_vacancies: number;
    canonical_vacancies: number;
    verified_active_vacancies: number;
    job_embeddings: number;
  };
  recommendations: {
    total_matches_evaluated: number;
    relevant_opportunities: number;
    highly_recommended_jobs: number;
    top_match_score?: number | null;
    top_composite_score?: number | null;
    best_job_id?: number | null;
    best_job_title?: string | null;
    best_company_name?: string | null;
    eligible_matching_jobs?: number;
    last_matching_at?: string | null;
    matching_status?: string | null;
    candidate_matches_count?: number;
  };
  saved_jobs: {
    total_saved: number;
  };
  saved?: {
    total_saved: number;
  };
  applications: {
    total_applications: number;
    active_in_pipeline: number;
    active_applications?: number;
    interviews_scheduled: number;
    offers_received: number;
    status_breakdown: Record<string, number>;
  };
  recent_pipeline_runs: Array<{
    run_id: string;
    trigger: string;
    status: string;
    started_at?: string | null;
    jobs_discovered: number;
    matches_computed: number;
  }>;
}

export interface UserPreferencesResponse {
  id: number;
  candidate_id: number;
  preferred_locations: string[];
  work_modes: string[];
  employment_types: string[];
  min_salary?: number | null;
  min_stipend?: number | null;
  min_match_score: number;
  updated_at: string;
}
