"use client"

import { useState } from "react"
import { FileText, Zap, CheckCircle2, TrendingUp, Database, AlertCircle, BarChart3, Layers, Activity, Copy, AlertTriangle, XCircle, Clock, FileX, Link2, RefreshCw, ExternalLink, Calendar, Globe, FileCheck, LayoutDashboard } from "lucide-react"
import MetricCard from "@/components/metric-card"

interface Issue {
  id: string
  type: "failed_url" | "corrupted_pdf" | "timeout" | "404_change" | "parsing_failure" | "indexing_failure" | "synced_not_indexed"
  severity: "critical" | "warning" | "info"
  title: string
  description: string
  url?: string
  fileName?: string
  timestamp: string
  count?: number
}

export default function DashboardOverview() {
  // Tab state
  const [activeTab, setActiveTab] = useState<"overview" | "operations" | "freshness">("overview")
  
  // Mock Issues/Alerting Data
  const issues: Issue[] = [
    {
      id: "1",
      type: "failed_url",
      severity: "critical",
      title: "Failed URL: irs.gov/forms-pubs/about-form-w-2",
      description: "Download timeout: Connection to irs.gov timed out after 30 seconds",
      url: "https://www.irs.gov/forms-pubs/about-form-w-2",
      timestamp: "2024-11-20 14:30 UTC",
    },
    {
      id: "2",
      type: "corrupted_pdf",
      severity: "warning",
      title: "Corrupted PDF: State_Tax_Return_CA.pdf",
      description: "OCR validation failed: 3 pages could not be processed. Low image quality detected.",
      fileName: "State_Tax_Return_CA.pdf",
      timestamp: "2024-11-18 09:45 UTC",
    },
    {
      id: "3",
      type: "404_change",
      severity: "critical",
      title: "404 Error: irs.gov/pub/irs-prior/rr-2023-15.pdf",
      description: "URL changed or removed from IRS website. Original URL returns 404.",
      url: "https://www.irs.gov/pub/irs-prior/rr-2023-15.pdf",
      timestamp: "2024-11-19 11:20 UTC",
    },
    {
      id: "4",
      type: "parsing_failure",
      severity: "warning",
      title: "Parsing Failure: FAQ_Individual_Taxes.pdf",
      description: "HTML parsing failed: Invalid text encoding detected. File may be corrupted.",
      fileName: "FAQ_Individual_Taxes.pdf",
      timestamp: "2024-11-13 12:00 UTC",
    },
    {
      id: "5",
      type: "indexing_failure",
      severity: "critical",
      title: "Indexing Failure: FAQ_Individual_Taxes.pdf",
      description: "Embedding generation failed: Invalid text encoding detected. File may be corrupted.",
      fileName: "FAQ_Individual_Taxes.pdf",
      timestamp: "2024-11-13 12:05 UTC",
    },
    {
      id: "6",
      type: "synced_not_indexed",
      severity: "warning",
      title: "Synced but Not Indexed: W2_Forms_2024.pdf",
      description: "File downloaded successfully but indexing failed. File is not searchable.",
      fileName: "W2_Forms_2024.pdf",
      timestamp: "2024-11-17 10:15 UTC",
    },
    {
      id: "7",
      type: "timeout",
      severity: "warning",
      title: "Timeout Error: irs.gov/forms-pubs/about-form-1040-es",
      description: "Request timeout after 30 seconds. Network connectivity issue.",
      url: "https://www.irs.gov/forms-pubs/about-form-1040-es",
      timestamp: "2024-11-16 11:20 UTC",
    },
  ]

  // Group issues by type for summary
  const issuesSummary = {
    failedUrls: issues.filter((i) => i.type === "failed_url").length,
    corruptedPDFs: issues.filter((i) => i.type === "corrupted_pdf").length,
    timeoutErrors: issues.filter((i) => i.type === "timeout").length,
    url404Changes: issues.filter((i) => i.type === "404_change").length,
    parsingFailures: issues.filter((i) => i.type === "parsing_failure").length,
    indexingFailures: issues.filter((i) => i.type === "indexing_failure").length,
    syncedNotIndexed: issues.filter((i) => i.type === "synced_not_indexed").length,
    total: issues.length,
  }

  const getIssueIcon = (type: Issue["type"]) => {
    switch (type) {
      case "failed_url":
      case "404_change":
        return <Link2 size={16} />
      case "corrupted_pdf":
        return <FileX size={16} />
      case "timeout":
        return <Clock size={16} />
      case "parsing_failure":
      case "indexing_failure":
        return <XCircle size={16} />
      case "synced_not_indexed":
        return <RefreshCw size={16} />
      default:
        return <AlertCircle size={16} />
    }
  }

  const getSeverityColor = (severity: Issue["severity"]) => {
    switch (severity) {
      case "critical":
        return "bg-destructive/10 border-destructive/30 text-destructive"
      case "warning":
        return "bg-yellow-500/10 border-yellow-500/30 text-yellow-600"
      case "info":
        return "bg-blue-500/10 border-blue-500/30 text-blue-600"
      default:
        return "bg-muted/50 border-border text-muted-foreground"
    }
  }

  // Mock Freshness Metrics Data
  const freshnessMetrics = {
    docsStaleOver30Days: 27,
    urlsChangedThisWeek: 4,
    newIrsReleasesToday: 2,
    docsStaleOver1Year: 8,
    docsStaleOver2Years: 3,
    stateGuidanceUpdated: 2,
    faqPagesUpdated: 1,
  }

  // Mock Freshness Details
  const staleDocuments = [
    {
      id: "1",
      name: "Form_1040_2023.pdf",
      lastCrawled: "2023-10-15",
      daysStale: 402,
      sourceUrl: "https://www.irs.gov/forms-pubs/about-form-1040",
      hasNewerVersion: true,
    },
    {
      id: "2",
      name: "Tax_Code_Title_26_2022.pdf",
      lastCrawled: "2022-11-20",
      daysStale: 730,
      sourceUrl: "https://uscode.house.gov/view.xhtml?path=/prelim@title26",
      hasNewerVersion: true,
    },
    {
      id: "3",
      name: "IRS_Publication_535_2022.pdf",
      lastCrawled: "2022-12-01",
      daysStale: 720,
      sourceUrl: "https://www.irs.gov/publications/p535",
      hasNewerVersion: true,
    },
  ]

  const urlChanges = [
    {
      id: "1",
      url: "https://www.irs.gov/forms-pubs/about-form-1040",
      changeType: "format_change",
      description: "URL changed from HTML to PDF format",
      detectedDate: "2024-11-18",
    },
    {
      id: "2",
      url: "https://www.irs.gov/faqs/individual-income-tax",
      changeType: "content_update",
      description: "FAQ page content updated",
      detectedDate: "2024-11-19",
    },
    {
      id: "3",
      url: "https://www.tax.ca.gov/forms-publications",
      changeType: "structure_change",
      description: "Page structure changed, new navigation",
      detectedDate: "2024-11-20",
    },
    {
      id: "4",
      url: "https://www.irs.gov/pub/irs-drop/rr-24-01.pdf",
      changeType: "version_update",
      description: "New version detected: rr-24-02.pdf",
      detectedDate: "2024-11-20",
    },
  ]

  const newIrsReleases = [
    {
      id: "1",
      title: "Form 1040 Instructions 2025",
      releaseDate: "2024-11-20",
      url: "https://www.irs.gov/forms-pubs/about-form-1040",
      type: "form",
    },
    {
      id: "2",
      title: "Revenue Ruling 2024-25",
      releaseDate: "2024-11-20",
      url: "https://www.irs.gov/pub/irs-drop/rr-24-25.pdf",
      type: "ruling",
    },
  ]

  // Mock RAG Health Metrics Data
  const ragMetrics = {
    documentsIndexed: 1247,
    chunksCreated: 384256,
    embeddingSuccessRate: 98.7,
    averageChunkSize: 512,
    errorsLast24h: 12,
    duplicateDetection: 47,
    authorityTierBreakdown: {
      level1: 142,
      level2: 523,
      level3: 198,
      level4: 287,
      level5: 67,
      level6: 30,
    },
    chunkSizeDistribution: {
      small: 45, // < 256 tokens
      medium: 35, // 256-512 tokens
      large: 15, // 512-1024 tokens
      xlarge: 5, // > 1024 tokens
    },
  }

  const metrics: Array<{
    label: string
    value: string
    change: string
    icon: React.ReactNode
    trend: "up" | "down"
  }> = [
    {
      label: "Documents Processed",
      value: "1,247",
      change: "+12.5%",
      icon: <FileText size={24} />,
      trend: "up",
    },
    {
      label: "Active URLs",
      value: "142",
      change: "+8.2%",
      icon: <Zap size={24} />,
      trend: "up",
    },
    {
      label: "System Uptime",
      value: "99.94%",
      change: "+0.02%",
      icon: <CheckCircle2 size={24} />,
      trend: "up",
    },
    {
      label: "Processing Speed",
      value: "2.4s",
      change: "-15.3%",
      icon: <TrendingUp size={24} />,
      trend: "down",
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header with Integration Badge */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Dashboard</h1>
          <p className="text-muted-foreground">Real-time overview of your tax document system</p>
        </div>
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent/10 border border-accent/20">
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse-glow" />
          <span className="text-sm font-semibold text-accent">Integrated with EL RAG</span>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-border">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-3 text-sm font-medium transition-colors flex items-center gap-2 border-b-2 -mb-px ${
              activeTab === "overview"
                ? "border-accent text-accent"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`}
          >
            <LayoutDashboard size={18} />
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab("operations")}
            className={`px-4 py-3 text-sm font-medium transition-colors flex items-center gap-2 border-b-2 -mb-px ${
              activeTab === "operations"
                ? "border-accent text-accent"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`}
          >
            <AlertTriangle size={18} />
            Alerts & Issues
          </button>
          <button
            onClick={() => setActiveTab("freshness")}
            className={`px-4 py-3 text-sm font-medium transition-colors flex items-center gap-2 border-b-2 -mb-px ${
              activeTab === "freshness"
                ? "border-accent text-accent"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            }`}
          >
            <Calendar size={18} />
            Document Freshness
          </button>
        </div>
      </div>

      {/* Dashboard Tab Content */}
      {activeTab === "overview" && (
        <div className="space-y-8">
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {metrics.map((metric, idx) => (
              <MetricCard key={idx} {...metric} />
            ))}
          </div>

          {/* Main Content Grid - System Scalability section with progress bars */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* System Scalability */}
        <div className="lg:col-span-2 p-6 rounded-lg bg-card border border-border">
          <h2 className="text-xl font-bold text-foreground mb-6">System Scalability</h2>
          <div className="space-y-6">
            {/* Document Processing Capacity */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-foreground font-medium">Document Processing Capacity</span>
                <span className="text-accent font-semibold">87%</span>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-accent" style={{ width: "87%" }} />
              </div>
            </div>

            {/* Storage Utilization */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-foreground font-medium">Storage Utilization</span>
                <span className="text-accent font-semibold">64%</span>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-accent" style={{ width: "64%" }} />
              </div>
            </div>

            {/* API Request Quota */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-foreground font-medium">API Request Quota</span>
                <span className="text-accent font-semibold">42%</span>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-accent" style={{ width: "42%" }} />
              </div>
            </div>
          </div>
        </div>

        {/* Quick Stats - Expanded with more statistics */}
        <div className="p-6 rounded-lg bg-card border border-border">
          <h2 className="text-xl font-bold text-foreground mb-6">Quick Stats</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Total URLs</span>
              <span className="text-lg font-bold text-foreground">142</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Last 24h Updates</span>
              <span className="text-lg font-bold text-foreground">287</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Total Users</span>
              <span className="text-lg font-bold text-foreground">12</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">API Health</span>
              <span className="text-sm font-bold text-accent">✓ Good</span>
            </div>
          </div>
        </div>
      </div>

      {/* RAG Health Metrics Section */}
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-foreground mb-2">RAG Health Metrics</h2>
          <p className="text-muted-foreground">Real-time monitoring of RAG pipeline quality and performance</p>
        </div>

        {/* Primary RAG Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="p-6 rounded-lg bg-card border border-border">
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-500">
                <Database size={24} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Documents Indexed</p>
            <p className="text-3xl font-bold text-foreground">{ragMetrics.documentsIndexed.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground mt-2">Total documents in vector DB</p>
          </div>

          <div className="p-6 rounded-lg bg-card border border-border">
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center text-green-500">
                <Layers size={24} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Chunks Created</p>
            <p className="text-3xl font-bold text-foreground">{ragMetrics.chunksCreated.toLocaleString()}</p>
            <p className="text-xs text-muted-foreground mt-2">Total text chunks embedded</p>
          </div>

          <div className="p-6 rounded-lg bg-card border border-border">
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-500">
                <CheckCircle2 size={24} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Embedding Success Rate</p>
            <p className="text-3xl font-bold text-foreground">{ragMetrics.embeddingSuccessRate}%</p>
            <p className="text-xs text-muted-foreground mt-2">Successfully embedded documents</p>
          </div>

          <div className="p-6 rounded-lg bg-card border border-border">
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-orange-500/20 flex items-center justify-center text-orange-500">
                <AlertCircle size={24} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Errors Last 24h</p>
            <p className="text-3xl font-bold text-foreground">{ragMetrics.errorsLast24h}</p>
            <p className="text-xs text-muted-foreground mt-2">Indexing/embedding failures</p>
          </div>
        </div>

        {/* Detailed RAG Metrics Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Average Chunk Size Distribution */}
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <BarChart3 size={20} className="text-accent" />
              Average Chunk Size Distribution
            </h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-foreground font-medium">Average Chunk Size</span>
                  <span className="text-accent font-semibold">{ragMetrics.averageChunkSize} tokens</span>
                </div>
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-accent" style={{ width: "75%" }} />
                </div>
              </div>
              <div className="space-y-3 pt-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">Small (&lt; 256 tokens)</span>
                  <span className="text-sm font-semibold text-foreground">{ragMetrics.chunkSizeDistribution.small}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">Medium (256-512 tokens)</span>
                  <span className="text-sm font-semibold text-foreground">{ragMetrics.chunkSizeDistribution.medium}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">Large (512-1024 tokens)</span>
                  <span className="text-sm font-semibold text-foreground">{ragMetrics.chunkSizeDistribution.large}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">X-Large (&gt; 1024 tokens)</span>
                  <span className="text-sm font-semibold text-foreground">{ragMetrics.chunkSizeDistribution.xlarge}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Duplicate Detection & Errors */}
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <Activity size={20} className="text-accent" />
              Quality Metrics
            </h3>
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-foreground font-medium flex items-center gap-2">
                    <Copy size={16} className="text-muted-foreground" />
                    Duplicate Detection
                  </span>
                  <span className="text-lg font-bold text-foreground">{ragMetrics.duplicateDetection}</span>
                </div>
                <p className="text-xs text-muted-foreground">Duplicate documents detected and prevented</p>
              </div>
              <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-foreground font-medium flex items-center gap-2">
                    <AlertCircle size={16} className="text-destructive" />
                    Errors Last 24h
                  </span>
                  <span className="text-lg font-bold text-destructive">{ragMetrics.errorsLast24h}</span>
                </div>
                <p className="text-xs text-muted-foreground">Indexing failures, OCR errors, embedding issues</p>
              </div>
            </div>
          </div>
        </div>

        {/* Authority Tier Breakdown */}
        <div className="p-6 rounded-lg bg-card border border-border">
          <h3 className="text-lg font-bold text-foreground mb-6 flex items-center gap-2">
            <BarChart3 size={20} className="text-accent" />
            Authority Tier Breakdown
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-xs font-semibold text-muted-foreground uppercase">Level 1</span>
              </div>
              <p className="text-2xl font-bold text-foreground">{ragMetrics.authorityTierBreakdown.level1}</p>
              <p className="text-xs text-muted-foreground mt-1">Statute/Reg</p>
            </div>
            <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="text-xs font-semibold text-muted-foreground uppercase">Level 2</span>
              </div>
              <p className="text-2xl font-bold text-foreground">{ragMetrics.authorityTierBreakdown.level2}</p>
              <p className="text-xs text-muted-foreground mt-1">Forms/Instructions</p>
            </div>
            <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                <span className="text-xs font-semibold text-muted-foreground uppercase">Level 3</span>
              </div>
              <p className="text-2xl font-bold text-foreground">{ragMetrics.authorityTierBreakdown.level3}</p>
              <p className="text-xs text-muted-foreground mt-1">Rulings/Procedures</p>
            </div>
            <div className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                <span className="text-xs font-semibold text-muted-foreground uppercase">Level 4</span>
              </div>
              <p className="text-2xl font-bold text-foreground">{ragMetrics.authorityTierBreakdown.level4}</p>
              <p className="text-xs text-muted-foreground mt-1">FAQs/Publications</p>
            </div>
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <span className="text-xs font-semibold text-muted-foreground uppercase">Level 5</span>
              </div>
              <p className="text-2xl font-bold text-foreground">{ragMetrics.authorityTierBreakdown.level5}</p>
              <p className="text-xs text-muted-foreground mt-1">Expert Sources</p>
            </div>
            <div className="p-4 rounded-lg bg-gray-500/10 border border-gray-500/20">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                <span className="text-xs font-semibold text-muted-foreground uppercase">Level 6</span>
              </div>
              <p className="text-2xl font-bold text-foreground">{ragMetrics.authorityTierBreakdown.level6}</p>
              <p className="text-xs text-muted-foreground mt-1">Other/Low Authority</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-border">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Total Documents by Authority Level</span>
              <span className="text-lg font-bold text-foreground">
                {Object.values(ragMetrics.authorityTierBreakdown).reduce((a, b) => a + b, 0).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>
      </div>
      )}

      {/* Operations Tab Content */}
      {activeTab === "operations" && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-2">Alerting & Issues</h2>
            <p className="text-muted-foreground">Monitor and resolve system issues, failures, and operational alerts</p>
          </div>

        {/* Issues Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Link2 size={16} className="text-destructive" />
              <span className="text-xs font-semibold text-muted-foreground">Failed URLs</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{issuesSummary.failedUrls}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <FileX size={16} className="text-yellow-600" />
              <span className="text-xs font-semibold text-muted-foreground">Corrupted PDFs</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{issuesSummary.corruptedPDFs}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Clock size={16} className="text-yellow-600" />
              <span className="text-xs font-semibold text-muted-foreground">Timeouts</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{issuesSummary.timeoutErrors}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <XCircle size={16} className="text-destructive" />
              <span className="text-xs font-semibold text-muted-foreground">404 Changes</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{issuesSummary.url404Changes}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <XCircle size={16} className="text-yellow-600" />
              <span className="text-xs font-semibold text-muted-foreground">Parsing Failures</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{issuesSummary.parsingFailures}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <XCircle size={16} className="text-destructive" />
              <span className="text-xs font-semibold text-muted-foreground">Indexing Failures</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{issuesSummary.indexingFailures}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <RefreshCw size={16} className="text-yellow-600" />
              <span className="text-xs font-semibold text-muted-foreground">Synced Not Indexed</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{issuesSummary.syncedNotIndexed}</p>
          </div>
        </div>

        {/* Total Issues Alert */}
        {issuesSummary.total > 0 && (
          <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/30 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle size={20} className="text-destructive" />
              <div>
                <p className="text-sm font-semibold text-foreground">
                  {issuesSummary.total} issue{issuesSummary.total !== 1 ? "s" : ""} require attention
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Review and resolve issues to maintain RAG pipeline health
                </p>
              </div>
            </div>
            <button className="px-4 py-2 rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors text-sm font-medium">
              View All Issues
            </button>
          </div>
        )}

        {/* Issues List */}
        <div className="p-6 rounded-lg bg-card border border-border">
          <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
            <AlertCircle size={20} className="text-accent" />
            Recent Issues (Last 24h)
          </h3>
          <div className="space-y-3">
            {issues.length > 0 ? (
              issues.map((issue) => (
                <div
                  key={issue.id}
                  className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <div className="mt-0.5">{getIssueIcon(issue.type)}</div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-foreground">{issue.title}</h4>
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              issue.severity === "critical"
                                ? "bg-destructive/20 text-destructive"
                                : issue.severity === "warning"
                                ? "bg-yellow-500/20 text-yellow-600"
                                : "bg-blue-500/20 text-blue-600"
                            }`}
                          >
                            {issue.severity.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">{issue.description}</p>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock size={12} />
                            {issue.timestamp}
                          </span>
                          {issue.url && (
                            <a
                              href={issue.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-accent hover:underline"
                            >
                              <ExternalLink size={12} />
                              View URL
                            </a>
                          )}
                          {issue.fileName && (
                            <span className="flex items-center gap-1">
                              <FileText size={12} />
                              {issue.fileName}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="px-3 py-1.5 rounded-lg bg-card border border-border text-foreground hover:bg-muted/50 transition-colors text-xs font-medium">
                        Retry
                      </button>
                      <button className="px-3 py-1.5 rounded-lg bg-muted/50 text-muted-foreground hover:bg-muted transition-colors text-xs font-medium">
                        Dismiss
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center">
                <CheckCircle2 size={48} className="text-green-500 mx-auto mb-3" />
                <p className="text-sm font-semibold text-foreground mb-1">No Issues Found</p>
                <p className="text-xs text-muted-foreground">All systems operating normally</p>
              </div>
            )}
          </div>
        </div>

        {/* Issue Categories Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Critical Issues */}
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <AlertTriangle size={20} className="text-destructive" />
              Critical Issues
            </h3>
            <div className="space-y-2">
              {issues.filter((i) => i.severity === "critical").length > 0 ? (
                issues
                  .filter((i) => i.severity === "critical")
                  .map((issue) => (
                    <div
                      key={issue.id}
                      className="p-3 rounded-lg bg-destructive/10 border border-destructive/30"
                    >
                      <p className="text-sm font-medium text-foreground">{issue.title}</p>
                      <p className="text-xs text-muted-foreground mt-1">{issue.timestamp}</p>
                    </div>
                  ))
              ) : (
                <p className="text-sm text-muted-foreground">No critical issues</p>
              )}
            </div>
          </div>

          {/* Warning Issues */}
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <AlertCircle size={20} className="text-yellow-600" />
              Warning Issues
            </h3>
            <div className="space-y-2">
              {issues.filter((i) => i.severity === "warning").length > 0 ? (
                issues
                  .filter((i) => i.severity === "warning")
                  .map((issue) => (
                    <div
                      key={issue.id}
                      className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30"
                    >
                      <p className="text-sm font-medium text-foreground">{issue.title}</p>
                      <p className="text-xs text-muted-foreground mt-1">{issue.timestamp}</p>
                    </div>
                  ))
              ) : (
                <p className="text-sm text-muted-foreground">No warning issues</p>
              )}
            </div>
          </div>
        </div>
        </div>
      )}

      {/* Freshness Tab Content */}
      {activeTab === "freshness" && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-2">Document Freshness & Staleness Alerts</h2>
            <p className="text-muted-foreground">Monitor document freshness, URL changes, and new IRS releases</p>
          </div>

        {/* Freshness Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-lg bg-card border border-border">
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-yellow-500/20 flex items-center justify-center text-yellow-600">
                <Calendar size={24} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Docs Stale &gt; 30 Days</p>
            <p className="text-3xl font-bold text-foreground">{freshnessMetrics.docsStaleOver30Days}</p>
            <p className="text-xs text-muted-foreground mt-2">Documents not updated in over 30 days</p>
          </div>

          <div className="p-6 rounded-lg bg-card border border-border">
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-orange-500/20 flex items-center justify-center text-orange-600">
                <Globe size={24} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">URLs Changed This Week</p>
            <p className="text-3xl font-bold text-foreground">{freshnessMetrics.urlsChangedThisWeek}</p>
            <p className="text-xs text-muted-foreground mt-2">Source URLs modified or restructured</p>
          </div>

          <div className="p-6 rounded-lg bg-card border border-border">
            <div className="flex items-start justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center text-green-600">
                <FileCheck size={24} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">New IRS Releases Today</p>
            <p className="text-3xl font-bold text-foreground">{freshnessMetrics.newIrsReleasesToday}</p>
            <p className="text-xs text-muted-foreground mt-2">New documents detected from IRS</p>
          </div>
        </div>

        {/* Additional Freshness Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={16} className="text-yellow-600" />
              <span className="text-xs font-semibold text-muted-foreground">Stale &gt; 1 Year</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{freshnessMetrics.docsStaleOver1Year}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={16} className="text-orange-600" />
              <span className="text-xs font-semibold text-muted-foreground">Stale &gt; 2 Years</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{freshnessMetrics.docsStaleOver2Years}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Globe size={16} className="text-blue-600" />
              <span className="text-xs font-semibold text-muted-foreground">State Guidance Updated</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{freshnessMetrics.stateGuidanceUpdated}</p>
          </div>
          <div className="p-4 rounded-lg bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <FileText size={16} className="text-purple-600" />
              <span className="text-xs font-semibold text-muted-foreground">FAQ Pages Updated</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{freshnessMetrics.faqPagesUpdated}</p>
          </div>
        </div>

        {/* Stale Documents List */}
        {staleDocuments.length > 0 && (
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <AlertTriangle size={20} className="text-yellow-600" />
              Stale Documents (&gt; 30 Days)
            </h3>
            <div className="space-y-3">
              {staleDocuments.map((doc) => (
                <div
                  key={doc.id}
                  className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <FileText size={20} className="text-yellow-600 mt-0.5" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-foreground">{doc.name}</h4>
                          {doc.hasNewerVersion && (
                            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-600">
                              Newer Version Available
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar size={12} />
                            Last crawled: {doc.lastCrawled}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock size={12} />
                            {doc.daysStale} days stale
                          </span>
                          {doc.sourceUrl && (
                            <a
                              href={doc.sourceUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-accent hover:underline"
                            >
                              <ExternalLink size={12} />
                              View Source
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                    <button className="px-3 py-1.5 rounded-lg bg-card border border-border text-foreground hover:bg-muted/50 transition-colors text-xs font-medium">
                      Re-crawl
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* URL Changes This Week */}
        {urlChanges.length > 0 && (
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <Globe size={20} className="text-orange-600" />
              URLs Changed This Week
            </h3>
            <div className="space-y-3">
              {urlChanges.map((change) => (
                <div
                  key={change.id}
                  className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/30"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <Link2 size={20} className="text-orange-600 mt-0.5" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-foreground truncate">{change.url}</h4>
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-orange-500/20 text-orange-600 capitalize">
                            {change.changeType.replace("_", " ")}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">{change.description}</p>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar size={12} />
                            Detected: {change.detectedDate}
                          </span>
                          <a
                            href={change.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-accent hover:underline"
                          >
                            <ExternalLink size={12} />
                            View URL
                          </a>
                        </div>
                      </div>
                    </div>
                    <button className="px-3 py-1.5 rounded-lg bg-card border border-border text-foreground hover:bg-muted/50 transition-colors text-xs font-medium">
                      Verify
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* New IRS Releases Today */}
        {newIrsReleases.length > 0 && (
          <div className="p-6 rounded-lg bg-card border border-border">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <FileCheck size={20} className="text-green-600" />
              New IRS Releases Detected Today
            </h3>
            <div className="space-y-3">
              {newIrsReleases.map((release) => (
                <div
                  key={release.id}
                  className="p-4 rounded-lg bg-green-500/10 border border-green-500/30"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1">
                      <FileCheck size={20} className="text-green-600 mt-0.5" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-foreground">{release.title}</h4>
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-600 capitalize">
                            {release.type}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar size={12} />
                            Released: {release.releaseDate}
                          </span>
                          <a
                            href={release.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-accent hover:underline"
                          >
                            <ExternalLink size={12} />
                            View Document
                          </a>
                        </div>
                      </div>
                    </div>
                    <button className="px-3 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors text-xs font-medium">
                      Add to KB
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Freshness Summary Alert */}
        {(freshnessMetrics.docsStaleOver30Days > 0 || freshnessMetrics.urlsChangedThisWeek > 0) && (
          <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle size={20} className="text-yellow-600" />
              <div>
                <p className="text-sm font-semibold text-foreground">
                  Freshness Alerts Require Attention
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {freshnessMetrics.docsStaleOver30Days} documents outdated, {freshnessMetrics.urlsChangedThisWeek} URLs changed this week
                </p>
              </div>
            </div>
            <button className="px-4 py-2 rounded-lg bg-yellow-600 text-white hover:bg-yellow-700 transition-colors text-sm font-medium">
              Review All
            </button>
          </div>
        )}
        </div>
      )}
    </div>
  )
}
