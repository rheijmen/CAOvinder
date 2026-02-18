"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FileText,
  CheckCircle,
  GitBranch,
  BarChart3,
  Settings,
  Users,
  Building,
  HelpCircle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";

interface NavItem {
  title: string;
  href?: string;
  icon: React.ElementType;
  children?: NavItem[];
  badge?: string;
  badgeVariant?: "default" | "secondary" | "destructive" | "outline";
}

const navigation: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "CAO Library",
    icon: FileText,
    children: [
      { title: "Browse", href: "/cao", icon: FileText },
      { title: "Upload", href: "/cao/upload", icon: FileText },
      { title: "Versions", href: "/cao/versions", icon: FileText },
    ],
  },
  {
    title: "Processing",
    icon: GitBranch,
    badge: "3",
    badgeVariant: "secondary",
    children: [
      { title: "Pipeline", href: "/pipeline", icon: GitBranch },
      { title: "Jobs", href: "/pipeline/jobs", icon: GitBranch },
      { title: "Queue", href: "/pipeline/queue", icon: GitBranch },
    ],
  },
  {
    title: "Compliance",
    href: "/compliance",
    icon: CheckCircle,
    badge: "12",
    badgeVariant: "destructive",
  },
  {
    title: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
  {
    title: "Organization",
    icon: Building,
    children: [
      { title: "Teams", href: "/org/teams", icon: Users },
      { title: "Settings", href: "/org/settings", icon: Settings },
      { title: "Billing", href: "/org/billing", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [expandedItems, setExpandedItems] = useState<string[]>([]);

  const toggleExpanded = (title: string) => {
    setExpandedItems((prev) =>
      prev.includes(title)
        ? prev.filter((item) => item !== title)
        : [...prev, title]
    );
  };

  const renderNavItem = (item: NavItem, level = 0) => {
    const isExpanded = expandedItems.includes(item.title);
    const hasChildren = item.children && item.children.length > 0;
    const Icon = item.icon;

    if (hasChildren) {
      return (
        <div key={item.title} className="space-y-1">
          <button
            onClick={() => toggleExpanded(item.title)}
            className={cn(
              "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
              level > 0 && "ml-4"
            )}
          >
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4" />
              <span>{item.title}</span>
              {item.badge && (
                <Badge
                  variant={item.badgeVariant || "default"}
                  className="ml-auto h-5 px-1.5 text-xs"
                >
                  {item.badge}
                </Badge>
              )}
            </div>
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
          {isExpanded && (
            <div className="ml-4 space-y-1">
              {item.children.map((child) => renderNavItem(child, level + 1))}
            </div>
          )}
        </div>
      );
    }

    return (
      <Link
        key={item.title}
        href={item.href || "#"}
        className={cn(
          "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
          pathname === item.href && "bg-accent",
          level > 0 && "ml-4"
        )}
      >
        <Icon className="h-4 w-4" />
        <span>{item.title}</span>
        {item.badge && (
          <Badge
            variant={item.badgeVariant || "default"}
            className="ml-auto h-5 px-1.5 text-xs"
          >
            {item.badge}
          </Badge>
        )}
      </Link>
    );
  };

  return (
    <div className="flex h-full w-64 flex-col border-r bg-background">
      {/* Logo/Brand */}
      <div className="flex h-16 items-center border-b px-6">
        <h2 className="text-lg font-bold">CAO Intelligence</h2>
        <Badge variant="outline" className="ml-2">
          v2.0
        </Badge>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-4">
        {navigation.map((item) => renderNavItem(item))}
      </nav>

      {/* Help Section */}
      <div className="border-t p-4">
        <Link
          href="/help"
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <HelpCircle className="h-4 w-4" />
          <span>Help & Documentation</span>
        </Link>
      </div>

      {/* Organization Selector */}
      <div className="border-t p-4">
        <div className="rounded-lg bg-muted px-3 py-2">
          <p className="text-xs font-medium text-muted-foreground">
            Organization
          </p>
          <p className="text-sm font-semibold">Acme Corporation</p>
          <p className="text-xs text-muted-foreground">Enterprise Plan</p>
        </div>
      </div>
    </div>
  );
}