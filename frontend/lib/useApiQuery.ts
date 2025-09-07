"use client";
import { useQuery, useMutation, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import { useApi } from './api';
import { useToast } from '../components/providers/ToastProvider';

export function useApiQuery<T = any>(
  queryKey: (string | number)[],
  path: string,
  options?: Omit<UseQueryOptions<T>, 'queryKey' | 'queryFn'>
) {
  const api = useApi();
  const { addToast } = useToast();

  return useQuery<T>({
    queryKey,
    queryFn: async () => {
      try {
        const response = await api(path);
        if (!response.ok) {
          throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        return response.json();
      } catch (error) {
        console.error(`Query error for ${path}:`, error);
        
        if (error instanceof Error && !error.message.includes('Authentication required')) {
          addToast({
            message: `Failed to load data: ${error.message}`,
            severity: 'error'
          });
        }
        
        throw error;
      }
    },
    ...options,
  });
}

export function useApiMutation<T = any, V = any>(
  mutationFn: (variables: V) => Promise<Response>,
  options?: UseMutationOptions<T, Error, V>
) {
  const { addToast } = useToast();

  return useMutation<T, Error, V>({
    mutationFn: async (variables: V) => {
      try {
        const response = await mutationFn(variables);
        if (!response.ok) {
          throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        return response.json();
      } catch (error) {
        console.error('Mutation error:', error);
        
        if (error instanceof Error && !error.message.includes('Authentication required')) {
          addToast({
            message: `Operation failed: ${error.message}`,
            severity: 'error'
          });
        }
        
        throw error;
      }
    },
    ...options,
  });
}
