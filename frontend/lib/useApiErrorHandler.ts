"use client";
import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useToast } from '@/components/providers/ToastProvider';
import { useAuth } from '@/hooks/useAuth';

export function useApiErrorHandler() {
  const { logout } = useAuth();
  const router = useRouter();
  const { addToast } = useToast();

  const handleApiError = useCallback(async (error: any, response?: Response) => {
    if (response?.status === 401 || error?.status === 401) {
      console.warn('Token expired or unauthorized, redirecting to login');
      addToast({
        message: 'Session expired. Please sign in again.',
        severity: 'warning',
      });

      logout();
      return;
    }

    if (response?.status === 403 || error?.status === 403) {
      console.warn('Access forbidden');
      return;
    }

    if (!response && (error?.message?.includes('fetch') || error?.name === 'TypeError')) {
      console.error('Network error:', error);
      return;
    }

    console.error('API Error:', error, response);
  }, [logout, router, addToast]);

  return { handleApiError };
}

export function useApiErrorBoundary() {
  const { handleApiError } = useApiErrorHandler();

  return useCallback(async (error: any) => {
    await handleApiError(error);
    throw error;
  }, [handleApiError]);
}
