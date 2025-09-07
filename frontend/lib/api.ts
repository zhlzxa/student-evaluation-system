"use client";
import { useSession, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useCallback } from 'react';

export function useApi() {
  const { data: session } = useSession();
  const router = useRouter();
  const token = (session as any)?.access_token as string | undefined;
  
  const handleUnauthorized = useCallback(async () => {
    console.warn('Token expired or unauthorized, redirecting to login');
    
    if (session) {
      await signOut({ 
        redirect: false,
        callbackUrl: '/login' 
      });
    }
    
    router.replace('/login');
  }, [session, router]);
  
  return useCallback(async (path: string, init?: RequestInit) => {
    const isForm = typeof FormData !== 'undefined' && init?.body instanceof FormData;
    const baseHeaders: Record<string, string> = {};
    if (!isForm) {
      baseHeaders['Content-Type'] = 'application/json';
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_BASE_URL}${path}`, {
        ...init,
        headers: {
          ...baseHeaders,
          ...(init?.headers || {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        cache: 'no-store',
      });

      if (res.status === 401) {
        await handleUnauthorized();
        throw new Error('Authentication required. Redirecting to login page.');
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
