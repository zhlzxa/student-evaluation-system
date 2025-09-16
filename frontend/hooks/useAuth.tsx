"use client";

import { useState, useEffect, useCallback, createContext, useContext, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'access_token';
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

// Helper function to decode JWT token without verification
function parseJWT(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

// Helper function to check if token is expired
function isTokenExpired(token: string): boolean {
  const payload = parseJWT(token);
  if (!payload || !payload.exp) return true;

  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp < currentTime;
}

// Helper function to get user info from token
function getUserFromToken(token: string): User | null {
  const payload = parseJWT(token);
  if (!payload || !payload.sub) return null;

  // Extract user info from token payload
  return {
    id: payload.user_id || 0,
    email: payload.sub,
    full_name: payload.full_name || '',
    is_active: payload.is_active !== false,
    is_superuser: payload.is_superuser === true,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);

    if (storedToken && !isTokenExpired(storedToken)) {
      const userData = getUserFromToken(storedToken);
      if (userData) {
        setToken(storedToken);
        setUser(userData);
      } else {
        localStorage.removeItem(TOKEN_KEY);
      }
    } else if (storedToken) {
      // Token expired, remove it
      localStorage.removeItem(TOKEN_KEY);
    }

    setLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      const { access_token } = data;

      if (!access_token) {
        throw new Error('No access token received');
      }

      const userData = getUserFromToken(access_token);
      if (!userData) {
        throw new Error('Invalid token received');
      }

      localStorage.setItem(TOKEN_KEY, access_token);
      setToken(access_token);
      setUser(userData);

      // Redirect to main page
      router.push('/assessments');
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }, [router]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    router.push('/login');
  }, [router]);

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    loading,
    isAuthenticated: !!user && !!token,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}