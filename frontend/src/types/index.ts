// Auth Types
export interface User {
    user_id: number;
    user_email: string;
    user_name: string;
    role: '일반' | '보안관리자' | '감사팀' | '시스템관리자';
    company?: string;
    department?: string;
}

export interface LoginCredentials {
    user_email: string;
    password: string;
}

export interface RegisterData {
    user_email: string;
    password: string;
    user_name: string;
    role: string;
    company?: string;
    department?: string;
}

export interface UserRegisterRequest {
    user_email: string;
    user_name: string;
    password?: string; // Optional for update
    company?: string;
    department?: string;
    role: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
}

export interface EntraLoginRequest {
    access_token: string;
}

export interface AuthConfig {
    allow_local: boolean;
    allow_entra: boolean;
    default_method: string;
}

// Case Types
export interface Case {
    case_id: number;
    siem_type: string;
    rule_title: string;
    rule_description?: string;
    incident_num?: number;
    summary?: string;
    case_type: '정보유출' | '보안위반' | '시스템접근' | '권한오남용';
    related_employee_id: number;
    requester_id: number;
    created_at: string;
    due_date: string;
    case_status: '미확인' | '요청' | '제출' | '승인' | '반려' | '종결';
    case_result?: '정당 사유' | '경미한 위반' | '소명 불충분' | '교육 필요' | '징계 요청' | '오탐';
    priority: '낮음' | '보통' | '높음';
    final_review_date?: string;
    final_reviewer_id?: number;
    related_employee?: {
        user_name: string;
        user_email: string;
        department?: string;
        company?: string;
        role: string;
    };
    submissions?: Submission[];
    review_comment?: string;
    reviewer_name?: string;
    original_log_link?: string;
    attachments?: Attachment[];
}

export interface Attachment {
    file_id: number;
    submission_id?: number | null;
    original_filename: string;
    file_size?: number;
    uploaded_at: string;
}

export interface Submission {
    submission_id: number;
    case_id: number;
    submitter_id: number;
    submitted_at: string;
    content: string;
    classification?: string;
    attachments?: Attachment[];
}

export interface Review {
    review_id: number;
    case_id: number;
    reviewer_id: number;
    reviewed_at: string;
    case_status: string;
    case_result: string;
    comments?: string;
}

export interface LoginHistoryResponse {
    login_id: number;
    user_id: number;
    login_at: string;
    ip_address: string;
    status: string;
}

export interface SiemConfiguration {
    siem_id?: number;
    siem_type: 'Sentinel' | 'ELK' | 'Splunk';
    name: string;
    host_url: string;
    tenant_id?: string;
    client_id?: string;
    client_secret?: string;
    subscription_id?: string;
    resource_group?: string;
    workspace_name?: string;
    api_key?: string;
    test_query?: string;
    field_mapping?: Record<string, string>;
    cron_expression?: string;
    is_active: boolean;
}

export interface SiemSyncHistory {
    history_id: number;
    siem_id: number;
    execution_time: string;
    status: string;
    records_fetched: number;
    error_message?: string;
}

// --- 대시보드·통계 (백엔드 /cases/stats, /cases/daily-stats, /cases/weekly-reports 응답) ---
export interface DashboardFilters {
    case_status: string | null;
    priority: string | null;
    case_type: string | null;
    date: string | null;
    startDate: string | null;
    endDate: string | null;
}

export interface CaseStatsChartPoint {
    date: string;
    case_type: string | null;
    count: number;
}

export interface CaseStats {
    total: number;
    status: { unclassified: number; requested: number; submitted: number; approved: number; rejected: number; closed: number };
    priority: { high: number; medium: number; low: number };
    case_type: { leak: number; violation: number; system: number; abuse: number };
    chart_data: CaseStatsChartPoint[];
}

export interface DailyStat {
    date: string;
    unclassified: number;
    request: number;
    submit: number;
    reviewed: number;
}

export interface WeeklyReport {
    report_id: number;
    week_start: string;
    week_end: string;
    created: number;
    approved: number;
    rejected: number;
    generated_at: string | null;
}

export interface PaginatedCases {
    items: Case[];
    total: number;
    page: number;
    size: number;
    pages: number;
}

// --- 사용자 일괄 등록·Entra 동기화 응답 ---
export interface UserUploadStats {
    total: number;
    created: number;
    skipped: number;
    errors: number;
    details: string[];
}

export interface UserUploadResponse {
    message: string;
    stats: UserUploadStats;
}

export interface EntraSyncResponse {
    message: string;
    stats: { total: number; created: number; updated: number };
}

/** 관리자 수동 작업 실행 시 전달하는 옵션 (예: { target_date: '2026-11-01' }) */
export type JobTriggerPayload = Record<string, string>;
