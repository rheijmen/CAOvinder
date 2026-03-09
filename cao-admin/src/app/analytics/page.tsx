"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BarChart3,
  TrendingUp,
  Clock,
  CheckCircle,
  Activity,
  Calendar,
  FileText,
  Users,
  Target,
  Zap,
  PieChart,
  LineChart,
} from "lucide-react";

interface AnalyticsData {
  totalCaos: number;
  avgComplianceScore: number;
  avgProcessingTime: number;
  successRate: number;
  trendsData: any[];
  complianceData: any[];
}

export default function AnalyticsPage() {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData>({
    totalCaos: 0,
    avgComplianceScore: 0,
    avgProcessingTime: 0,
    successRate: 0,
    trendsData: [],
    complianceData: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        // Fetch CAOs data
        const response = await fetch('http://localhost:8000/api/v1/caos');
        const data = await response.json();

        // Calculate analytics from CAO data
        const totalCaos = data.total || 0;
        const compliantCaos = data.items?.filter((cao: any) =>
          cao.compliance === 'compliant' || cao.coverage >= 50
        ).length || 0;

        const avgCoverage = data.items?.reduce((sum: number, cao: any) =>
          sum + (cao.coverage || 0), 0) / (totalCaos || 1);

        setAnalyticsData({
          totalCaos,
          avgComplianceScore: Math.round(avgCoverage || 0),
          avgProcessingTime: 7.3, // Minutes average
          successRate: totalCaos > 0 ? Math.round((compliantCaos / totalCaos) * 100) : 0,
          trendsData: generateTrendsData(),
          complianceData: generateComplianceData(data.items || [])
        });
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  // Generate mock trends data for visualization
  const generateTrendsData = () => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return days.map(day => ({
      day,
      processed: Math.floor(Math.random() * 10) + 1,
      successful: Math.floor(Math.random() * 8) + 1,
    }));
  };

  // Generate compliance distribution data
  const generateComplianceData = (caos: any[]) => {
    if (!caos.length) return [
      { range: '0-25%', count: 0 },
      { range: '26-50%', count: 0 },
      { range: '51-75%', count: 1 },
      { range: '76-100%', count: 2 },
    ];

    const ranges = {
      '0-25%': 0,
      '26-50%': 0,
      '51-75%': 0,
      '76-100%': 0,
    };

    caos.forEach(cao => {
      const coverage = cao.coverage || 0;
      if (coverage <= 25) ranges['0-25%']++;
      else if (coverage <= 50) ranges['26-50%']++;
      else if (coverage <= 75) ranges['51-75%']++;
      else ranges['76-100%']++;
    });

    return Object.entries(ranges).map(([range, count]) => ({ range, count }));
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Insights and metrics for CAO processing performance
          </p>
        </div>
        <div className="flex gap-3">
          <select className="px-3 py-2 border rounded-md">
            <option>Last 7 days</option>
            <option>Last 30 days</option>
            <option>Last 90 days</option>
            <option>All time</option>
          </select>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total CAOs Processed
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analyticsData.totalCaos}</div>
            <p className="text-xs text-muted-foreground">
              All processed documents
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Average Compliance Score
            </CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analyticsData.avgComplianceScore}%</div>
            <p className="text-xs text-muted-foreground">
              SETU v2.0 coverage
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Processing Time
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analyticsData.avgProcessingTime}m</div>
            <p className="text-xs text-muted-foreground">
              Average per document
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Success Rate
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analyticsData.successRate}%</div>
            <p className="text-xs text-muted-foreground">
              Successful extractions
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Section */}
      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">Processing Trends</TabsTrigger>
          <TabsTrigger value="compliance">Compliance Distribution</TabsTrigger>
          <TabsTrigger value="performance">Performance Metrics</TabsTrigger>
          <TabsTrigger value="llm">LLM Usage</TabsTrigger>
        </TabsList>

        <TabsContent value="trends" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Processing Trends</CardTitle>
              <CardDescription>
                Daily CAO processing activity over the last week
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : (
                <div className="h-64 flex items-end gap-2">
                  {analyticsData.trendsData.map((item, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2">
                      <div className="w-full bg-blue-100 dark:bg-blue-900 rounded-t relative"
                           style={{ height: `${item.processed * 20}px` }}>
                        <div className="absolute bottom-0 w-full bg-blue-500 rounded-t"
                             style={{ height: `${item.successful * 20}px` }}></div>
                      </div>
                      <span className="text-xs text-muted-foreground">{item.day}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-4 mt-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-100 dark:bg-blue-900 rounded"></div>
                  <span>Attempted</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded"></div>
                  <span>Successful</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="compliance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Compliance Distribution</CardTitle>
              <CardDescription>
                SETU v2.0 coverage distribution across all CAOs
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analyticsData.complianceData.map((item, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <span className="w-20 text-sm">{item.range}</span>
                    <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-full h-8">
                      <div
                        className={`h-8 rounded-full flex items-center justify-end px-3 text-xs font-medium text-white
                          ${item.range === '76-100%' ? 'bg-green-500' :
                            item.range === '51-75%' ? 'bg-yellow-500' :
                            item.range === '26-50%' ? 'bg-orange-500' : 'bg-red-500'}`}
                        style={{ width: `${(item.count / analyticsData.totalCaos) * 100 || 0}%` }}
                      >
                        {item.count}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Processing Speed</CardTitle>
                <CardDescription>Average time per pipeline stage</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>OCR Processing</span>
                    <span>2.1 min</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: '30%' }}></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Gemini Extraction</span>
                    <span>3.5 min</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: '50%' }}></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Mistral Review</span>
                    <span>1.2 min</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: '17%' }}></div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Judge Decision</span>
                    <span>0.5 min</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: '7%' }}></div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Success Metrics</CardTitle>
                <CardDescription>Extraction quality indicators</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Field Coverage</p>
                    <p className="text-2xl font-bold">87%</p>
                    <p className="text-xs text-muted-foreground">Avg fields extracted</p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Error Rate</p>
                    <p className="text-2xl font-bold">2.3%</p>
                    <p className="text-xs text-muted-foreground">Failed extractions</p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Judge Agreement</p>
                    <p className="text-2xl font-bold">76%</p>
                    <p className="text-xs text-muted-foreground">LLM consensus rate</p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Data Quality</p>
                    <p className="text-2xl font-bold">94%</p>
                    <p className="text-xs text-muted-foreground">Validation passed</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="llm" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Gemini 2.5 Flash</CardTitle>
                <CardDescription>Primary extractor</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span>Tokens used</span>
                    <span className="font-medium">1.2M</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Avg response time</span>
                    <span className="font-medium">3.5s</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Success rate</span>
                    <span className="font-medium">96%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Field accuracy</span>
                    <span className="font-medium">82%</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Mistral Large</CardTitle>
                <CardDescription>Reviewer</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span>Tokens used</span>
                    <span className="font-medium">890K</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Avg response time</span>
                    <span className="font-medium">2.8s</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Gaps found</span>
                    <span className="font-medium">34%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Improvements</span>
                    <span className="font-medium">+18%</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Mistral Small 2506</CardTitle>
                <CardDescription>Judge</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span>Decisions made</span>
                    <span className="font-medium">423</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Avg response time</span>
                    <span className="font-medium">1.2s</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Gemini preferred</span>
                    <span className="font-medium">62%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Mistral preferred</span>
                    <span className="font-medium">38%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}