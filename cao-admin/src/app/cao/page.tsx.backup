"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Search,
  Filter,
  Upload,
  Download,
  MoreHorizontal,
  FileText,
  Eye,
  Edit,
  Trash2,
  Copy,
  GitBranch,
  RefreshCw,
  Grid3x3,
  List,
  ChevronDown,
} from "lucide-react";
import { CAODocument, FilterState } from "@/types";
import { formatDate, formatFileSize } from "@/lib/format-utils";

// Mock data
const mockCAOs: CAODocument[] = [
  {
    id: "1",
    organizationId: "org1",
    name: "CAO Metalektro 2024",
    sector: "Metaal & Techniek",
    company: "FME",
    version: 1,
    status: "complete",
    effectiveDate: new Date("2024-01-01"),
    expiryDate: new Date("2025-12-31"),
    originalFileName: "cao_metalektro_2024.pdf",
    fileSize: 2457600,
    uploadedAt: new Date("2024-02-01"),
    uploadedBy: "admin@example.com",
    processedAt: new Date("2024-02-01"),
    complianceStatus: "compliant",
    metadata: {
      pageCount: 127,
      language: "nl",
      confidence: 98.5,
    },
  },
  {
    id: "2",
    organizationId: "org1",
    name: "CAO Bouw & Infra",
    sector: "Bouw",
    company: "Bouwend Nederland",
    version: 2,
    status: "requires_review",
    effectiveDate: new Date("2023-07-01"),
    originalFileName: "cao_bouw_2023.pdf",
    fileSize: 3145728,
    uploadedAt: new Date("2024-02-10"),
    uploadedBy: "user@example.com",
    complianceStatus: "partial",
    discrepancies: [
      {
        id: "d1",
        caoDocumentId: "2",
        fieldPath: "loongebouw.schalen",
        type: "missing",
        currentValue: null,
        status: "open",
        priority: "high",
      },
    ],
    metadata: {
      pageCount: 156,
      language: "nl",
      confidence: 76.2,
    },
  },
  {
    id: "3",
    organizationId: "org1",
    name: "CAO Transport",
    sector: "Transport & Logistiek",
    company: "TLN",
    version: 1,
    status: "extracting",
    effectiveDate: new Date("2024-03-01"),
    originalFileName: "cao_transport_2024.pdf",
    fileSize: 1987654,
    uploadedAt: new Date("2024-02-18"),
    uploadedBy: "admin@example.com",
    complianceStatus: "unknown",
    metadata: {
      pageCount: 98,
      language: "nl",
    },
  },
];

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    complete: "text-green-600",
    extracting: "text-blue-600",
    requires_review: "text-orange-600",
    failed: "text-red-600",
  };
  return colors[status] || "text-gray-600";
};

// formatFileSize is now imported from lib/format-utils

export default function CAOLibraryPage() {
  const [viewMode, setViewMode] = useState<"grid" | "list">("list");
  const [selectedCAOs, setSelectedCAOs] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<FilterState>({
    sector: [],
    status: [],
    complianceStatus: [],
  });

  const toggleCAOSelection = (id: string) => {
    setSelectedCAOs((prev) =>
      prev.includes(id)
        ? prev.filter((caoId) => caoId !== id)
        : [...prev, id]
    );
  };

  const selectAllCAOs = () => {
    if (selectedCAOs.length === mockCAOs.length) {
      setSelectedCAOs([]);
    } else {
      setSelectedCAOs(mockCAOs.map((cao) => cao.id));
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">CAO Library</h1>
          <p className="text-muted-foreground">
            Manage and search your CAO documents
          </p>
        </div>
        <Button className="gap-2">
          <Upload className="h-4 w-4" />
          Upload CAO
        </Button>
      </div>

      {/* Search and Filters Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-1 gap-2">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search CAOs, companies, sectors..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Sector" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sectors</SelectItem>
                  <SelectItem value="metaal">Metaal & Techniek</SelectItem>
                  <SelectItem value="bouw">Bouw</SelectItem>
                  <SelectItem value="transport">Transport</SelectItem>
                </SelectContent>
              </Select>
              <Select>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="complete">Complete</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="review">Needs Review</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline">
                <Filter className="mr-2 h-4 w-4" />
                Filter
              </Button>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setViewMode("list")}
                className={viewMode === "list" ? "bg-muted" : ""}
              >
                <List className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setViewMode("grid")}
                className={viewMode === "grid" ? "bg-muted" : ""}
              >
                <Grid3x3 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions Bar */}
      {selectedCAOs.length > 0 && (
        <Card className="border-primary">
          <CardContent className="flex items-center justify-between p-3">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">Bulk Actions:</span>
              <Badge>{selectedCAOs.length} selected</Badge>
              <Button variant="outline" size="sm">
                <RefreshCw className="mr-2 h-4 w-4" />
                Reprocess
              </Button>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
              <Button variant="outline" size="sm">
                <GitBranch className="mr-2 h-4 w-4" />
                Compare
              </Button>
              <Button variant="outline" size="sm" className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Archive
              </Button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedCAOs([])}
            >
              Clear selection
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Helper text for bulk operations - always visible */}
      <div className="text-sm text-muted-foreground">
        {selectedCAOs.length === 0
          ? "Select CAOs to perform Bulk operations"
          : `${selectedCAOs.length} items selected for Bulk operations`}
      </div>

      {/* CAO List/Grid View */}
      {viewMode === "list" ? (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <input
                      type="checkbox"
                      checked={selectedCAOs.length === mockCAOs.length}
                      onChange={selectAllCAOs}
                      className="h-4 w-4"
                    />
                  </TableHead>
                  <TableHead>CAO Name</TableHead>
                  <TableHead>Sector</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Compliance</TableHead>
                  <TableHead>Effective Date</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockCAOs.map((cao) => (
                  <TableRow key={cao.id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={selectedCAOs.includes(cao.id)}
                        onChange={() => toggleCAOSelection(cao.id)}
                        className="h-4 w-4"
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="font-medium">{cao.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {cao.company} • v{cao.version}
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{cao.sector}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={getStatusColor(cao.status)}
                      >
                        {cao.status.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            cao.complianceStatus === "compliant"
                              ? "default"
                              : cao.complianceStatus === "partial"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {cao.complianceStatus}
                        </Badge>
                        {cao.discrepancies && cao.discrepancies.length > 0 && (
                          <span className="text-xs text-destructive">
                            {cao.discrepancies.length} issues
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {formatDate(cao.effectiveDate)}
                    </TableCell>
                    <TableCell>{formatFileSize(cao.fileSize)}</TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>
                            <Eye className="mr-2 h-4 w-4" />
                            View Details
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Edit className="mr-2 h-4 w-4" />
                            Edit Metadata
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Reprocess
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Copy className="mr-2 h-4 w-4" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Download className="mr-2 h-4 w-4" />
                            Download
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-destructive">
                            <Trash2 className="mr-2 h-4 w-4" />
                            Archive
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {mockCAOs.map((cao) => (
            <Card key={cao.id} className="relative">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <FileText className="h-8 w-8 text-muted-foreground" />
                  <input
                    type="checkbox"
                    checked={selectedCAOs.includes(cao.id)}
                    onChange={() => toggleCAOSelection(cao.id)}
                    className="h-4 w-4"
                  />
                </div>
                <CardTitle className="text-lg">{cao.name}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {cao.company} • {cao.sector}
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Status</span>
                    <Badge
                      variant="outline"
                      className={getStatusColor(cao.status)}
                    >
                      {cao.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Compliance</span>
                    <Badge
                      variant={
                        cao.complianceStatus === "compliant"
                          ? "default"
                          : "outline"
                      }
                    >
                      {cao.complianceStatus}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Effective</span>
                    <span className="text-sm text-muted-foreground">
                      {formatDate(cao.effectiveDate)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Size</span>
                    <span className="text-sm text-muted-foreground">
                      {formatFileSize(cao.fileSize)}
                    </span>
                  </div>
                </div>
                <div className="mt-4 flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1">
                    <Eye className="mr-2 h-4 w-4" />
                    View
                  </Button>
                  <Button variant="outline" size="sm" className="flex-1">
                    <Edit className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}