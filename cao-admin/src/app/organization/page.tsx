"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Building2,
  Users,
  Key,
  Globe,
  Shield,
  Mail,
  Phone,
  MapPin,
  CreditCard,
  Settings,
  Plus,
  Copy,
  Eye,
  EyeOff,
  Trash2,
  Edit,
  Check,
  X,
  ExternalLink,
  AlertCircle,
  Zap,
} from "lucide-react";

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive';
  lastActive: string;
}

interface ApiKey {
  id: string;
  name: string;
  key: string;
  created: string;
  lastUsed: string;
  status: 'active' | 'revoked';
}

export default function OrganizationPage() {
  const [showApiKey, setShowApiKey] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);

  const mockUsers: User[] = [
    {
      id: '1',
      name: 'Admin User',
      email: 'admin@example.com',
      role: 'Administrator',
      status: 'active',
      lastActive: '2 hours ago'
    },
    {
      id: '2',
      name: 'John Doe',
      email: 'john@example.com',
      role: 'Analyst',
      status: 'active',
      lastActive: '1 day ago'
    }
  ];

  const mockApiKeys: ApiKey[] = [
    {
      id: '1',
      name: 'Production API',
      key: 'sk_live_4242424242424242',
      created: '2024-01-15',
      lastUsed: '2 hours ago',
      status: 'active'
    },
    {
      id: '2',
      name: 'Development API',
      key: 'sk_test_1234567890123456',
      created: '2024-02-01',
      lastUsed: '1 week ago',
      status: 'active'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Organization Settings</h1>
          <p className="text-muted-foreground">
            Manage your organization, users, and integrations
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        {/* General Tab */}
        <TabsContent value="general" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Organization Information</CardTitle>
              <CardDescription>
                Basic information about your organization
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="org-name">Organization Name</Label>
                  <Input
                    id="org-name"
                    defaultValue="Acme Corporation"
                    disabled={!editMode}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="org-id">Organization ID</Label>
                  <Input
                    id="org-id"
                    value="org_2hFkL3mQpK"
                    disabled
                    className="font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Contact Email</Label>
                  <Input
                    id="email"
                    type="email"
                    defaultValue="contact@acme.com"
                    disabled={!editMode}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number</Label>
                  <Input
                    id="phone"
                    defaultValue="+31 20 123 4567"
                    disabled={!editMode}
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="address">Address</Label>
                  <Input
                    id="address"
                    defaultValue="Herengracht 100, 1015 BS Amsterdam, Netherlands"
                    disabled={!editMode}
                  />
                </div>
              </div>

              <div className="flex justify-between items-center pt-4">
                <div className="flex items-center gap-4">
                  <Badge variant="default">Enterprise Plan</Badge>
                  <span className="text-sm text-muted-foreground">
                    Member since January 2024
                  </span>
                </div>
                <Button
                  onClick={() => setEditMode(!editMode)}
                  variant={editMode ? "default" : "outline"}
                >
                  {editMode ? (
                    <>
                      <Check className="mr-2 h-4 w-4" /> Save Changes
                    </>
                  ) : (
                    <>
                      <Edit className="mr-2 h-4 w-4" /> Edit
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Preferences</CardTitle>
              <CardDescription>
                Configure organization-wide preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-process new CAOs</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically start processing when new CAOs are uploaded
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Email notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive email alerts for important events
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Compliance monitoring</Label>
                  <p className="text-sm text-muted-foreground">
                    Enable automatic compliance checking for all CAOs
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Users</CardTitle>
                <CardDescription>
                  Manage users and their permissions
                </CardDescription>
              </div>
              <Button>
                <Plus className="mr-2 h-4 w-4" /> Invite User
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockUsers.map((user) => (
                  <div key={user.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <Users className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{user.name}</p>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                      </div>
                      <Badge variant={user.status === 'active' ? 'default' : 'secondary'}>
                        {user.status}
                      </Badge>
                      <Badge variant="outline">{user.role}</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        Active {user.lastActive}
                      </span>
                      <Button variant="ghost" size="icon">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api-keys" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>API Keys</CardTitle>
                <CardDescription>
                  Manage API keys for programmatic access
                </CardDescription>
              </div>
              <Button>
                <Plus className="mr-2 h-4 w-4" /> Create API Key
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockApiKeys.map((apiKey) => (
                  <div key={apiKey.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <Key className="h-5 w-5 text-primary" />
                      </div>
                      <div className="space-y-1">
                        <p className="font-medium">{apiKey.name}</p>
                        <div className="flex items-center gap-2">
                          <code className="text-sm bg-muted px-2 py-1 rounded">
                            {showApiKey === apiKey.id ? apiKey.key : '••••••••••••••••'}
                          </code>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => setShowApiKey(showApiKey === apiKey.id ? null : apiKey.id)}
                          >
                            {showApiKey === apiKey.id ? (
                              <EyeOff className="h-3 w-3" />
                            ) : (
                              <Eye className="h-3 w-3" />
                            )}
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      <Badge variant={apiKey.status === 'active' ? 'default' : 'destructive'}>
                        {apiKey.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-right">
                        <p className="text-sm text-muted-foreground">
                          Created {apiKey.created}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Last used {apiKey.lastUsed}
                        </p>
                      </div>
                      <Button variant="ghost" size="icon">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Integrations Tab */}
        <TabsContent value="integrations" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                      <Globe className="h-5 w-5 text-blue-500" />
                    </div>
                    <div>
                      <CardTitle className="text-base">Webhook Integration</CardTitle>
                      <CardDescription className="text-sm">
                        Receive real-time notifications
                      </CardDescription>
                    </div>
                  </div>
                  <Switch />
                </div>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Configure Webhooks
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                      <Zap className="h-5 w-5 text-green-500" />
                    </div>
                    <div>
                      <CardTitle className="text-base">Slack Integration</CardTitle>
                      <CardDescription className="text-sm">
                        Get notifications in Slack
                      </CardDescription>
                    </div>
                  </div>
                  <Badge variant="outline">Coming Soon</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full" disabled>
                  Connect Slack
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                      <Shield className="h-5 w-5 text-purple-500" />
                    </div>
                    <div>
                      <CardTitle className="text-base">SSO Integration</CardTitle>
                      <CardDescription className="text-sm">
                        Single sign-on with SAML 2.0
                      </CardDescription>
                    </div>
                  </div>
                  <Switch defaultChecked />
                </div>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Configure SSO
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                      <ExternalLink className="h-5 w-5 text-orange-500" />
                    </div>
                    <div>
                      <CardTitle className="text-base">Export Integration</CardTitle>
                      <CardDescription className="text-sm">
                        Automated data export
                      </CardDescription>
                    </div>
                  </div>
                  <Switch />
                </div>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Setup Export
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Billing Tab */}
        <TabsContent value="billing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Current Plan</CardTitle>
              <CardDescription>
                You are currently on the Enterprise plan
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                    <CreditCard className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold">Enterprise Plan</p>
                    <p className="text-sm text-muted-foreground">
                      Unlimited CAOs, priority support, custom integrations
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold">€999</p>
                  <p className="text-sm text-muted-foreground">per month</p>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <p className="text-sm font-medium">CAOs Processed</p>
                  <p className="text-2xl font-bold">47 / ∞</p>
                  <p className="text-xs text-muted-foreground">This month</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium">API Calls</p>
                  <p className="text-2xl font-bold">12.4K / ∞</p>
                  <p className="text-xs text-muted-foreground">This month</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium">Storage Used</p>
                  <p className="text-2xl font-bold">2.3 GB</p>
                  <p className="text-xs text-muted-foreground">Of unlimited</p>
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="outline">View Invoice History</Button>
                <Button variant="outline">Update Payment Method</Button>
                <Button variant="outline">Change Plan</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}