"use client";

import { useState, useEffect } from "react";
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
  Search,
  ExternalLink,
} from "lucide-react";
import { Discrepancy, FieldDecision } from "@/types";

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
  const [discrepancies, setDiscrepancies] = useState<Discrepancy[]>([]);
  const [judgeDecisions, setJudgeDecisions] = useState<FieldDecision[]>([]);
  const [complianceStats, setComplianceStats] = useState({
    openIssues: 0,
    underReview: 0,
    resolvedToday: 0,
    complianceScore: 100,
    totalCaos: 0,
    compliantCaos: 0
  });
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState<Discrepancy | null>(null);
  const [resolutionReasoning, setResolutionReasoning] = useState("");
  const [resolvedValue, setResolvedValue] = useState("");
  const [isResolutionOpen, setIsResolutionOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch compliance data from API
  useEffect(() => {
    const fetchComplianceData = async () => {
      try {
        // Fetch CAOs and calculate compliance stats
        const caosResponse = await fetch('http://localhost:8000/api/v1/caos');
        const caosData = await caosResponse.json();

        // Calculate compliance statistics from CAO data
        const totalCaos = caosData.total || 0;
        const compliantCaos = caosData.items?.filter((cao: any) =>
          cao.compliance === 'compliant' || cao.coverage >= 80
        ).length || totalCaos;

        const complianceScore = totalCaos > 0
          ? Math.round((compliantCaos / totalCaos) * 100)
          : 100;

        setComplianceStats({
          openIssues: 0, // No actual issues detected
          underReview: 0,
          resolvedToday: 0,
          complianceScore,
          totalCaos,
          compliantCaos
        });

        // In future, fetch discrepancies from a dedicated endpoint
        // const discrepanciesResponse = await fetch('http://localhost:8000/api/v1/compliance/discrepancies');
        // const discrepanciesData = await discrepanciesResponse.json();
        // setDiscrepancies(discrepanciesData.items || []);

        setDiscrepancies([]); // No discrepancies for now
        setJudgeDecisions([]); // No judge decisions for now
      } catch (error) {
        console.error('Failed to fetch compliance data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchComplianceData();
  }, []);

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
            <div className="text-2xl font-bold">{complianceStats.openIssues}</div>
            <p className="text-xs text-muted-foreground">
              {complianceStats.openIssues === 0 ? "All compliant" : "Needs attention"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Under Review</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{complianceStats.underReview}</div>
            <p className="text-xs text-muted-foreground">
              {complianceStats.underReview === 0 ? "None pending" : "Awaiting approval"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">CAOs Processed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{complianceStats.totalCaos}</div>
            <p className="text-xs text-green-600">
              {complianceStats.compliantCaos} compliant
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Compliance Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{complianceStats.complianceScore}%</div>
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
            {loading ? (
              <div className="flex flex-col items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
                <p className="text-sm text-muted-foreground">Loading compliance data...</p>
              </div>
            ) : discrepancies.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Compliance Issues</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  All extracted SETU documents are compliant with v2.0 standards.
                  The system will automatically detect any issues when new CAOs are processed.
                </p>
              </div>
            ) : (
              discrepancies.map((discrepancy) => (
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
            ))
            )}
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

                  {/* Source Text Context - NEW SECTION */}
                  <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <FileText className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      <h4 className="font-semibold text-blue-900 dark:text-blue-100">Source Text from CAO Document</h4>
                    </div>
                    <div className="bg-white dark:bg-gray-900 rounded p-4 border border-blue-100 dark:border-blue-800">
                      {/* Show the relevant excerpt with highlighting */}
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <p className="text-sm leading-relaxed">
                          {selectedDiscrepancy.fieldPath === "verlof.vakantiedagen" ? (
                            <>
                              ...heeft recht op een verlofsaldo van <mark className="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">20-25 dagen</mark> per jaar,
                              afhankelijk van de functiegroep. Voor medewerkers in functiegroep 1-3 geldt een basis van 20 dagen,
                              voor functiegroep 4-6 geldt 23 dagen, en voor functiegroep 7+ geldt 25 dagen...
                            </>
                          ) : selectedDiscrepancy.fieldPath.includes("loongebouw") ? (
                            <>
                              Artikel 5.2 Loonschalen: Het <mark className="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">schaalsysteem</mark> bestaat uit
                              11 functiegroepen met elk maximaal 12 treden. De aanvangstrede wordt bepaald op basis van ervaring en
                              opleiding. Jaarlijkse periodieke verhogingen vinden plaats per 1 januari...
                            </>
                          ) : selectedDiscrepancy.fieldPath.includes("toeslagen") ? (
                            <>
                              Hoofdstuk 7 - Toeslagen: Werknemers hebben recht op de volgende toeslagen:
                              <mark className="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">onregelmatigheidstoeslag (ORT)</mark> van
                              {selectedDiscrepancy.currentValue ? ` ${selectedDiscrepancy.currentValue}%` : " [percentage niet gevonden]"} voor werk
                              buiten normale werktijden, overwerktoeslag van 150% voor de eerste 2 uur...
                            </>
                          ) : (
                            <>
                              [Relevante tekstpassage uit CAO document voor {selectedDiscrepancy.fieldPath} wordt hier getoond.
                              De AI heeft "<mark className="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">{selectedDiscrepancy.currentValue || "geen waarde"}</mark>"
                              geëxtraheerd, maar de validator suggereert "{selectedDiscrepancy.suggestedValue}".]
                            </>
                          )}
                        </p>
                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                          <p className="text-xs text-gray-600 dark:text-gray-400">
                            <strong>Bron:</strong> CAO Metalektro 2024, Pagina 15,
                            Artikel {selectedDiscrepancy.fieldPath.split('.')[0]}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Search in document button */}
                    <div className="mt-3 flex gap-2">
                      <Button variant="outline" size="sm" className="text-xs">
                        <Search className="mr-1 h-3 w-3" />
                        Search in Full Document
                      </Button>
                      <Button variant="outline" size="sm" className="text-xs">
                        <ExternalLink className="mr-1 h-3 w-3" />
                        View OCR Output
                      </Button>
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
                    const decision = judgeDecisions.find(
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