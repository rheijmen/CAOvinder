"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  AlertCircle,
  CheckCircle,
  XCircle,
  Eye,
  GitCompare,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
  AlertTriangle,
  Info,
  FileText,
  Scale,
} from "lucide-react";
import { Discrepancy, FieldDecision } from "@/types";

// Mock data for demonstration
const mockDiscrepancies: Discrepancy[] = [
  {
    id: "d1",
    caoDocumentId: "cao-1",
    fieldPath: "loongebouw.schalen[0].bedrag",
    type: "mismatch",
    currentValue: 2650.50,
    suggestedValue: 2750.00,
    validationRule: "SETU.InquiryPayEquity.minimumWage",
    status: "open",
    priority: "high",
  },
  {
    id: "d2",
    caoDocumentId: "cao-1",
    fieldPath: "toeslagen.onregelmatigheid.percentage",
    type: "missing",
    currentValue: null,
    suggestedValue: 25,
    validationRule: "SETU.InquiryPayEquity.allowances.irregular",
    status: "reviewing",
    priority: "medium",
  },
  {
    id: "d3",
    caoDocumentId: "cao-1",
    fieldPath: "verlof.vakantiedagen",
    type: "ambiguous",
    currentValue: "20-25 dagen",
    suggestedValue: 23,
    validationRule: "SETU.InquiryPayEquity.leave.annual",
    status: "resolved",
    priority: "low",
    resolution: {
      finalValue: 23,
      resolvedBy: "admin@example.com",
      resolvedAt: new Date("2024-02-15"),
      reasoning: "Confirmed with HR: 23 days is the standard for this function group",
    },
  },
];

const mockJudgeDecisions: FieldDecision[] = [
  {
    fieldPath: "loongebouw.schalen[0].bedrag",
    geminiValue: 2650.50,
    mistralValue: 2750.00,
    finalValue: 2750.00,
    reasoning: "Mistral's value aligns with the current WML (Wettelijk Minimumloon) requirements effective January 2024",
    confidence: 92.5,
    source: "mistral",
  },
  {
    fieldPath: "toeslagen.onregelmatigheid.percentage",
    geminiValue: null,
    mistralValue: 25,
    finalValue: 25,
    reasoning: "Field was missed by Gemini extraction. Mistral correctly identified the irregular hours allowance in Article 7.2",
    confidence: 88.0,
    source: "mistral",
  },
];

const getPriorityColor = (priority: "low" | "medium" | "high") => {
  const colors = {
    low: "text-blue-600 bg-blue-50",
    medium: "text-yellow-600 bg-yellow-50",
    high: "text-red-600 bg-red-50",
  };
  return colors[priority];
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case "open":
      return <AlertCircle className="h-4 w-4 text-orange-500" />;
    case "reviewing":
      return <Eye className="h-4 w-4 text-blue-500" />;
    case "resolved":
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case "ignored":
      return <XCircle className="h-4 w-4 text-gray-500" />;
    default:
      return null;
  }
};

export default function CompliancePage() {
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState<Discrepancy | null>(null);
  const [resolutionReasoning, setResolutionReasoning] = useState("");
  const [resolvedValue, setResolvedValue] = useState("");
  const [isResolutionOpen, setIsResolutionOpen] = useState(false);

  const handleResolve = () => {
    console.log("Resolving:", {
      discrepancy: selectedDiscrepancy,
      value: resolvedValue,
      reasoning: resolutionReasoning,
    });
    setIsResolutionOpen(false);
    setResolutionReasoning("");
    setResolvedValue("");
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">SETU Compliance Review</h1>
          <p className="text-muted-foreground">
            Review and resolve SETU v2.0 compliance issues
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">Export Report</Button>
          <Button>Validate All</Button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Open Issues</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">12 high priority</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Under Review</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">7</div>
            <p className="text-xs text-muted-foreground">Awaiting approval</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Resolved Today</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">15</div>
            <p className="text-xs text-green-600">+25% from yesterday</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Compliance Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">87.3%</div>
            <p className="text-xs text-muted-foreground">SETU v2.0 compliant</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Discrepancies List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Discrepancies</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {mockDiscrepancies.map((discrepancy) => (
              <div
                key={discrepancy.id}
                className={`rounded-lg border p-3 cursor-pointer transition-colors hover:bg-muted/50 ${
                  selectedDiscrepancy?.id === discrepancy.id ? "border-primary bg-muted/50" : ""
                }`}
                onClick={() => setSelectedDiscrepancy(discrepancy)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-2">
                    {getStatusIcon(discrepancy.status)}
                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        {discrepancy.fieldPath.split(".").pop()?.replace(/[\[\]0-9]/g, "")}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {discrepancy.fieldPath}
                      </p>
                      <div className="flex gap-2">
                        <Badge
                          variant="outline"
                          className={getPriorityColor(discrepancy.priority)}
                        >
                          {discrepancy.priority}
                        </Badge>
                        <Badge variant="outline">
                          {discrepancy.type}
                        </Badge>
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Detail View */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Discrepancy Details</CardTitle>
          </CardHeader>
          <CardContent>
            {selectedDiscrepancy ? (
              <Tabs defaultValue="comparison" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="comparison">Comparison</TabsTrigger>
                  <TabsTrigger value="judge">Judge Report</TabsTrigger>
                  <TabsTrigger value="history">History</TabsTrigger>
                </TabsList>

                <TabsContent value="comparison" className="space-y-4">
                  {/* Field Information */}
                  <div className="rounded-lg bg-muted p-4">
                    <h4 className="font-semibold mb-2">Field Information</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Path:</span>
                        <code className="bg-background px-2 py-1 rounded">
                          {selectedDiscrepancy.fieldPath}
                        </code>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Validation Rule:</span>
                        <span>{selectedDiscrepancy.validationRule}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Issue Type:</span>
                        <Badge variant="outline">{selectedDiscrepancy.type}</Badge>
                      </div>
                    </div>
                  </div>

                  {/* Value Comparison */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-lg border p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <h4 className="font-semibold">Current Value</h4>
                      </div>
                      <div className="bg-background rounded p-3">
                        <code className="text-sm">
                          {JSON.stringify(selectedDiscrepancy.currentValue, null, 2) || "null"}
                        </code>
                      </div>
                    </div>

                    <div className="rounded-lg border p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Scale className="h-4 w-4 text-muted-foreground" />
                        <h4 className="font-semibold">Suggested Value</h4>
                      </div>
                      <div className="bg-green-50 dark:bg-green-900/20 rounded p-3 border border-green-200 dark:border-green-800">
                        <code className="text-sm">
                          {JSON.stringify(selectedDiscrepancy.suggestedValue, null, 2)}
                        </code>
                      </div>
                    </div>
                  </div>

                  {/* Resolution Actions */}
                  {selectedDiscrepancy.status !== "resolved" && (
                    <div className="flex gap-2">
                      <Dialog open={isResolutionOpen} onOpenChange={setIsResolutionOpen}>
                        <DialogTrigger asChild>
                          <Button className="flex-1">
                            <CheckCircle className="mr-2 h-4 w-4" />
                            Resolve with Suggested
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Resolve Discrepancy</DialogTitle>
                            <DialogDescription>
                              Provide the final value and reasoning for this resolution.
                            </DialogDescription>
                          </DialogHeader>
                          <div className="space-y-4 py-4">
                            <div>
                              <Label htmlFor="value">Final Value</Label>
                              <Input
                                id="value"
                                value={resolvedValue || selectedDiscrepancy.suggestedValue}
                                onChange={(e) => setResolvedValue(e.target.value)}
                                placeholder="Enter the resolved value"
                              />
                            </div>
                            <div>
                              <Label htmlFor="reasoning">Reasoning</Label>
                              <Textarea
                                id="reasoning"
                                value={resolutionReasoning}
                                onChange={(e) => setResolutionReasoning(e.target.value)}
                                placeholder="Explain why this value was chosen..."
                                rows={4}
                              />
                            </div>
                          </div>
                          <DialogFooter>
                            <Button variant="outline" onClick={() => setIsResolutionOpen(false)}>
                              Cancel
                            </Button>
                            <Button onClick={handleResolve}>Confirm Resolution</Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>

                      <Button variant="outline" className="flex-1">
                        <MessageSquare className="mr-2 h-4 w-4" />
                        Request Review
                      </Button>
                      <Button variant="outline">
                        <XCircle className="mr-2 h-4 w-4" />
                        Ignore
                      </Button>
                    </div>
                  )}

                  {/* Resolution Info */}
                  {selectedDiscrepancy.resolution && (
                    <div className="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <h4 className="font-semibold text-green-800 dark:text-green-200">
                          Resolved
                        </h4>
                      </div>
                      <div className="space-y-2 text-sm">
                        <div>
                          <span className="text-muted-foreground">Final Value: </span>
                          <code className="bg-white dark:bg-background px-2 py-1 rounded">
                            {JSON.stringify(selectedDiscrepancy.resolution.finalValue)}
                          </code>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Resolved by: </span>
                          {selectedDiscrepancy.resolution.resolvedBy}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Reasoning: </span>
                          {selectedDiscrepancy.resolution.reasoning}
                        </div>
                      </div>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="judge" className="space-y-4">
                  {/* Find the matching judge decision */}
                  {(() => {
                    const decision = mockJudgeDecisions.find(
                      (d) => d.fieldPath === selectedDiscrepancy.fieldPath
                    );
                    if (!decision) return <p>No judge report available for this field.</p>;

                    return (
                      <>
                        {/* Confidence Score */}
                        <div className="rounded-lg bg-muted p-4">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-semibold">Judge Confidence</h4>
                            <Badge
                              variant={decision.confidence > 90 ? "default" : "secondary"}
                            >
                              {decision.confidence.toFixed(1)}%
                            </Badge>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                decision.confidence > 90
                                  ? "bg-green-500"
                                  : decision.confidence > 70
                                  ? "bg-yellow-500"
                                  : "bg-red-500"
                              }`}
                              style={{ width: `${decision.confidence}%` }}
                            />
                          </div>
                        </div>

                        {/* LLM Comparison */}
                        <div className="space-y-3">
                          <h4 className="font-semibold">LLM Extraction Comparison</h4>
                          <div className="grid gap-3 md:grid-cols-2">
                            <div className="rounded-lg border p-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium">Gemini 2.5 Flash</span>
                                {decision.source === "gemini" && (
                                  <Badge variant="default" className="text-xs">
                                    Selected
                                  </Badge>
                                )}
                              </div>
                              <code className="text-sm bg-muted px-2 py-1 rounded">
                                {JSON.stringify(decision.geminiValue) || "null"}
                              </code>
                            </div>
                            <div className="rounded-lg border p-3">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium">Mistral Large</span>
                                {decision.source === "mistral" && (
                                  <Badge variant="default" className="text-xs">
                                    Selected
                                  </Badge>
                                )}
                              </div>
                              <code className="text-sm bg-muted px-2 py-1 rounded">
                                {JSON.stringify(decision.mistralValue) || "null"}
                              </code>
                            </div>
                          </div>
                        </div>

                        {/* Judge Reasoning */}
                        <div className="rounded-lg border p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <Info className="h-4 w-4 text-blue-500" />
                            <h4 className="font-semibold">Judge Reasoning</h4>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {decision.reasoning}
                          </p>
                        </div>

                        {/* Final Decision */}
                        <div className="rounded-lg bg-primary/10 p-4">
                          <h4 className="font-semibold mb-2">Final Decision</h4>
                          <code className="text-sm bg-background px-3 py-2 rounded block">
                            {JSON.stringify(decision.finalValue, null, 2)}
                          </code>
                        </div>
                      </>
                    );
                  })()}
                </TabsContent>

                <TabsContent value="history" className="space-y-4">
                  <div className="space-y-3">
                    <div className="rounded-lg border p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <AlertCircle className="h-4 w-4 text-orange-500" />
                          <div>
                            <p className="text-sm font-medium">Discrepancy Detected</p>
                            <p className="text-xs text-muted-foreground">
                              System • 2 days ago
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="rounded-lg border p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Eye className="h-4 w-4 text-blue-500" />
                          <div>
                            <p className="text-sm font-medium">Review Started</p>
                            <p className="text-xs text-muted-foreground">
                              admin@example.com • 1 day ago
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                    {selectedDiscrepancy.resolution && (
                      <div className="rounded-lg border p-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <div>
                              <p className="text-sm font-medium">Resolved</p>
                              <p className="text-xs text-muted-foreground">
                                {selectedDiscrepancy.resolution.resolvedBy} • 3 hours ago
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a discrepancy to view details</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}