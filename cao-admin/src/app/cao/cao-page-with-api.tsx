"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
  RefreshCw,
} from "lucide-react";

export default function CAOPageWithAPI() {
  const [caos, setCAOs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCAO, setSelectedCAO] = useState(null);

  // Fetch CAOs from API
  useEffect(() => {
    fetchCAOs();
  }, []);

  const fetchCAOs = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/api/v1/caos");
      const data = await response.json();
      setCAOs(data.data || []);
    } catch (error) {
      console.error("Error fetching CAOs:", error);
    } finally {
      setLoading(false);
    }
  };

  // Export CAO as JSON
  const exportCAO = async (caoId, caoName) => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/caos/${caoId}`);
      const data = await response.json();

      // Create downloadable JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${caoName || caoId}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error exporting CAO:", error);
    }
  };

  // Filter CAOs based on search
  const filteredCAOs = caos.filter(cao =>
    cao.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    cao.company?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    cao.sector?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusBadge = (status) => {
    const variants = {
      complete: "default",
      processing: "secondary",
      requires_review: "destructive",
      extracting: "outline",
    };
    return <Badge variant={variants[status] || "default"}>{status}</Badge>;
  };

  const getComplianceBadge = (compliance) => {
    const variants = {
      compliant: "default",
      partial: "outline",
      unknown: "secondary",
    };
    return <Badge variant={variants[compliance] || "secondary"}>{compliance}</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">CAO Library</h1>
          <p className="text-muted-foreground">
            {loading ? "Loading..." : `${filteredCAOs.length} CAO documents available`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchCAOs}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            Upload CAO
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search CAOs, companies, sectors..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* CAO Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>CAO Name</TableHead>
              <TableHead>Company/Sector</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Compliance</TableHead>
              <TableHead>Effective Date</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredCAOs.map((cao) => (
              <TableRow key={cao.id}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    {cao.name}
                  </div>
                </TableCell>
                <TableCell>{cao.company || cao.sector || "-"}</TableCell>
                <TableCell>{getStatusBadge(cao.status)}</TableCell>
                <TableCell>{getComplianceBadge(cao.compliance_status)}</TableCell>
                <TableCell>{cao.effective_date || "-"}</TableCell>
                <TableCell>
                  {cao.confidence ? `${Math.round(cao.confidence)}%` : "-"}
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => window.open(`http://localhost:8000/api/v1/caos/${cao.id}`, '_blank')}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View JSON in Browser
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => exportCAO(cao.id, cao.name)}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Export as JSON
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>How to Export CAO Data</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>• Click the menu (⋯) next to any CAO and select "Export as JSON" to download</p>
          <p>• Select "View JSON in Browser" to see the data in a new tab</p>
          <p>• API Endpoint: <code className="bg-muted px-1 rounded">http://localhost:8000/api/v1/caos/[cao-id]</code></p>
          <p>• Files are also available in: <code className="bg-muted px-1 rounded">data/setu/*.json</code></p>
        </CardContent>
      </Card>
    </div>
  );
}