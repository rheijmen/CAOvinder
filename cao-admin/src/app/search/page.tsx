"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search,
  Building2,
  Briefcase,
  Hash,
  Calendar,
  TrendingUp,
  FileText,
  ArrowRight,
  AlertCircle,
  CheckCircle,
  Clock,
  Euro,
  Users,
  Calculator,
  Shield,
  BookOpen,
} from "lucide-react";

interface CAOResult {
  id: string;
  name: string;
  sector: string;
  company?: string;
  effective_from: string;
  effective_to: string;
  coverage_score: number;
  document_count: number;
  has_salary_scales: boolean;
  match_type: string;
  match_score: number;
}

export default function SearchPage() {
  const [searchType, setSearchType] = useState<"company" | "sector" | "kvk">("company");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<CAOResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [autoDetected, setAutoDetected] = useState(false);

  const detectSearchType = (query: string): "company" | "sector" | "kvk" => {
    // Check if it's a KVK number (8 digits)
    if (/^\d{8}$/.test(query.trim())) {
      return "kvk";
    }

    // Common sector keywords
    const sectorKeywords = ["metaal", "elektro", "handel", "zorg", "transport", "bouw", "horeca", "onderwijs", "logistiek", "industrie"];
    const queryLower = query.toLowerCase();
    if (sectorKeywords.some(keyword => queryLower.includes(keyword))) {
      return "sector";
    }

    // Default to company
    return "company";
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setHasSearched(true);
    setAutoDetected(false);

    try {
      // Try all search types if no results with current type
      let effectiveSearchType = searchType;
      let data = null;

      // First try with selected type
      const params1 = new URLSearchParams();
      params1.append(effectiveSearchType, searchQuery);
      const response1 = await fetch(`http://localhost:8000/api/v2/search/cao?${params1}`);
      data = await response1.json();

      // If no results and searchType is company, try auto-detection
      if (data.total === 0 && searchType === "company") {
        const detectedType = detectSearchType(searchQuery);
        if (detectedType !== searchType) {
          const params2 = new URLSearchParams();
          params2.append(detectedType, searchQuery);
          const response2 = await fetch(`http://localhost:8000/api/v2/search/cao?${params2}`);
          const data2 = await response2.json();

          if (data2.total > 0) {
            data = data2;
            effectiveSearchType = detectedType;
            setSearchType(detectedType);
            setAutoDetected(true);
          }
        }
      }

      setSearchResults(data.results || []);
      setSuggestions(data.suggestions || []);
    } catch (error) {
      console.error("Search failed:", error);
      setSearchResults([]);
      setSuggestions(["Connection error. Please try again."]);
    } finally {
      setIsSearching(false);
    }
  };

  const getMatchBadgeColor = (score: number) => {
    if (score >= 90) return "default";
    if (score >= 70) return "secondary";
    return "outline";
  };

  const getComplianceBadgeColor = (score: number) => {
    if (score >= 85) return "default";
    if (score >= 70) return "secondary";
    return "destructive";
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("nl-NL", {
      year: "numeric",
      month: "long",
      day: "numeric"
    });
  };

  const isCAOExpiringSoon = (effectiveTo: string) => {
    const endDate = new Date(effectiveTo);
    const monthsUntilExpiry = (endDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24 * 30);
    return monthsUntilExpiry < 6;
  };

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 rounded-lg p-8">
        <div className="max-w-3xl">
          <h1 className="text-4xl font-bold tracking-tight mb-3">
            Find Your Applicable CAO
          </h1>
          <p className="text-lg text-muted-foreground mb-6">
            Search for the correct Collective Labour Agreement for your company or sector.
            Ensure compliance with gelijkwaardige beloning starting January 2026.
          </p>

          {/* Search Tabs */}
          <Card>
            <CardHeader className="pb-3">
              <Tabs value={searchType} onValueChange={(v) => setSearchType(v as any)}>
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="company">
                    <Building2 className="mr-2 h-4 w-4" />
                    Company
                  </TabsTrigger>
                  <TabsTrigger value="sector">
                    <Briefcase className="mr-2 h-4 w-4" />
                    Sector
                  </TabsTrigger>
                  <TabsTrigger value="kvk">
                    <Hash className="mr-2 h-4 w-4" />
                    KVK Number
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>
            <CardContent>
              <div className="flex gap-3">
                <Input
                  placeholder={
                    searchType === "company"
                      ? "Enter company name (e.g., Achmea, IKEA)"
                      : searchType === "sector"
                      ? "Enter sector (e.g., Metalektro, Transport)"
                      : "Enter KVK number (e.g., 12345678)"
                  }
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="flex-1"
                />
                <Button onClick={handleSearch} disabled={isSearching}>
                  <Search className="mr-2 h-4 w-4" />
                  {isSearching ? "Searching..." : "Search CAO"}
                </Button>
              </div>
              {autoDetected && (
                <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-950 rounded-md flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-blue-600" />
                  <span className="text-sm">
                    Auto-detected search type changed to <strong>{searchType}</strong> based on your query
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Quick Stats */}
      {!hasSearched && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total CAOs</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">743</div>
              <p className="text-xs text-muted-foreground">Active agreements</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Coverage</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">2.3M</div>
              <p className="text-xs text-muted-foreground">Workers covered</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Compliance Date</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">Jan 2026</div>
              <p className="text-xs text-muted-foreground">Gelijkwaardige beloning</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Compliance</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">82%</div>
              <p className="text-xs text-muted-foreground">SETU coverage</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search Results */}
      {hasSearched && (
        <div className="space-y-4">
          {searchResults.length > 0 ? (
            <>
              <h2 className="text-2xl font-semibold">
                Found {searchResults.length} matching CAO{searchResults.length > 1 ? "s" : ""}
              </h2>

              {searchResults.map((cao) => (
                <Card key={cao.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-xl flex items-center gap-3">
                          {cao.name}
                          <Badge variant={getMatchBadgeColor(cao.match_score)}>
                            {Math.round(cao.match_score)}% match
                          </Badge>
                        </CardTitle>
                        <CardDescription className="mt-2">
                          <div className="flex items-center gap-4 flex-wrap">
                            <span className="flex items-center gap-1">
                              <Briefcase className="h-3 w-3" />
                              {cao.sector}
                            </span>
                            {cao.company && (
                              <span className="flex items-center gap-1">
                                <Building2 className="h-3 w-3" />
                                {cao.company}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {formatDate(cao.effective_from)} - {formatDate(cao.effective_to)}
                            </span>
                          </div>
                        </CardDescription>
                      </div>
                      {isCAOExpiringSoon(cao.effective_to) && (
                        <Badge variant="destructive" className="ml-3">
                          <AlertCircle className="mr-1 h-3 w-3" />
                          Expiring Soon
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                      <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Compliance Score</p>
                        <div className="flex items-center gap-2">
                          <span className="text-2xl font-bold">{cao.coverage_score}%</span>
                          <Badge variant={getComplianceBadgeColor(cao.coverage_score)}>
                            SETU v2.0
                          </Badge>
                        </div>
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Documents</p>
                        <div className="flex items-center gap-2">
                          <FileText className="h-5 w-5" />
                          <span className="text-lg font-semibold">{cao.document_count} processed</span>
                        </div>
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Salary Scales</p>
                        <div className="flex items-center gap-2">
                          {cao.has_salary_scales ? (
                            <>
                              <CheckCircle className="h-5 w-5 text-green-500" />
                              <span className="text-lg font-semibold">Available</span>
                            </>
                          ) : (
                            <>
                              <Clock className="h-5 w-5 text-yellow-500" />
                              <span className="text-lg font-semibold">Processing</span>
                            </>
                          )}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">Match Type</p>
                        <Badge variant="outline" className="text-base">
                          {cao.match_type.replace("_", " ")}
                        </Badge>
                      </div>
                    </div>

                    <div className="flex gap-3 mt-6">
                      <Button>
                        <BookOpen className="mr-2 h-4 w-4" />
                        View Details
                      </Button>
                      <Button variant="outline">
                        <Euro className="mr-2 h-4 w-4" />
                        Salary Scales
                      </Button>
                      <Button variant="outline">
                        <Calculator className="mr-2 h-4 w-4" />
                        Calculate Compensation
                      </Button>
                      <Button variant="outline">
                        <Shield className="mr-2 h-4 w-4" />
                        Check Compliance
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </>
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <AlertCircle className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No CAOs Found</h3>
                <p className="text-muted-foreground mb-4">
                  We couldn't find any CAOs matching your search criteria.
                </p>
                {suggestions.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Suggestions:</p>
                    {suggestions.map((suggestion, idx) => (
                      <p key={idx} className="text-sm text-muted-foreground">
                        • {suggestion}
                      </p>
                    ))}
                  </div>
                )}
                <Button className="mt-4" onClick={() => {
                  setSearchQuery("");
                  setHasSearched(false);
                }}>
                  Try Another Search
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Help Section */}
      {!hasSearched && (
        <Card>
          <CardHeader>
            <CardTitle>Need Help Finding Your CAO?</CardTitle>
            <CardDescription>
              Here are some tips to find the right collective agreement
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <h4 className="font-medium flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Search by Company
              </h4>
              <p className="text-sm text-muted-foreground">
                If your client has a company-specific CAO, search by their exact company name.
                This gives the most accurate results.
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium flex items-center gap-2">
                <Briefcase className="h-4 w-4" />
                Search by Sector
              </h4>
              <p className="text-sm text-muted-foreground">
                For sector-wide agreements, search by industry terms like "Metalektro",
                "Zorg", or "Transport".
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium flex items-center gap-2">
                <Hash className="h-4 w-4" />
                Search by KVK
              </h4>
              <p className="text-sm text-muted-foreground">
                The Chamber of Commerce number provides the most precise match,
                linking directly to the registered company.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}