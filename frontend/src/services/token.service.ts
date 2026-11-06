/**
 * 토큰 관리 서비스
 * localStorage 대신 메모리 + sessionStorage를 사용하여 XSS 공격 위험 감소
 */
class TokenService {
    private token: string | null = null;

    /**
     * 토큰 가져오기
     * 메모리에 없으면 sessionStorage에서 복원 시도
     */
    getToken(): string | null {
        if (this.token) {
            return this.token;
        }
        
        // 새로고침 시 sessionStorage에서 복원
        const sessionToken = sessionStorage.getItem('token');
        if (sessionToken) {
            this.token = sessionToken;
            return sessionToken;
        }
        
        return null;
    }

    /**
     * 토큰 저장
     * 메모리와 sessionStorage 모두에 저장
     */
    setToken(token: string): void {
        this.token = token;
        sessionStorage.setItem('token', token);
    }

    /**
     * 토큰 제거
     * 로그아웃 시 사용
     */
    clearToken(): void {
        this.token = null;
        sessionStorage.removeItem('token');
    }

    /**
     * 토큰 존재 여부 확인
     */
    hasToken(): boolean {
        return this.getToken() !== null;
    }
}

// 싱글톤 인스턴스 생성
export const tokenService = new TokenService();
