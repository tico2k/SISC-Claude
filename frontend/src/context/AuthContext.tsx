import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, LoginCredentials } from '../types';
import { authService } from '../services/auth.service';
import { tokenService } from '../services/token.service';
import { jwtDecode } from "jwt-decode";

interface JWTPayload {
    sub: string; // email
    name: string;
    role: string;
    exp: number; // expiration timestamp
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (credentials: LoginCredentials) => Promise<void>;
    setToken: (token: string) => void;
    logout: () => void;
    isAuthenticated: boolean;
    role: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(tokenService.getToken());
    const [role, setRole] = useState<string | null>(null);

    useEffect(() => {
        if (token) {
            try {
                // JWT 디코딩 및 만료 검증
                const decoded = jwtDecode<JWTPayload>(token);

                // 토큰 만료 확인
                const currentTime = Date.now() / 1000;
                if (decoded.exp && decoded.exp < currentTime) {
                    console.warn('Token expired, logging out');
                    logout();
                    return;
                }

                // 사용자 정보 설정
                setUser({
                    user_email: decoded.sub,
                    user_name: decoded.name,
                    role: decoded.role
                } as User);
                setRole(decoded.role);
            } catch (e) {
                console.error('Failed to decode token:', e);
                logout();
            }
        }
    }, [token]);

    const login = async (credentials: LoginCredentials) => {
        const data = await authService.login(credentials);
        handleSetToken(data.access_token);
    };

    const handleSetToken = (newToken: string) => {
        tokenService.setToken(newToken);
        setToken(newToken);
    };

    const logout = () => {
        tokenService.clearToken();
        setToken(null);
        setUser(null);
        setRole(null);
    };

    return (
        <AuthContext.Provider value={{ user, token, login, setToken: handleSetToken, logout, isAuthenticated: !!token, role }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
