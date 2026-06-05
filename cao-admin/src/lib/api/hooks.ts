/**
 * React Query Hooks for API Integration
 *
 * These hooks provide a clean interface between React components and the backend API.
 * They handle caching, refetching, optimistic updates, and error handling automatically.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from './client';
import { CAODocument, ProcessingJob, Discrepancy } from '@/types';

// ==========================================
// CAO Document Hooks
// ==========================================

/**
 * Hook to fetch all CAO documents
 */
export function useCaoDocuments(params?: {
  search?: string;
  sector?: string;
  status?: string;
  page?: number;
}) {
  return useQuery({
    queryKey: ['caos', params],
    queryFn: () => apiClient.getCaoDocuments(params),
    staleTime: 30000, // Consider data stale after 30 seconds
  });
}

/**
 * Hook to fetch single CAO document
 */
export function useCaoDocument(id: string) {
  return useQuery({
    queryKey: ['caos', id],
    queryFn: () => apiClient.getCaoDocument(id),
    enabled: !!id,
  });
}

/**
 * Hook to upload CAO document
 */
export function useUploadCao() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, metadata }: { file: File; metadata?: Partial<CAODocument> }) =>
      apiClient.uploadCaoDocument(file, metadata),
    onSuccess: () => {
      // Invalidate and refetch CAO list
      queryClient.invalidateQueries({ queryKey: ['caos'] });
    },
  });
}

/**
 * Hook to start processing
 */
export function useStartProcessing() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ caoId, config }: { caoId: string; config?: any }) =>
      apiClient.startProcessing(caoId, config),
    onSuccess: (data) => {
      // Invalidate jobs list
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      // Update CAO status optimistically
      queryClient.setQueryData(['caos', data.caoDocumentId], (old: any) => ({
        ...old,
        status: 'processing',
      }));
    },
  });
}

// ==========================================
// SETU Compliance Hooks
// ==========================================

/**
 * Hook to fetch discrepancies for a CAO
 */
export function useDiscrepancies(caoId: string) {
  return useQuery({
    queryKey: ['discrepancies', caoId],
    queryFn: () => apiClient.getDiscrepancies(caoId),
    enabled: !!caoId,
    refetchInterval: 10000, // Refetch every 10 seconds for real-time updates
  });
}

/**
 * Hook to resolve discrepancy
 */
export function useResolveDiscrepancy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      discrepancyId,
      resolution,
    }: {
      discrepancyId: string;
      resolution: { finalValue: any; reasoning: string };
    }) => apiClient.resolveDiscrepancy(discrepancyId, resolution),
    onSuccess: (data) => {
      // Update discrepancy in cache
      queryClient.setQueryData(
        ['discrepancies', data.caoDocumentId],
        (old: Discrepancy[] = []) =>
          old.map(d => d.id === data.id ? data : d)
      );
    },
  });
}

/**
 * Hook to fetch SETU compliance report
 */
export function useSetuReport(caoId: string) {
  return useQuery({
    queryKey: ['setu-report', caoId],
    queryFn: () => apiClient.getSetuReport(caoId),
    enabled: !!caoId,
  });
}

/**
 * Hook to fetch judge report
 */
export function useJudgeReport(caoId: string) {
  return useQuery({
    queryKey: ['judge-report', caoId],
    queryFn: () => apiClient.getJudgeReport(caoId),
    enabled: !!caoId,
  });
}

// ==========================================
// Processing Pipeline Hooks
// ==========================================

/**
 * Hook to fetch processing jobs
 */
export function useProcessingJobs(status?: 'queued' | 'running' | 'completed' | 'failed') {
  return useQuery({
    queryKey: ['jobs', status],
    queryFn: () => apiClient.getProcessingJobs({ status }),
    refetchInterval: 5000, // Refresh every 5 seconds for real-time updates
  });
}

/**
 * Hook to fetch single job details
 */
export function useProcessingJob(jobId: string) {
  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => apiClient.getProcessingJob(jobId),
    enabled: !!jobId,
    refetchInterval: (query) => {
      // Only refetch if job is running
      return query.state.data?.status === 'running' ? 2000 : false;
    },
  });
}

/**
 * Hook to pause job
 */
export function usePauseJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => apiClient.pauseJob(jobId),
    onSuccess: (data) => {
      // Update job in cache
      queryClient.setQueryData(['jobs', data.id], data);
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

/**
 * Hook to resume job
 */
export function useResumeJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => apiClient.resumeJob(jobId),
    onSuccess: (data) => {
      queryClient.setQueryData(['jobs', data.id], data);
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

/**
 * Hook to cancel job
 */
export function useCancelJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => apiClient.cancelJob(jobId),
    onSuccess: (_, jobId) => {
      // Remove job from cache
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.removeQueries({ queryKey: ['jobs', jobId] });
    },
  });
}

// ==========================================
// Analytics Hooks
// ==========================================

/**
 * Hook to fetch metrics
 */
export function useMetrics(period: 'day' | 'week' | 'month' = 'day') {
  return useQuery({
    queryKey: ['metrics', period],
    queryFn: () => apiClient.getMetrics({ period }),
    staleTime: 60000, // Cache for 1 minute
  });
}

/**
 * Hook to fetch cost analytics
 */
export function useCostAnalytics(organizationId?: string) {
  return useQuery({
    queryKey: ['costs', organizationId],
    queryFn: () => apiClient.getCostAnalytics(organizationId),
    staleTime: 300000, // Cache for 5 minutes
  });
}

/**
 * Hook to fetch compliance statistics
 */
export function useComplianceStats() {
  return useQuery({
    queryKey: ['compliance-stats'],
    queryFn: () => apiClient.getComplianceStats(),
    staleTime: 300000, // Cache for 5 minutes
  });
}

// ==========================================
// Authentication Hooks
// ==========================================

/**
 * Hook to get current user
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: ['user'],
    queryFn: () => apiClient.getCurrentUser(),
    staleTime: Infinity, // User data rarely changes
  });
}

/**
 * Hook to login
 */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      apiClient.login(email, password),
    onSuccess: (data) => {
      // Set user data in cache
      queryClient.setQueryData(['user'], data.user);
    },
  });
}

/**
 * Hook to logout
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.logout(),
    onSuccess: () => {
      // Clear all cached data
      queryClient.clear();
    },
  });
}

// ==========================================
// WebSocket Hook for Real-time Updates
// ==========================================

import { useEffect, useRef } from 'react';

/**
 * Hook to establish WebSocket connection for real-time updates
 */
export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    // Connect to WebSocket
    wsRef.current = apiClient.connectWebSocket({
      onJobUpdate: (job) => {
        // Update job in cache
        queryClient.setQueryData(['jobs', job.id], job);

        // If job is complete, invalidate CAO data
        if (job.status === 'completed') {
          queryClient.invalidateQueries({
            queryKey: ['caos', job.caoDocumentId]
          });
        }
      },
      onDiscrepancyFound: (discrepancy) => {
        // Add discrepancy to cache
        queryClient.setQueryData(
          ['discrepancies', discrepancy.caoDocumentId],
          (old: Discrepancy[] = []) => [...old, discrepancy]
        );
      },
      onNotification: (notification) => {
        // Handle notifications (could trigger toast, update bell icon, etc.)
        console.log('New notification:', notification);
      },
    });

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [queryClient]);

  return wsRef.current;
}