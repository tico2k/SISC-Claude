/**
 * 파일 업로드 검증 유틸리티
 * 클라이언트 측에서 파일 확장자, 크기, MIME 타입을 검증
 */

export const ALLOWED_FILE_EXTENSIONS = [
    '.pdf', '.docx', '.xlsx', '.pptx', '.txt',
    '.png', '.jpg', '.jpeg', '.gif'
];

export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export interface FileValidationResult {
    valid: boolean;
    error?: string;
}

/**
 * 허용된 MIME 타입 목록
 * 확장자 스푸핑 방지용
 */
const ALLOWED_MIME_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'image/png',
    'image/jpeg',
    'image/gif'
];

/**
 * 단일 파일 검증
 */
export const validateFile = (file: File): FileValidationResult => {
    // 확장자 체크
    const fileName = file.name.toLowerCase();
    const ext = '.' + fileName.split('.').pop();

    if (!ALLOWED_FILE_EXTENSIONS.includes(ext)) {
        return {
            valid: false,
            error: `허용되지 않는 파일 형식입니다. 허용 형식: ${ALLOWED_FILE_EXTENSIONS.join(', ')}`
        };
    }

    // 파일 크기 체크
    if (file.size > MAX_FILE_SIZE) {
        const maxSizeMB = MAX_FILE_SIZE / (1024 * 1024);
        return {
            valid: false,
            error: `파일 크기가 너무 큽니다. 최대 ${maxSizeMB}MB까지 업로드 가능합니다.`
        };
    }

    // 파일 크기가 0인 경우
    if (file.size === 0) {
        return {
            valid: false,
            error: '빈 파일은 업로드할 수 없습니다.'
        };
    }

    // MIME 타입 체크 (확장자 스푸핑 방지)
    if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
        return {
            valid: false,
            error: '파일 형식이 올바르지 않습니다.'
        };
    }

    return { valid: true };
};

/**
 * 여러 파일 검증
 */
export const validateFiles = (files: File[]): FileValidationResult => {
    if (!files || files.length === 0) {
        return { valid: true }; // allow empty list as a valid state
    }

    for (const file of files) {
        const result = validateFile(file);
        if (!result.valid) {
            return result;
        }
    }

    return { valid: true };
};

/**
 * 파일 크기를 사람이 읽기 쉬운 형식으로 변환
 */
export const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};
