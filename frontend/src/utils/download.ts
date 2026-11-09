/** 서버가 보낸 파일(Blob)을 브라우저 다운로드로 저장 */
export const saveBlob = (blob: Blob, contentDisposition: string | undefined, fallbackName: string): void => {
    let filename = fallbackName;
    const match = contentDisposition?.match(/filename\*=UTF-8''([^;]+)/i);
    if (match) {
        try {
            filename = decodeURIComponent(match[1]);
        } catch {
            // 잘못된 인코딩이면 기본 이름 사용
        }
    }
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
};
