import axios from 'axios';

/** API 오류 응답 본문 (FastAPI는 detail, 일부 화면은 message 필드를 사용) */
export interface ApiErrorBody {
    detail?: string;
    message?: string;
}

/** catch 절의 unknown 오류에서 API 응답 본문을 꺼낸다 (axios 오류가 아니면 빈 객체) */
export const getApiErrorBody = (err: unknown): ApiErrorBody =>
    axios.isAxiosError<ApiErrorBody>(err) ? (err.response?.data ?? {}) : {};

/** catch 절의 unknown 오류에서 메시지 문자열을 꺼낸다 */
export const getErrorMessage = (err: unknown): string =>
    err instanceof Error ? err.message : String(err);

/** catch 절의 unknown 오류에서 HTTP 상태 코드를 꺼낸다 (없으면 undefined) */
export const getHttpStatus = (err: unknown): number | undefined =>
    axios.isAxiosError(err) ? err.response?.status : undefined;
