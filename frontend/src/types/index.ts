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
