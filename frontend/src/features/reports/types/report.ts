// frontend/src/features/reports/types/report.ts
export interface Report {
    id: number;
    title: string;
    summary: string | null;
    created_at: string;
    created_by_id: number;
}

export interface ReportCreate {
    title: string;
    summary?: string;
}
