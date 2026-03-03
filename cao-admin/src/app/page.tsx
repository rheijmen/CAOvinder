"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  FileText,
  TrendingUp,
  AlertCircle,
  Clock,
  DollarSign,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Upload,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ProcessingStatus, ComplianceStatus } from "@/types";
import { useCaoDocuments, useProcessingJobs } from "@/lib/api/hooks";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { retryJob, pollJobStatus } from "@/lib/api/processing";
import { useState } from "react";
import { Progress } from "@/components/ui/progress";

const getStatusBadge = (status: ProcessingStatus) => {
  const variants: Record<ProcessingStatus, any> = {
    uploaded: { variant: "secondary", icon: Upload },
    queued: { variant: "secondary", icon: Clock },
    ocr_processing: { variant: "secondary", icon: Clock },
    ocr_complete: { variant: "secondary", icon: CheckCircle2 },
    extracting: { variant: "default", icon: Clock },
    reviewing: { variant: "default", icon: Clock },
    judging: { variant: "default", icon: Clock },
    complete: { variant: "success", icon: CheckCircle2 },
    failed: { variant: "destructive", icon: XCircle },
    requires_review: { variant: "warning", icon: AlertCircle },
  };

  const { variant, icon: Icon } = variants[status] || variants.uploaded;

  return (
    <Badge variant={variant as any} className="gap-1">
      <Icon className="h-3 w-3" />
      {status.replace(/_/g, " ")}
    </Badge>
  );
};

const getComplianceBadge = (compliance: ComplianceStatus | undefined | null) => {
  // Handle undefined or null compliance status
  const status = compliance || "unknown";

  const variants: Record<ComplianceStatus, string> = {
    compliant: "success",
    partial: "warning",
    non_compliant: "destructive",
    version_mismatch: "secondary",
    unknown: "outline",
  };

  return (
    <Badge variant={variants[status] as any}>
      {status.replace(/_/g, " ")}
    </Badge>
  );
};

export default function DashboardPage() {
  // Fetch REAL data from backend
  const { data: caoResponse, isLoading: caosLoading } = useCaoDocuments({
    page: 1
  });

  const { data: jobsData, isLoading: jobsLoading } = useProcessingJobs();

  // Retry state
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryStatus, setRetryStatus] = useState<string | null>(null);

  const handleRetry = async (jobId: string) => {
    setIsRetrying(true);
    setRetryStatus("Initiating retry...");

    try {
      const result = await retryJob(jobId);
      setRetryStatus("Retry started successfully");

      // Poll for job status updates
      await pollJobStatus(
        jobId,
        (job) => {
          setRetryStatus(`${job.stage}: ${job.message}`);
        },
        2000
      );

      setRetryStatus("Pipeline completed successfully!");
    } catch (error) {
      console.error("Retry failed:", error);
      setRetryStatus(`Retry failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsRetrying(false);
      // Clear status after 5 seconds
      setTimeout(() => setRetryStatus(null), 5000);
    }
  };

  // Calculate real stats from backend data
  const totalCAOs = caoResponse?.total || 0;
  const recentCAOs = caoResponse?.data || [];
  const activeJobs = jobsData?.filter(job => job.status === 'running') || [];
  const queuedJobs = jobsData?.filter(job => job.status === 'queued') || [];

  // Calculate processing rate (example: completed vs total in last 30 days)
  const completedCAOs = recentCAOs.filter(cao => cao.status === 'complete').length;
  const processingRate = totalCAOs > 0
    ? ((completedCAOs / totalCAOs) * 100).toFixed(1)
    : 0;

  // Count pending review
  const pendingReview = recentCAOs.filter(
    cao => cao.status === 'requires_review' || cao.complianceStatus === 'partial'
  ).length;

  // Calculate average processing time from jobs
  const avgProcessingTime = jobsData && jobsData.length > 0
    ? jobsData.reduce((acc, job) => acc + (job.progress || 0), 0) / jobsData.length
    : 0;

  // Calculate costs (example based on job count)
  const todayCost = activeJobs.length * 2.50 + queuedJobs.length * 0.5;
  const monthlyBudget = 3700;
  const monthlyCost = todayCost * 30; // Rough estimate

  const stats = [
    {
      title: "Total CAOs",
      value: totalCAOs.toString(),
      change: totalCAOs > 0 ? `${recentCAOs.length} recent` : "No data",
      changeLabel: "in database",
      icon: FileText,
    },
    {
      title: "Processing Rate",
      value: `${processingRate}%`,
      change: completedCAOs > 0 ? `${completedCAOs} completed` : "0",
      changeLabel: "documents",
      icon: TrendingUp,
    },
    {
      title: "Pending Review",
      value: pendingReview.toString(),
      change: pendingReview > 10 ? `${Math.floor(pendingReview/2)} urgent` : "None urgent",
      changeLabel: pendingReview > 0 ? "requires attention" : "",
      icon: AlertCircle,
      urgent: pendingReview > 10,
    },
    {
      title: "Active Jobs",
      value: activeJobs.length.toString(),
      change: queuedJobs.length > 0 ? `${queuedJobs.length} queued` : "None queued",
      changeLabel: "",
      icon: Clock,
    },
    {
      title: "Today's Cost",
      value: `€${todayCost.toFixed(2)}`,
      change: `€${(monthlyBudget - monthlyCost).toFixed(0)}`,
      changeLabel: "budget remaining",
      icon: DollarSign,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time overview of your CAO processing pipeline
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">Download Report</Button>
          <Link href="/cao">
            <Button className="gap-2">
              <Upload className="h-4 w-4" />
              Upload CAO
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <Icon
                  className={`h-4 w-4 ${
                    stat.urgent ? "text-destructive" : "text-muted-foreground"
                  }`}
                />
              </CardHeader>
              <CardContent>
                {caosLoading || jobsLoading ? (
                  <div>
                    <Skeleton className="h-8 w-20 mb-1" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                ) : (
                  <>
                    <div className="text-2xl font-bold">{stat.value}</div>
                    <p className="text-xs text-muted-foreground">
                      <span
                        className={
                          stat.urgent ? "text-destructive font-semibold" : ""
                        }
                      >
                        {stat.change}
                      </span>{" "}
                      {stat.changeLabel}
                    </p>
                  </>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Recent CAOs and Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent CAOs */}
        <Card className="col-span-1">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent CAO Processing</CardTitle>
            <Link href="/cao">
              <Button variant="ghost" size="sm" className="gap-1">
                View all <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {caosLoading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex items-center space-x-4">
                    <Skeleton className="h-12 w-full" />
                  </div>
                ))}
              </div>
            ) : recentCAOs.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>CAO Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Compliance</TableHead>
                    <TableHead className="text-right">Confidence</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentCAOs.slice(0, 5).map((cao) => (
                    <TableRow key={cao.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{cao.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {cao.company || "Unknown company"}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>{getStatusBadge(cao.status)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getComplianceBadge(cao.complianceStatus)}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        {cao.metadata?.confidence ? (
                          <span
                            className={
                              cao.metadata.confidence > 90
                                ? "text-green-600"
                                : cao.metadata.confidence > 70
                                ? "text-yellow-600"
                                : "text-red-600"
                            }
                          >
                            {cao.metadata.confidence.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8">
                <p className="text-muted-foreground">No CAO documents yet</p>
                <Link href="/cao">
                  <Button variant="outline" size="sm" className="mt-3">
                    Upload First CAO
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pipeline Status */}
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Pipeline Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Show real jobs from API if any are running or failed */}
              {activeJobs.length > 0 ? (
                activeJobs
                  .filter((job: any) => job.status === 'failed' || job.status === 'running')
                  .slice(0, 1) // Show only the most recent job
                  .map((job: any) => (
                    <div key={job.id} className={`rounded-lg p-4 border shadow-sm ${
                      job.status === 'failed'
                        ? 'bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-950/30 dark:to-orange-950/30 border-red-300 dark:border-red-700'
                        : 'bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-950/30 dark:to-cyan-950/30 border-blue-300 dark:border-blue-700'
                    }`}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="relative">
                            <div className={`h-3 w-3 ${job.status === 'failed' ? 'bg-red-500' : 'bg-blue-500 animate-pulse'} rounded-full`}></div>
                          </div>
                          <div>
                            <p className={`text-sm font-bold ${job.status === 'failed' ? 'text-red-900 dark:text-red-100' : 'text-blue-900 dark:text-blue-100'}`}>
                              {job.status === 'failed' ? '⚠️ FAILED: ' : '🔄 PROCESSING: '}{job.cao_name}
                            </p>
                            <p className={`text-xs ${job.status === 'failed' ? 'text-red-700 dark:text-red-300' : 'text-blue-700 dark:text-blue-300'}`}>
                              {job.message || job.error_details}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className={`text-lg font-bold ${job.status === 'failed' ? 'text-red-900 dark:text-red-100' : 'text-blue-900 dark:text-blue-100'}`}>
                            {job.progress}%
                          </p>
                          <p className={`text-xs ${job.status === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400'}`}>
                            {job.status}
                          </p>
                        </div>
                      </div>
                      <Progress value={job.progress} className={`h-2 ${job.status === 'failed' ? 'bg-red-100 dark:bg-red-900' : 'bg-blue-100 dark:bg-blue-900'}`} />
                      {job.status === 'failed' && job.retry_from_step && (
                        <div className="mt-2 pt-2 border-t border-red-200 dark:border-red-800">
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs"
                            onClick={() => handleRetry(job.id)}
                            disabled={isRetrying}
                          >
                            {isRetrying ? "⏳ Retrying..." : `🔄 Retry from Step ${job.retry_from_step}`}
                          </Button>
                          {retryStatus && (
                            <p className="mt-1 text-xs text-muted-foreground">{retryStatus}</p>
                          )}
                        </div>
                      )}
                    </div>
                  ))
              ) : (
                <div className="rounded-lg border p-4">
                  <p className="text-sm text-muted-foreground text-center">No active processing jobs</p>
                </div>
              )}

              {/* Active Jobs Summary */}
              <div className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-3">
                  <div className={`h-2 w-2 ${activeJobs.length > 0 ? 'animate-pulse bg-green-500' : 'bg-gray-300'} rounded-full`} />
                  <div>
                    <p className="text-sm font-medium">Queue Status</p>
                    <div className="text-xs text-muted-foreground">
                      {jobsLoading ? (
                        <Skeleton className="h-3 w-24" />
                      ) : (
                        `${activeJobs.length} documents in pipeline`
                      )}
                    </div>
                  </div>
                </div>
                <Link href="/pipeline">
                  <Button variant="ghost" size="sm">
                    View All
                  </Button>
                </Link>
              </div>

              {/* Queue */}
              <div className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-3">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Queue</p>
                    <div className="text-xs text-muted-foreground">
                      {jobsLoading ? (
                        <Skeleton className="h-3 w-24" />
                      ) : (
                        `${queuedJobs.length} documents waiting`
                      )}
                    </div>
                  </div>
                </div>
                <Link href="/pipeline">
                  <Button variant="ghost" size="sm">
                    Manage
                  </Button>
                </Link>
              </div>

              {/* LLM Status (This could be fetched from backend too) */}
              <div className="space-y-2">
                <p className="text-sm font-medium">LLM Availability</p>
                <div className="grid grid-cols-3 gap-2">
                  {["Gemini", "Mistral", "Claude"].map((llm) => (
                    <div
                      key={llm}
                      className="flex items-center gap-2 rounded-lg border px-3 py-2"
                    >
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                      <span className="text-xs">{llm}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cost Today */}
              <div className="rounded-lg bg-muted p-3">
                <p className="text-sm font-medium">Cost Today</p>
                {jobsLoading ? (
                  <Skeleton className="h-8 w-24 mt-1" />
                ) : (
                  <>
                    <p className="text-2xl font-bold">€{todayCost.toFixed(2)}</p>
                    <div className="mt-2 flex gap-4 text-xs">
                      <span>OCR: €{(todayCost * 0.2).toFixed(2)}</span>
                      <span>LLM: €{(todayCost * 0.8).toFixed(2)}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}