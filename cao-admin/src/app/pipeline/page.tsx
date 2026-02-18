"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Play,
  Pause,
  RotateCcw,
  X,
  Clock,
  DollarSign,
  Cpu,
  FileText,
  ChevronRight,
  Settings,
  Zap,
  AlertTriangle,
  CheckCircle,
  GitBranch,
  Activity,
  TrendingUp,
} from "lucide-react";
import { ProcessingJob, PipelineStage, StageProgress } from "@/types";

// Mock pipeline stages
const pipelineStages: PipelineStage[] = [
  { id: "ocr", type: "ocr", provider: "mistral", config: {}, enabled: true, order: 1 },
  { id: "extract", type: "extract", provider: "gemini", config: { model: "gemini-2.5-flash" }, enabled: true, order: 2 },
  { id: "review", type: "review", provider: "mistral", config: { model: "mistral-large" }, enabled: true, order: 3 },
  { id: "judge", type: "judge", provider: "mistral", config: { model: "mistral-small-2506" }, enabled: true, order: 4 },
  { id: "validate", type: "validate", provider: "custom", config: {}, enabled: true, order: 5 },
];

// Mock active jobs
const mockJobs: ProcessingJob[] = [
  {
    id: "job-1",
    organizationId: "org-1",
    caoDocumentId: "cao-1",
    pipeline: {
      name: "Standard 3-LLM Pipeline",
      stages: pipelineStages,
      retryPolicy: { maxAttempts: 3, backoffMs: 5000 },
      costLimit: 10,
    },
    status: "running",
    progress: 65,
    stages: [
      { stageId: "ocr", status: "completed", completedAt: new Date(), tokensUsed: 1500, cost: 0.15 },
      { stageId: "extract", status: "completed", completedAt: new Date(), tokensUsed: 8000, cost: 0.80 },
      { stageId: "review", status: "running", startedAt: new Date() },
      { stageId: "judge", status: "pending" },
      { stageId: "validate", status: "pending" },
    ],
    cost: {
      estimated: 2.50,
      actual: 0.95,
      breakdown: { ocr: 0.15, llm: 0.80, storage: 0 },
    },
    startedAt: new Date(Date.now() - 300000), // 5 minutes ago
  },
  {
    id: "job-2",
    organizationId: "org-1",
    caoDocumentId: "cao-2",
    pipeline: {
      name: "Fast Extraction",
      stages: pipelineStages.slice(0, 2),
      retryPolicy: { maxAttempts: 2, backoffMs: 3000 },
    },
    status: "queued",
    progress: 0,
    stages: [],
    cost: {
      estimated: 1.20,
      breakdown: { ocr: 0.20, llm: 1.00, storage: 0 },
    },
  },
];

// Stage icons
const getStageIcon = (type: string) => {
  switch (type) {
    case "ocr": return <FileText className="h-4 w-4" />;
    case "extract": return <Cpu className="h-4 w-4" />;
    case "review": return <Activity className="h-4 w-4" />;
    case "judge": return <Zap className="h-4 w-4" />;
    case "validate": return <CheckCircle className="h-4 w-4" />;
    default: return <GitBranch className="h-4 w-4" />;
  }
};

// Stage status colors
const getStageStatusColor = (status: string) => {
  switch (status) {
    case "completed": return "bg-green-500";
    case "running": return "bg-blue-500 animate-pulse";
    case "failed": return "bg-red-500";
    case "pending": return "bg-gray-300";
    default: return "bg-gray-300";
  }
};

export default function PipelinePage() {
  const [selectedJob, setSelectedJob] = useState<ProcessingJob | null>(mockJobs[0]);
  const [activeTab, setActiveTab] = useState("active");

  const formatDuration = (start: Date) => {
    const diff = Date.now() - start.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Processing Pipeline</h1>
          <p className="text-muted-foreground">
            Monitor and control document processing jobs
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">
            <Settings className="mr-2 h-4 w-4" />
            Configure Pipeline
          </Button>
          <Button>
            <Play className="mr-2 h-4 w-4" />
            Start New Job
          </Button>
        </div>
      </div>

      {/* Pipeline Stats */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">Currently processing</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Queue Length</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">7</div>
            <p className="text-xs text-muted-foreground">Waiting to start</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Avg. Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">4.2m</div>
            <p className="text-xs text-green-600">-18% from last week</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">94.2%</div>
            <p className="text-xs text-green-600">+2.4% improvement</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Cost/Document</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">€2.38</div>
            <p className="text-xs text-muted-foreground">Average today</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Jobs List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Processing Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="active">Active</TabsTrigger>
                <TabsTrigger value="queue">Queue</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
              </TabsList>
              <TabsContent value="active" className="space-y-3">
                {mockJobs.filter(j => j.status === "running").map((job) => (
                  <div
                    key={job.id}
                    className={`rounded-lg border p-3 cursor-pointer transition-colors hover:bg-muted/50 ${
                      selectedJob?.id === job.id ? "border-primary bg-muted/50" : ""
                    }`}
                    onClick={() => setSelectedJob(job)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">CAO Document #{job.caoDocumentId}</p>
                        <p className="text-xs text-muted-foreground">{job.pipeline.name}</p>
                        <div className="flex items-center gap-2">
                          <Progress value={job.progress} className="h-1 w-20" />
                          <span className="text-xs">{job.progress}%</span>
                        </div>
                        {job.startedAt && (
                          <p className="text-xs text-muted-foreground">
                            Running for {formatDuration(job.startedAt)}
                          </p>
                        )}
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>
                ))}
              </TabsContent>
              <TabsContent value="queue" className="space-y-3">
                {mockJobs.filter(j => j.status === "queued").map((job, index) => (
                  <div
                    key={job.id}
                    className={`rounded-lg border p-3 cursor-pointer transition-colors hover:bg-muted/50 ${
                      selectedJob?.id === job.id ? "border-primary bg-muted/50" : ""
                    }`}
                    onClick={() => setSelectedJob(job)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <p className="text-sm font-medium">CAO Document #{job.caoDocumentId}</p>
                        <p className="text-xs text-muted-foreground">{job.pipeline.name}</p>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">Position #{index + 1}</Badge>
                          <span className="text-xs text-muted-foreground">
                            Est. €{job.cost.estimated.toFixed(2)}
                          </span>
                        </div>
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>
                ))}
              </TabsContent>
              <TabsContent value="history" className="space-y-3">
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No completed jobs in the last hour</p>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Job Details */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Job Details</CardTitle>
            {selectedJob && (
              <div className="flex gap-2">
                {selectedJob.status === "running" ? (
                  <Button size="sm" variant="outline">
                    <Pause className="mr-2 h-4 w-4" />
                    Pause
                  </Button>
                ) : (
                  <Button size="sm" variant="outline">
                    <Play className="mr-2 h-4 w-4" />
                    Resume
                  </Button>
                )}
                <Button size="sm" variant="outline">
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Retry
                </Button>
                <Button size="sm" variant="outline" className="text-destructive">
                  <X className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            {selectedJob ? (
              <div className="space-y-6">
                {/* Pipeline Visualization */}
                <div>
                  <h4 className="font-semibold mb-3">Pipeline Progress</h4>
                  <div className="flex items-center justify-between">
                    {selectedJob.pipeline.stages.map((stage, index) => {
                      const stageProgress = selectedJob.stages.find(s => s.stageId === stage.id);
                      const status = stageProgress?.status || "pending";

                      return (
                        <div key={stage.id} className="flex items-center">
                          <div className="flex flex-col items-center">
                            <div
                              className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                status === "completed"
                                  ? "bg-green-100 text-green-600"
                                  : status === "running"
                                  ? "bg-blue-100 text-blue-600"
                                  : status === "failed"
                                  ? "bg-red-100 text-red-600"
                                  : "bg-gray-100 text-gray-400"
                              }`}
                            >
                              {getStageIcon(stage.type)}
                            </div>
                            <span className="text-xs mt-1">{stage.type}</span>
                            <span className="text-xs text-muted-foreground">
                              {stage.provider}
                            </span>
                          </div>
                          {index < selectedJob.pipeline.stages.length - 1 && (
                            <div
                              className={`h-0.5 w-12 mx-2 ${
                                stageProgress?.status === "completed"
                                  ? "bg-green-500"
                                  : "bg-gray-300"
                              }`}
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Stage Details */}
                <div>
                  <h4 className="font-semibold mb-3">Stage Details</h4>
                  <div className="space-y-2">
                    {selectedJob.stages.map((stage) => {
                      const stageConfig = selectedJob.pipeline.stages.find(s => s.id === stage.stageId);
                      return (
                        <div
                          key={stage.stageId}
                          className="flex items-center justify-between rounded-lg border p-3"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${getStageStatusColor(stage.status)}`} />
                            <div>
                              <p className="text-sm font-medium capitalize">{stage.stageId}</p>
                              <p className="text-xs text-muted-foreground">
                                {stageConfig?.provider} • {stageConfig?.config?.model || "default"}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            {stage.tokensUsed && (
                              <p className="text-xs text-muted-foreground">
                                {stage.tokensUsed.toLocaleString()} tokens
                              </p>
                            )}
                            {stage.cost && (
                              <p className="text-xs font-medium">€{stage.cost.toFixed(2)}</p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Cost Breakdown */}
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-lg bg-muted p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Estimated Cost</span>
                      <DollarSign className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <p className="text-2xl font-bold">€{selectedJob.cost.estimated.toFixed(2)}</p>
                    {selectedJob.pipeline.costLimit && (
                      <p className="text-xs text-muted-foreground">
                        Limit: €{selectedJob.pipeline.costLimit}
                      </p>
                    )}
                  </div>
                  <div className="rounded-lg bg-muted p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Actual Cost</span>
                      <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <p className="text-2xl font-bold">
                      €{(selectedJob.cost.actual || 0).toFixed(2)}
                    </p>
                    <div className="text-xs text-muted-foreground">
                      OCR: €{selectedJob.cost.breakdown.ocr.toFixed(2)} •
                      LLM: €{selectedJob.cost.breakdown.llm.toFixed(2)}
                    </div>
                  </div>
                </div>

                {/* Job Metadata */}
                <div className="rounded-lg border p-4">
                  <h4 className="font-semibold mb-2">Job Information</h4>
                  <div className="grid gap-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Job ID:</span>
                      <code className="bg-muted px-2 py-0.5 rounded">{selectedJob.id}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Document ID:</span>
                      <code className="bg-muted px-2 py-0.5 rounded">{selectedJob.caoDocumentId}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Started:</span>
                      <span>
                        {selectedJob.startedAt
                          ? new Date(selectedJob.startedAt).toLocaleString()
                          : "Not started"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Retry Policy:</span>
                      <span>
                        {selectedJob.pipeline.retryPolicy.maxAttempts} attempts,
                        {selectedJob.pipeline.retryPolicy.backoffMs}ms backoff
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <GitBranch className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a job to view details</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* LLM Provider Status */}
      <Card>
        <CardHeader>
          <CardTitle>LLM Provider Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {["Gemini 2.5 Flash", "Mistral Large", "Mistral Small"].map((llm) => (
              <div key={llm} className="rounded-lg border p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold">{llm}</h4>
                  <div className="flex items-center gap-1">
                    <div className="h-2 w-2 rounded-full bg-green-500" />
                    <span className="text-xs text-green-600">Online</span>
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Latency:</span>
                    <span>245ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Rate:</span>
                    <span>€0.10/1M tokens</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Used today:</span>
                    <span>1.2M tokens</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}