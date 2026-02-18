/**
 * MODERN API-BASED COMPONENT EXAMPLE
 *
 * This shows the RIGHT way to build frontend components that connect to backend APIs.
 * The component has ZERO business logic - it only handles UI and calls API hooks.
 */

"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";

// Import our API hooks - this is the ONLY way to get data
import {
  useCaoDocuments,
  useUploadCao,
  useStartProcessing,
  useDiscrepancies,
  useResolveDiscrepancy,
  useProcessingJobs,
  useWebSocket,
} from "@/lib/api/hooks";

export default function ModernCAOManagement() {
  const [selectedCaoId, setSelectedCaoId] = useState<string | null>(null);
  const { toast } = useToast();

  // ==========================================
  // 1. FETCHING DATA FROM BACKEND API
  // ==========================================

  // Fetch CAO documents from backend API
  // This automatically handles loading, error, caching, and refetching
  const {
    data: caosResponse,
    isLoading: caosLoading,
    error: caosError,
    refetch: refetchCaos,
  } = useCaoDocuments({
    search: "",
    sector: undefined,
    status: undefined,
    page: 1,
  });

  // Fetch discrepancies for selected CAO
  const {
    data: discrepancies,
    isLoading: discrepanciesLoading,
  } = useDiscrepancies(selectedCaoId || "");

  // Fetch active processing jobs
  const {
    data: activeJobs,
    isLoading: jobsLoading,
  } = useProcessingJobs("running");

  // ==========================================
  // 2. MUTATIONS (CREATE, UPDATE, DELETE)
  // ==========================================

  // Upload CAO mutation
  const uploadMutation = useUploadCao();

  // Start processing mutation
  const startProcessingMutation = useStartProcessing();

  // Resolve discrepancy mutation
  const resolveDiscrepancyMutation = useResolveDiscrepancy();

  // ==========================================
  // 3. REAL-TIME UPDATES VIA WEBSOCKET
  // ==========================================

  // Connect to WebSocket for real-time updates
  // This automatically updates the cache when backend sends updates
  useWebSocket();

  // ==========================================
  // 4. UI EVENT HANDLERS (No Business Logic!)
  // ==========================================

  const handleFileUpload = async (file: File) => {
    try {
      // Call backend API to upload file
      const result = await uploadMutation.mutateAsync({
        file,
        metadata: {
          name: file.name,
          uploadedAt: new Date(),
        },
      });

      toast({
        title: "Upload Successful",
        description: `${file.name} has been uploaded and processing has started.`,
      });

      // The cache is automatically updated by React Query
      // No need to manually update state!
    } catch (error) {
      toast({
        title: "Upload Failed",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleStartProcessing = async (caoId: string) => {
    try {
      // Call backend API to start processing
      await startProcessingMutation.mutateAsync({
        caoId,
        config: {
          pipeline: "3-llm-standard",
          priority: "high",
        },
      });

      toast({
        title: "Processing Started",
        description: "The document is now being processed.",
      });
    } catch (error) {
      toast({
        title: "Failed to Start Processing",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleResolveDiscrepancy = async (
    discrepancyId: string,
    resolution: any
  ) => {
    try {
      // Call backend API to resolve discrepancy
      await resolveDiscrepancyMutation.mutateAsync({
        discrepancyId,
        resolution,
      });

      toast({
        title: "Discrepancy Resolved",
        description: "The issue has been resolved successfully.",
      });
    } catch (error) {
      toast({
        title: "Resolution Failed",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  // ==========================================
  // 5. RENDER UI (Pure Presentation)
  // ==========================================

  // Loading state
  if (caosLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // Error state
  if (caosError) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-center text-destructive">
            Failed to load data: {caosError.message}
          </p>
          <Button onClick={() => refetchCaos()} className="mx-auto mt-4">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Modern API-Connected Component</CardTitle>
          <p className="text-sm text-muted-foreground">
            This component fetches all data from the backend API.
            No business logic lives in the frontend!
          </p>
        </CardHeader>
        <CardContent>
          {/* File Upload */}
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Upload New CAO</h3>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file);
              }}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-full file:border-0
                file:text-sm file:font-semibold
                file:bg-primary file:text-primary-foreground
                hover:file:bg-primary/90"
            />
            {uploadMutation.isPending && (
              <p className="text-sm text-muted-foreground mt-2">
                Uploading...
              </p>
            )}
          </div>

          {/* CAO List from API */}
          <div className="space-y-4">
            <h3 className="font-semibold">
              CAO Documents ({caosResponse?.total || 0})
            </h3>

            {caosResponse?.data.map((cao) => (
              <div
                key={cao.id}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div>
                  <p className="font-medium">{cao.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {cao.sector} • {cao.company}
                  </p>
                  <div className="flex gap-2 mt-2">
                    <Badge>{cao.status}</Badge>
                    <Badge variant="outline">{cao.compliance_status}</Badge>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedCaoId(cao.id)}
                  >
                    View Details
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleStartProcessing(cao.id)}
                    disabled={startProcessingMutation.isPending}
                  >
                    {startProcessingMutation.isPending
                      ? "Processing..."
                      : "Start Processing"}
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {/* Active Jobs from API */}
          {activeJobs && activeJobs.length > 0 && (
            <div className="mt-6">
              <h3 className="font-semibold mb-2">
                Active Processing Jobs ({activeJobs.length})
              </h3>
              {activeJobs.map((job) => (
                <div key={job.id} className="rounded-lg bg-muted p-3 mb-2">
                  <p className="text-sm">
                    Job {job.id}: {job.status} - {job.progress}%
                  </p>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                    <div
                      className="bg-primary h-2 rounded-full"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Discrepancies for Selected CAO */}
          {selectedCaoId && discrepancies && (
            <div className="mt-6">
              <h3 className="font-semibold mb-2">
                Discrepancies ({discrepancies.length})
              </h3>
              {discrepancies.map((disc) => (
                <div
                  key={disc.id}
                  className="flex items-center justify-between rounded-lg border p-3 mb-2"
                >
                  <div>
                    <p className="text-sm font-medium">{disc.fieldPath}</p>
                    <Badge variant="outline" className="mt-1">
                      {disc.type}
                    </Badge>
                  </div>
                  <Button
                    size="sm"
                    onClick={() =>
                      handleResolveDiscrepancy(disc.id, {
                        finalValue: disc.suggestedValue,
                        reasoning: "Accepted suggested value",
                      })
                    }
                    disabled={resolveDiscrepancyMutation.isPending}
                  >
                    Resolve
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Connection Status */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-sm">
              Connected to Backend API at{" "}
              <code className="bg-muted px-2 py-1 rounded">
                {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
              </code>
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}