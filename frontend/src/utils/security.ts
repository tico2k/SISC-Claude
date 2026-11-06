/**
 * 보안 관련 유틸리티 함수
 * XSS 방지를 위한 입력 sanitization
 */

/**
 * 기본 입력 sanitization
 * HTML 태그 및 위험한 문자를 제거
 */
export const sanitizeInput = (input: string): string => {
    if (!input) return '';

    // 앞뒤 공백 제거
    let sanitized = input.trim();

    // HTML 태그 제거
    sanitized = sanitized.replace(/[<>]/g, '');

    // 스크립트 관련 문자열 제거
    sanitized = sanitized.replace(/javascript:/gi, '');
    sanitized = sanitized.replace(/on\w+\s*=/gi, '');

    return sanitized;
};

/**
 * 이메일 입력 검증 및 sanitization
 */
export const sanitizeEmail = (email: string): string => {
    if (!email) return '';

    // 기본 sanitization
    let sanitized = email.trim().toLowerCase();

    // 이메일 형식 검증을 위한 정규식
    const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

    if (!emailRegex.test(sanitized)) {
        return '';
    }

    return sanitized;
};

/**
 * URL 검증 및 sanitization
 */
export const sanitizeUrl = (url: string): string => {
    if (!url) return '';

    const sanitized = url.trim();

    // 허용된 프로토콜만 통과
    const allowedProtocols = ['http:', 'https:'];

    try {
        const urlObj = new URL(sanitized);
        if (!allowedProtocols.includes(urlObj.protocol)) {
            return '';
        }
        return sanitized;
    } catch {
        return '';
    }
};

/**
 * 파일명 sanitization
 * Path traversal 공격 방지
 */
export const sanitizeFileName = (fileName: string): string => {
    if (!fileName) return '';

    // 경로 구분자 제거
    let sanitized = fileName.replace(/[\/\\]/g, '');

    // null 바이트 제거
    sanitized = sanitized.replace(/\0/g, '');

    // 특수 문자 제거 (파일명에 허용되는 문자만 유지)
    sanitized = sanitized.replace(/[^a-zA-Z0-9가-힣._-]/g, '_');

    // 길이 제한 (확장자 포함 100자)
    if (sanitized.length > 100) {
        const ext = sanitized.substring(sanitized.lastIndexOf('.'));
        const name = sanitized.substring(0, sanitized.lastIndexOf('.'));
        sanitized = name.substring(0, 100 - ext.length) + ext;
    }

    return sanitized;
};

/**
 * 검색어 sanitization
 * SQL Injection 및 XSS 방지
 */
export const sanitizeSearchQuery = (query: string): string => {
    if (!query) return '';

    let sanitized = query.trim();

    // SQL 특수 문자 이스케이프
    sanitized = sanitized.replace(/['";\\]/g, '');

    // HTML 태그 제거
    sanitized = sanitized.replace(/[<>]/g, '');

    // 최대 길이 제한
    if (sanitized.length > 200) {
        sanitized = sanitized.substring(0, 200);
    }

    return sanitized;
};

/**
 * 일반 텍스트 필드 sanitization
 * 기본적인 XSS 방지
 */
export const sanitizeText = (text: string, maxLength: number = 1000): string => {
    if (!text) return '';

    let sanitized = text.trim();

    // HTML 태그 제거
    sanitized = sanitized.replace(/[<>]/g, '');

    // 최대 길이 제한
    if (sanitized.length > maxLength) {
        sanitized = sanitized.substring(0, maxLength);
    }

    return sanitized;
};
