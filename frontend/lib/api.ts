"use client";
import { useCallback } from 'react';
import { useToast } from '@/components/providers/ToastProvider';
import { useAuth } from '@/hooks/useAuth';

export function useApi() {
  const { token, logout } = useAuth();
  const { addToast } = useToast();

  const handleUnauthorized = useCallback(() => {
    console.warn('Token expired or unauthorized, redirecting to login');
    addToast({
      message: 'Session expired. Please sign in again.',
      severity: 'warning',
    });
    logout();
  }, [logout, addToast]);
  
  return useCallback(async (path: string, init?: RequestInit) => {

    const isForm = typeof FormData !== 'undefined' && init?.body instanceof FormData;
    const baseHeaders: Record<string, string> = {};
    if (!isForm) {
      baseHeaders['Content-Type'] = 'application/json';
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
        ...init,
        headers: {
          ...baseHeaders,
          ...(init?.headers || {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        cache: 'no-store',
      });

      if (res.status === 401) {
        handleUnauthorized();
        throw new Error('Authentication required. Redirecting to login page.');
      }

      if (res.status === 403) {
        // Check if this is actually an authentication issue
        if (!token || token.length === 0) {
          console.warn('403 error with no token - treating as authentication issue');
          handleUnauthorized();
          throw new Error('Authentication required. Redirecting to login page.');
        }

        // True permission error - surface to UI
        addToast({
          message: 'You do not have permission to perform this action.',
          severity: 'warning',
        });
      }

      return res;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        console.error('Network error:', error);
        throw new Error('Network error. Please check your connection.');
      }
      
      throw error;
    }
  }, [token, handleUnauthorized]);
}
