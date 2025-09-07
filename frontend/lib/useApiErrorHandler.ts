"use client";
import { useCallback } from 'react';
import { useSession, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';

export function useApiErrorHandler() {
  const { data: session } = useSession();
  const router = useRouter();

  const handleApiError = useCallback(async (error: any, response?: Response) => {
    if (response?.status === 401 || error?.status === 401) {
      console.warn('Token expired or unauthorized, redirecting to login');
      
      if (session) {
        await signOut({ 
          redirect: false,
          callbackUrl: '/login' 
        });
      }
      
      router.push('/login');
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
  }, [session, router]);

  return { handleApiError };
}

export function useApiErrorBoundary() {
  const { handleApiError } = useApiErrorHandler();

  return useCallback(async (error: any) => {
    await handleApiError(error);
    throw error;
  }, [handleApiError]);
}
