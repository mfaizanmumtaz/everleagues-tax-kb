"use client"

import { useState, useRef, useEffect } from "react"
import { FileText, Filter, Trash2, Download, Search, ChevronLeft, ChevronRight, Globe, ExternalLink, AlertCircle, X, ChevronDown, Check, AlertTriangle, ChevronUp, Database, Cpu, RefreshCw, Archive, Unlink, GitCompare, Calendar, Edit2, Info, History, Clock, User, FileCheck, CheckCircle2, XCircle, ArrowRight } from "lucide-react"
import { useGovernanceLog } from "@/contexts/governance-log-context"

interface IngestionHistoryEvent {
  timestamp: string
  action: "uploaded" | "synced" | "indexed" | "re_crawled" | "re_indexed"
  status: "success" | "failed" | "in_progress"
  details?: string
  userId?: string
}

interface ErrorHistoryEvent {
  timestamp: string
  type: "sync_error" | "index_error" | "validation_error" | "ocr_error"
  message: string
  severity: "critical" | "warning" | "info"
  resolved?: boolean
  resolvedAt?: string
}

interface GovernanceHistoryEvent {
  timestamp: string
  action: "state_changed" | "metadata_updated" | "authority_changed"
  userId?: string
  previousValue?: string
  newValue: string
  reason?: string
}

interface File {
  id: string
  name: string
  size: string
  tags: string[]
  uploadedDate: string
  syncStatus: "synced" | "syncing" | "sync_failed"
  indexStatus: "indexed" | "indexing" | "index_failed" | "not_indexed"
  sourceUrl?: string
  sourceDomain?: string
  syncError?: string
  indexError?: string
  knowledgeBaseId?: string
  knowledgeBaseName?: string
  taxYear?: number
  effectiveFrom?: string
  effectiveTo?: string
  appliesToTaxYears?: number[]
  appliesToJurisdictions?: string[]
  replacedBy?: string
  supersededBy?: string
  supersededByVersionId?: string  // Version ID that supersedes this doc (same tax_year only)
  hasNewerVersion?: boolean
  lastCrawled?: string
  chunkCount?: number
  embeddingModel?: string
  tokensIndexed?: number
  ragErrors?: string
  lastEmbedded?: string
  authorityLevel?: 1 | 2 | 3 | 4 | 5 | 6
  authorityLevelRationale?: string
  governanceState?: "Draft" | "Under Review" | "Published" | "Deprecated"
  ingestionHistory?: IngestionHistoryEvent[]
  errorHistory?: ErrorHistoryEvent[]
  governanceHistory?: GovernanceHistoryEvent[]
  supersessionChain?: string[]
  // New fields for tax-year validity, version lineage, citable eligibility
  docType?: "form" | "instructions" | "schedule" | "publication" | "other"
  formFamily?: string
  version?: string
  revisionDate?: string
  parsingQuality?: "ok" | "partial" | "failed"
  isLatestForTaxYear?: boolean
  // Red Flag System - AI Classification Confidence
  classificationConfidence?: number  // 0-100 percentage
  needsHumanReview?: boolean  // True if AI couldn't classify with confidence
  reviewReason?: string  // Why it was flagged
  reviewedAt?: string  // Timestamp when human reviewed
  reviewedBy?: string  // Who reviewed it
}

const initialFiles: File[] = [
  {
    id: "1",
    name: "Form_1040_2024.pdf",
    size: "2.4 MB",
    tags: ["federal", "forms", "2024"],
    uploadedDate: "2024-11-20",
    syncStatus: "synced",
    indexStatus: "indexed",
    sourceUrl: "https://www.irs.gov/forms-pubs/about-form-1040",
    sourceDomain: "irs.gov",
    knowledgeBaseId: "kb_federal_individual",
    knowledgeBaseName: "Tax – Federal Individual",
    taxYear: 2024,
    effectiveFrom: "2024-01-01",
    appliesToTaxYears: [2024],
    appliesToJurisdictions: ["federal"],
    hasNewerVersion: true,
    lastCrawled: "2024-11-20 03:12 UTC",
    chunkCount: 384,
    embeddingModel: "text-embedding-3-large",
    tokensIndexed: 92000,
    ragErrors: "0",
    lastEmbedded: "2024-11-20 03:15 UTC",
    authorityLevel: 2,
    authorityLevelRationale: "IRS official form - Level 2 authority (Forms/Instructions). Auto-assigned based on URL pattern matching irs.gov/forms-pubs.",
    governanceState: "Published",
    ingestionHistory: [
      { timestamp: "2024-11-20 03:00 UTC", action: "synced", status: "success", details: "Downloaded from https://www.irs.gov/forms-pubs/about-form-1040" },
      { timestamp: "2024-11-20 03:12 UTC", action: "indexed", status: "success", details: "384 chunks created, 92,000 tokens indexed" },
    ],
    errorHistory: [],
    governanceHistory: [
      { timestamp: "2024-11-20 03:15 UTC", action: "state_changed", previousValue: "Draft", newValue: "Published", userId: "admin@example.com", reason: "Document verified and ready for use" },
    ],
    supersessionChain: [],
    docType: "form",
    formFamily: "1040",
    version: "2024-v1",
    revisionDate: "2024-01-15",
    parsingQuality: "ok",
    isLatestForTaxYear: true,
    classificationConfidence: 95,
    needsHumanReview: false,
  },
  {
    id: "2",
    name: "Schedule_C_2024.pdf",
    size: "1.8 MB",
    tags: ["federal", "forms", "2024"],
    uploadedDate: "2024-11-19",
    syncStatus: "synced",
    indexStatus: "indexing",
    sourceUrl: "https://www.irs.gov/forms-pubs/about-schedule-c-form-1040",
    sourceDomain: "irs.gov",
    knowledgeBaseId: "kb_federal_individual",
    knowledgeBaseName: "Tax – Federal Individual",
    taxYear: 2024,
    effectiveFrom: "2024-01-01",
    appliesToTaxYears: [2024],
    appliesToJurisdictions: ["federal"],
    lastCrawled: "2024-11-19 14:30 UTC",
    chunkCount: 256,
    embeddingModel: "text-embedding-3-large",
    tokensIndexed: 61000,
    ragErrors: "0",
    lastEmbedded: "2024-11-19 14:33 UTC",
    authorityLevel: 2,
    authorityLevelRationale: "IRS official form - Level 2 authority (Forms/Instructions). Auto-assigned based on URL pattern matching irs.gov/forms-pubs.",
    governanceState: "Under Review",
    ingestionHistory: [
      { timestamp: "2024-11-19 14:20 UTC", action: "synced", status: "success", details: "Downloaded from https://www.irs.gov/forms-pubs/about-schedule-c-form-1040" },
      { timestamp: "2024-11-19 14:30 UTC", action: "indexed", status: "in_progress", details: "Indexing in progress..." },
    ],
    errorHistory: [],
    governanceHistory: [
      { timestamp: "2024-11-19 14:35 UTC", action: "state_changed", previousValue: "Draft", newValue: "Under Review", userId: "curator@example.com", reason: "Pending review for accuracy" },
    ],
    supersessionChain: [],
    docType: "schedule",
    formFamily: "SchC",
    version: "2024-v1",
    revisionDate: "2024-01-10",
    parsingQuality: "ok",
    isLatestForTaxYear: true,
    classificationConfidence: 88,
    needsHumanReview: false,
  },
  {
    id: "3",
    name: "State_Tax_Return_CA.pdf",
    size: "3.1 MB",
    tags: ["state", "forms", "sales-tax"],
    uploadedDate: "2024-11-18",
    syncStatus: "synced",
    indexStatus: "index_failed",
    sourceUrl: "https://www.tax.ca.gov/forms-publications/individual-income-tax",
    sourceDomain: "tax.ca.gov",
    indexError: "OCR validation failed: 3 pages could not be processed. Low image quality detected.",
    knowledgeBaseId: "kb_sales_tax",
    knowledgeBaseName: "Tax – Sales Tax",
    taxYear: 2024,
    effectiveFrom: "2024-01-01",
    appliesToTaxYears: [2024],
    appliesToJurisdictions: ["state", "CA"],
    lastCrawled: "2024-11-18 09:45 UTC",
    chunkCount: 192,
    embeddingModel: "text-embedding-3-large",
    tokensIndexed: 45000,
    ragErrors: "3 paragraphs skipped (bad HTML)",
    lastEmbedded: "2024-11-18 09:48 UTC",
    authorityLevel: 6,
    authorityLevelRationale: "State tax form from California - Level 6 authority (Other/Low Authority). State forms have lower authority than federal IRS forms.",
    governanceState: "Draft",
    ingestionHistory: [
      { timestamp: "2024-11-18 09:30 UTC", action: "synced", status: "success", details: "Downloaded from https://www.tax.ca.gov/forms-publications/individual-income-tax" },
      { timestamp: "2024-11-18 09:45 UTC", action: "indexed", status: "failed", details: "OCR validation failed" },
    ],
    errorHistory: [
      { timestamp: "2024-11-18 09:45 UTC", type: "ocr_error", message: "OCR validation failed: 3 pages could not be processed. Low image quality detected.", severity: "warning", resolved: false },
    ],
    governanceHistory: [
      { timestamp: "2024-11-18 09:50 UTC", action: "state_changed", previousValue: undefined, newValue: "Draft", userId: "system", reason: "Auto-assigned Draft state on ingestion" },
    ],
    supersessionChain: [],
    docType: "form",
    formFamily: "540",
    version: "2024-v1",
    revisionDate: "2024-01-05",
    parsingQuality: "partial",
    isLatestForTaxYear: true,
    classificationConfidence: 45,
    needsHumanReview: true,
    reviewReason: "Low confidence (45%): State tax form - could be Level 3 (official state guidance) or Level 6 (other). Multiple authority patterns detected.",
  },
  {
    id: "4",
    name: "W2_Forms_2024.pdf",
    size: "5.2 MB",
    tags: ["federal", "forms", "2024"],
    uploadedDate: "2024-11-17",
    syncStatus: "sync_failed",
    indexStatus: "not_indexed",
    sourceUrl: "https://www.irs.gov/forms-pubs/about-form-w-2",
    sourceDomain: "irs.gov",
    syncError: "Download timeout: Connection to irs.gov timed out after 30 seconds. Please check network connectivity.",
    knowledgeBaseId: "kb_federal_individual",
    knowledgeBaseName: "Tax – Federal Individual",
    taxYear: 2024,
    effectiveFrom: "2024-01-01",
    appliesToTaxYears: [2024],
    appliesToJurisdictions: ["federal"],
    authorityLevel: 2,
    authorityLevelRationale: "IRS official form - Level 2 authority (Forms/Instructions). Auto-assigned based on URL pattern matching irs.gov/forms-pubs.",
    governanceState: "Draft",
    ingestionHistory: [
      { timestamp: "2024-11-17 10:00 UTC", action: "synced", status: "failed", details: "Download timeout after 30 seconds" },
    ],
    errorHistory: [
      { timestamp: "2024-11-17 10:00 UTC", type: "sync_error", message: "Download timeout: Connection to irs.gov timed out after 30 seconds. Please check network connectivity.", severity: "critical", resolved: false },
    ],
    governanceHistory: [
      { timestamp: "2024-11-17 10:05 UTC", action: "state_changed", previousValue: undefined, newValue: "Draft", userId: "system", reason: "Auto-assigned Draft state on failed ingestion" },
    ],
    supersessionChain: [],
    docType: "form",
    formFamily: "W-2",
    version: "2024-v1",
    revisionDate: "2024-01-01",
    parsingQuality: "failed",
    isLatestForTaxYear: true,
    classificationConfidence: 92,
    needsHumanReview: false,
  },
  {
    id: "5",
    name: "Quarterly_Estimated_Q4.pdf",
    size: "1.5 MB",
    tags: ["federal", "instructions", "2024"],
    uploadedDate: "2024-11-16",
    syncStatus: "syncing",
    indexStatus: "not_indexed",
    sourceUrl: "https://www.irs.gov/forms-pubs/about-form-1040-es",
    sourceDomain: "irs.gov",
    knowledgeBaseId: "kb_small_business",
    knowledgeBaseName: "Tax – Small Business",
    taxYear: 2024,
    effectiveFrom: "2024-10-01",
    appliesToTaxYears: [2024],
    appliesToJurisdictions: ["federal"],
    lastCrawled: "2024-11-16 11:20 UTC",
    chunkCount: 128,
    embeddingModel: "text-embedding-3-large",
    tokensIndexed: 31000,
    ragErrors: "0",
    lastEmbedded: "2024-11-16 11:22 UTC",
    authorityLevel: 2,
    authorityLevelRationale: "IRS official form - Level 2 authority (Forms/Instructions). Auto-assigned based on URL pattern matching irs.gov/forms-pubs.",
    governanceState: "Under Review",
    ingestionHistory: [
      { timestamp: "2024-11-16 11:10 UTC", action: "synced", status: "in_progress", details: "Downloading from https://www.irs.gov/forms-pubs/about-form-1040-es" },
    ],
    errorHistory: [],
    governanceHistory: [
      { timestamp: "2024-11-16 11:25 UTC", action: "state_changed", previousValue: "Draft", newValue: "Under Review", userId: "curator@example.com", reason: "Pending quarterly review" },
    ],
    supersessionChain: [],
    docType: "instructions",
    formFamily: "1040-ES",
    version: "2024-Q4",
    revisionDate: "2024-10-01",
    parsingQuality: "ok",
    isLatestForTaxYear: true,
    classificationConfidence: 85,
    needsHumanReview: false,
  },
  {
    id: "6",
    name: "IRS_Revenue_Ruling_2024.pdf",
    size: "0.8 MB",
    tags: ["federal", "bulletins", "2024"],
    uploadedDate: "2024-11-15",
    syncStatus: "synced",
    indexStatus: "indexed",
    sourceUrl: "https://www.irs.gov/pub/irs-drop/rr-24-01.pdf",
    sourceDomain: "irs.gov",
    knowledgeBaseId: "kb_federal_individual",
    knowledgeBaseName: "Tax – Federal Individual",
    taxYear: 2024,
    effectiveFrom: "2024-01-15",
    effectiveTo: "2024-12-31",
    appliesToTaxYears: [2024],
    appliesToJurisdictions: ["federal"],
    lastCrawled: "2024-11-15 16:10 UTC",
    chunkCount: 64,
    embeddingModel: "text-embedding-3-large",
    tokensIndexed: 15000,
    ragErrors: "0",
    lastEmbedded: "2024-11-15 16:12 UTC",
    authorityLevel: 3,
    authorityLevelRationale: "IRS Revenue Procedure - Level 3 authority (Rulings/Procedures). Auto-assigned based on URL pattern matching irs.gov/pub/irs-drop.",
    governanceState: "Published",
    ingestionHistory: [
      { timestamp: "2024-11-15 16:00 UTC", action: "synced", status: "success", details: "Downloaded from https://www.irs.gov/pub/irs-drop/rr-24-01.pdf" },
      { timestamp: "2024-11-15 16:10 UTC", action: "indexed", status: "success", details: "64 chunks created, 15,000 tokens indexed" },
    ],
    errorHistory: [],
    governanceHistory: [
      { timestamp: "2024-11-15 16:15 UTC", action: "state_changed", previousValue: "Under Review", newValue: "Published", userId: "admin@example.com", reason: "Revenue procedure verified and published" },
    ],
    supersessionChain: [],
    docType: "publication",
    formFamily: "RR",
    version: "RR-24-01",
    revisionDate: "2024-01-15",
    parsingQuality: "ok",
    isLatestForTaxYear: true,
    classificationConfidence: 78,
    needsHumanReview: false,
  },
  {
    id: "7",
    name: "Tax_Code_Title_26.pdf",
    size: "12.4 MB",
    tags: ["federal", "code"],
    uploadedDate: "2024-11-14",
    syncStatus: "synced",
    indexStatus: "indexed",
    sourceUrl: "https://uscode.house.gov/view.xhtml?path=/prelim@title26",
    sourceDomain: "uscode.house.gov",
    knowledgeBaseId: "kb_federal_individual",
    knowledgeBaseName: "Tax – Federal Individual",
    taxYear: 2023,
    effectiveFrom: "2023-01-01",
    effectiveTo: "2023-12-31",
    appliesToTaxYears: [2023],
    appliesToJurisdictions: ["federal"],
    replacedBy: "Tax_Code_Title_26_2024.pdf",
    supersededBy: "Tax_Code_Title_26_2024.pdf",
    supersededByVersionId: "2024-v1",  // Version ID of the superseding doc (same form family)
    lastCrawled: "2024-11-14 08:30 UTC",
    chunkCount: 1024,
    embeddingModel: "text-embedding-3-large",
    tokensIndexed: 245000,
    ragErrors: "0",
    lastEmbedded: "2024-11-14 08:45 UTC",
    authorityLevel: 1,
    authorityLevelRationale: "US Code Title 26 - Level 1 authority (Statute/Reg). Highest authority level. Auto-assigned based on URL pattern matching uscode.house.gov.",
    governanceState: "Deprecated",
    ingestionHistory: [
      { timestamp: "2024-11-14 08:20 UTC", action: "synced", status: "success", details: "Downloaded from https://uscode.house.gov/view.xhtml?path=/prelim@title26" },
      { timestamp: "2024-11-14 08:30 UTC", action: "indexed", status: "success", details: "1024 chunks created, 245,000 tokens indexed" },
      { timestamp: "2024-11-20 10:00 UTC", action: "re_crawled", status: "success", details: "Re-crawled to check for updates" },
    ],
    errorHistory: [],
    governanceHistory: [
      { timestamp: "2024-11-14 08:50 UTC", action: "state_changed", previousValue: undefined, newValue: "Published", userId: "admin@example.com", reason: "Initial publication" },
      { timestamp: "2024-11-20 10:05 UTC", action: "state_changed", previousValue: "Published", newValue: "Deprecated", userId: "admin@example.com", reason: "Superseded by 2024 version" },
      { timestamp: "2024-11-20 10:05 UTC", action: "metadata_updated", previousValue: undefined, newValue: "Tax_Code_Title_26_2024.pdf", userId: "admin@example.com", reason: "Set supersededBy field" },
    ],
    supersessionChain: ["Tax_Code_Title_26_2024.pdf"],
    docType: "other",
    formFamily: "USC-26",
    version: "2023-v1",
    revisionDate: "2023-01-01",
    parsingQuality: "ok",
    isLatestForTaxYear: false,
    classificationConfidence: 98,
    needsHumanReview: false,
    reviewedAt: "2024-11-14 09:00 UTC",
    reviewedBy: "admin@example.com",
  },
  {
    id: "8",
    name: "FAQ_Individual_Taxes.pdf",
    size: "2.1 MB",
    tags: ["federal", "faq"],
    uploadedDate: "2024-11-13",
    syncStatus: "synced",
    indexStatus: "index_failed",
    sourceUrl: "https://www.irs.gov/faqs/individual-income-tax",
    sourceDomain: "irs.gov",
    indexError: "Embedding generation failed: Invalid text encoding detected. File may be corrupted.",
    knowledgeBaseId: "kb_federal_individual",
    knowledgeBaseName: "Tax – Federal Individual",
    taxYear: 2024,
    effectiveFrom: "2024-01-01",
    appliesToTaxYears: [2023, 2024, 2025],
    appliesToJurisdictions: ["federal"],
    lastCrawled: "2024-11-13 12:00 UTC",
    chunkCount: 0,
    embeddingModel: "text-embedding-3-large",
    tokensIndexed: 0,
    ragErrors: "Embedding generation failed",
    lastEmbedded: "N/A",
    authorityLevel: 4,
    authorityLevelRationale: "IRS FAQ - Level 4 authority (FAQs/Publications). Auto-assigned based on URL pattern matching irs.gov/faqs.",
    governanceState: "Draft",
    ingestionHistory: [
      { timestamp: "2024-11-13 11:50 UTC", action: "synced", status: "success", details: "Downloaded from https://www.irs.gov/faqs/individual-income-tax" },
      { timestamp: "2024-11-13 12:00 UTC", action: "indexed", status: "failed", details: "Embedding generation failed" },
    ],
    errorHistory: [
      { timestamp: "2024-11-13 12:00 UTC", type: "index_error", message: "Embedding generation failed: Invalid text encoding detected. File may be corrupted.", severity: "critical", resolved: false },
      { timestamp: "2024-11-13 12:00 UTC", type: "validation_error", message: "Text encoding validation failed during processing", severity: "warning", resolved: false },
    ],
    governanceHistory: [
      { timestamp: "2024-11-13 12:05 UTC", action: "state_changed", previousValue: undefined, newValue: "Draft", userId: "system", reason: "Auto-assigned Draft state due to indexing failure" },
    ],
    supersessionChain: [],
    docType: "publication",
    formFamily: "FAQ",
    version: "2024-v1",
    revisionDate: "2024-01-01",
    parsingQuality: "failed",
    isLatestForTaxYear: true,
    classificationConfidence: 52,
    needsHumanReview: true,
    reviewReason: "Low confidence (52%): FAQ document - could be Level 4 (FAQ/Publications) or Level 5 (Expert Sources). Parsing quality issues also detected.",
  },
]

// Helper function to extract domain from URL
const getDomainFromUrl = (url: string): string => {
  try {
    const urlObj = new URL(url)
    return urlObj.hostname.replace("www.", "")
  } catch {
    return url
  }
}

// Helper function to format source path
const formatSourcePath = (url: string): string => {
  try {
    const urlObj = new URL(url)
    const pathParts = urlObj.pathname.split("/").filter(Boolean)
    const domain = urlObj.hostname.replace("www.", "")
    const filename = pathParts[pathParts.length - 1] || ""
    
    if (pathParts.length > 0) {
      return `${domain} › ${pathParts.slice(0, -1).join(" › ")}${filename ? ` › ${filename}` : ""}`
    }
    return domain
  } catch {
    return url
  }
}

const JURISDICTION_TAGS = ["federal", "state", "local"]

const US_STATES = [
  "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
  "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
  "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
  "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
  "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
  "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
  "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
  "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
  "Washington", "West Virginia", "Wisconsin", "Wyoming",
]

const KNOWLEDGE_BASES = [
  { id: "all", name: "All" },
  { id: "kb_federal_individual", name: "Tax – Federal Individual" },
  { id: "kb_small_business", name: "Tax – Small Business" },
  { id: "kb_sales_tax", name: "Tax – Sales Tax" },
  { id: "kb_hospital_compliance", name: "Hospital Compliance" },
]

// Authority Level Definitions
const AUTHORITY_LEVELS = {
  1: {
    label: "Level 1 – Statute/Reg",
    description: "IRC, Treasury Regs, CFR",
    color: "bg-blue-500/20 text-blue-600 border-blue-500/30",
    badgeColor: "bg-blue-500",
  },
  2: {
    label: "Level 2 – Forms/Instructions",
    description: "IRS forms",
    color: "bg-green-500/20 text-green-600 border-green-500/30",
    badgeColor: "bg-green-500",
  },
  3: {
    label: "Level 3 – Rulings/Procedures",
    description: "Revenue Rulings, Notices",
    color: "bg-purple-500/20 text-purple-600 border-purple-500/30",
    badgeColor: "bg-purple-500",
  },
  4: {
    label: "Level 4 – FAQs/Publications",
    description: "IRS FAQs, IRM",
    color: "bg-orange-500/20 text-orange-600 border-orange-500/30",
    badgeColor: "bg-orange-500",
  },
  5: {
    label: "Level 5 – Expert Sources",
    description: "Big-4 memos, CCH, RIA",
    color: "bg-yellow-500/20 text-yellow-600 border-yellow-500/30",
    badgeColor: "bg-yellow-500",
  },
  6: {
    label: "Level 6 – Other/Low Authority",
    description: "Blogs, generic articles",
    color: "bg-gray-500/20 text-gray-600 border-gray-500/30",
    badgeColor: "bg-gray-500",
  },
} as const

// Helper function to auto-assign authority level based on URL (for display purposes)
// In production, this would be done on the backend during ingestion
const getAuthorityLevelFromUrl = (url: string): 1 | 2 | 3 | 4 | 5 | 6 => {
  const urlLower = url.toLowerCase()
  
  // Level 1: Statute/Reg (IRC, Treasury Regs, CFR)
  if (urlLower.includes("law.cornell.edu") || 
      urlLower.includes("govinfo.gov") ||
      urlLower.includes("/irc/") ||
      urlLower.includes("/cfr/") ||
      urlLower.includes("treasury.gov/regulations")) {
    return 1
  }
  
  // Level 2: Forms/Instructions
  if (urlLower.includes("irs.gov/forms-pubs") ||
      urlLower.includes("irs.gov/forms-instructions") ||
      urlLower.includes("/form-")) {
    return 2
  }
  
  // Level 3: Rulings/Procedures
  if (urlLower.includes("irs.gov/pub/irs-drop") ||
      urlLower.includes("revenue-ruling") ||
      urlLower.includes("revenue-procedure") ||
      urlLower.includes("/rr-") ||
      urlLower.includes("/rp-")) {
    return 3
  }
  
  // Level 4: FAQs/Publications
  if (urlLower.includes("irs.gov/faqs") ||
      urlLower.includes("irs.gov/publications") ||
      urlLower.includes("/pub/") ||
      urlLower.includes("/irm/")) {
    return 4
  }
  
  // Level 5: Expert Sources
  if (urlLower.includes("cch.com") ||
      urlLower.includes("ria.thomsonreuters.com") ||
      urlLower.includes("pwc.com") ||
      urlLower.includes("deloitte.com") ||
      urlLower.includes("ey.com") ||
      urlLower.includes("kpmg.com")) {
    return 5
  }
  
  // Level 6: Other/Low Authority (default)
  return 6
}

// Governance State Definitions
const GOVERNANCE_STATES = ["Draft", "Under Review", "Published", "Deprecated"] as const
type GovernanceState = typeof GOVERNANCE_STATES[number]

const GOVERNANCE_STATE_STYLES: Record<GovernanceState, { badge: string; color: string }> = {
  "Draft": {
    badge: "bg-yellow-500/20 text-yellow-600 border-yellow-500/30",
    color: "text-yellow-600",
  },
  "Under Review": {
    badge: "bg-blue-500/20 text-blue-600 border-blue-500/30",
    color: "text-blue-600",
  },
  "Published": {
    badge: "bg-green-500/20 text-green-600 border-green-500/30",
    color: "text-green-600",
  },
  "Deprecated": {
    badge: "bg-gray-500/20 text-gray-600 border-gray-500/30",
    color: "text-gray-600",
  },
}

// Document type constants for form family classification
const DOC_TYPES: Record<string, { label: string; color: string }> = {
  form: { label: "Form", color: "bg-blue-500/20 text-blue-600 border-blue-500/30" },
  instructions: { label: "Instructions", color: "bg-purple-500/20 text-purple-600 border-purple-500/30" },
  schedule: { label: "Schedule", color: "bg-green-500/20 text-green-600 border-green-500/30" },
  publication: { label: "Publication", color: "bg-orange-500/20 text-orange-600 border-orange-500/30" },
  other: { label: "Other", color: "bg-gray-500/20 text-gray-600 border-gray-500/30" },
}

// Red Flag System - Confidence Threshold
const CONFIDENCE_THRESHOLD = 70  // Below this percentage = needs human review

// Helper function to get confidence color
const getConfidenceColor = (confidence: number | undefined): string => {
  if (confidence === undefined) return "bg-gray-500"
  if (confidence >= 70) return "bg-green-500"
  if (confidence >= 50) return "bg-amber-500"
  return "bg-red-500"
}

const getConfidenceTextColor = (confidence: number | undefined): string => {
  if (confidence === undefined) return "text-gray-600"
  if (confidence >= 70) return "text-green-600"
  if (confidence >= 50) return "text-amber-600"
  return "text-red-600"
}

// Helper function to get governance state badge class
const getGovernanceStateBadgeClass = (state: GovernanceState | undefined): string => {
  if (!state) return "bg-muted/50 text-muted-foreground border-border"
  return GOVERNANCE_STATE_STYLES[state].badge
}

// Helper function to format tax years array as display string
const formatTaxYears = (taxYears: number[] | undefined, singleTaxYear?: number): string => {
  if (taxYears && taxYears.length > 0) {
    const sorted = [...taxYears].sort((a, b) => a - b)
    // Check if consecutive
    const isConsecutive = sorted.every((year, index) => index === 0 || year === sorted[index - 1] + 1)
    if (isConsecutive && sorted.length > 1) {
      return `${sorted[0]}-${sorted[sorted.length - 1]}`
    }
    return sorted.join(", ")
  }
  if (singleTaxYear) {
    return String(singleTaxYear)
  }
  return ""
}

// Helper function to format effective date
const formatEffectiveDate = (dateString: string | undefined): string => {
  if (!dateString) return ""
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
  } catch {
    return dateString
  }
}

// Helper function to validate date range
const validateDateRange = (effectiveFrom: string | undefined, effectiveTo: string | undefined): boolean => {
  if (!effectiveFrom || !effectiveTo) return true
  try {
    const fromDate = new Date(effectiveFrom)
    const toDate = new Date(effectiveTo)
    return toDate >= fromDate
  } catch {
    return false
  }
}

// Compute citability for RAG answers based on multiple criteria
const computeCitability = (file: File): { isCitable: boolean; reasons: string[] } => {
  const reasons: string[] = []
  const currentTaxYear = 2024

  // Check Published state
  const isPublished = file.governanceState === "Published"
  if (isPublished) {
    reasons.push("Published")
  } else {
    reasons.push(`Not Published (${file.governanceState || "No state"})`)
  }

  // Check Authority Level <= 2 (higher authority = lower number)
  const hasHighAuthority = file.authorityLevel !== undefined && file.authorityLevel <= 2
  if (hasHighAuthority) {
    reasons.push(`Authority Level ${file.authorityLevel}`)
  } else {
    reasons.push(`Authority Level ${file.authorityLevel || "unset"} (needs 1-2)`)
  }

  // Check Tax Year is current
  const isCurrentTaxYear = file.taxYear === currentTaxYear || (file.appliesToTaxYears?.includes(currentTaxYear) ?? false)
  if (isCurrentTaxYear) {
    reasons.push(`Tax Year ${currentTaxYear}`)
  } else {
    reasons.push(`Tax Year ${file.taxYear || "unset"} (not current)`)
  }

  // Check not superseded (check both version ID and legacy name-based supersession)
  const isNotSuperseded = !file.supersededByVersionId && !file.supersededBy
  if (isNotSuperseded) {
    reasons.push("Not superseded")
  } else {
    const supersededBy = file.supersededByVersionId || file.supersededBy || "unknown"
    reasons.push(`Superseded by ${supersededBy}`)
  }

  // Check parsing quality
  const hasGoodParsing = file.parsingQuality === "ok" || !file.parsingQuality
  if (hasGoodParsing) {
    reasons.push("Parsing quality OK")
  } else {
    reasons.push(`Parsing quality: ${file.parsingQuality}`)
  }

  // Determine overall citability
  const isCitable = isPublished && hasHighAuthority && isCurrentTaxYear && isNotSuperseded && hasGoodParsing

  return { isCitable, reasons }
}

// Compute if document is latest for its tax year (within same form family)
const computeIsLatestForTaxYear = (file: File, allFiles: File[]): boolean => {
  // Must have tax year and form family to compute
  if (!file.taxYear || !file.formFamily) return false

  // If superseded by a version ID (same tax_year), it's not latest
  if (file.supersededByVersionId) {
    return false
  }

  // If superseded by name (legacy), it's not latest
  if (file.supersededBy) {
    return false
  }

  // Find all documents with same form family and tax year
  const sameFamilyAndYear = allFiles.filter(f =>
    f.formFamily === file.formFamily &&
    f.taxYear === file.taxYear &&
    f.id !== file.id &&
    f.version // Only compare documents that have versions
  )

  // If no other versions exist, this is latest
  if (sameFamilyAndYear.length === 0) {
    return true
  }

  // Compare versions to see if this is the latest
  const thisVersion = file.version || ""
  const hasNewerVersion = sameFamilyAndYear.some(f => {
    const otherVersion = f.version || ""
    // Simple string comparison for versions (e.g., "v2" > "v1", "2024-v2" > "2024-v1")
    return otherVersion > thisVersion && !f.supersededByVersionId
  })

  return !hasNewerVersion
}

export default function ELCloudFiles() {
  const { addLog } = useGovernanceLog()
  const [files, setFiles] = useState<File[]>(initialFiles)
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [selectedKB, setSelectedKB] = useState<string>("all")
  const [selectedAuthorityLevel, setSelectedAuthorityLevel] = useState<number | "all">("all")
  const [selectedGovernanceStates, setSelectedGovernanceStates] = useState<GovernanceState[]>([])
  const [governanceFilterDropdownOpen, setGovernanceFilterDropdownOpen] = useState(false)
  const governanceFilterDropdownRef = useRef<HTMLDivElement>(null)
  const [selectedReviewStatus, setSelectedReviewStatus] = useState<"all" | "needs_review" | "reviewed">("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 5
  const [errorDetailsFile, setErrorDetailsFile] = useState<File | null>(null)
  const [kbDropdownOpen, setKbDropdownOpen] = useState(false)
  const kbDropdownRef = useRef<HTMLDivElement>(null)
  const [governanceStateDropdownOpen, setGovernanceStateDropdownOpen] = useState<Record<string, boolean>>({})
  const governanceStateDropdownRef = useRef<Record<string, HTMLDivElement | null>>({})
  const [expandedRagFiles, setExpandedRagFiles] = useState<Set<string>>(new Set())
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [versionDiffModalOpen, setVersionDiffModalOpen] = useState(false)
  const [selectedVersion1, setSelectedVersion1] = useState<File | null>(null)
  const [selectedVersion2, setSelectedVersion2] = useState<File | null>(null)
  const [diffContent, setDiffContent] = useState<{ version1: string[], version2: string[] } | null>(null)
  const [editingFileId, setEditingFileId] = useState<string | null>(null)
  const [editingFile, setEditingFile] = useState<File | null>(null)
  const [editFormData, setEditFormData] = useState<{
    effectiveFrom?: string
    effectiveTo?: string
    appliesToTaxYears?: number[]
    appliesToJurisdictions?: string[]
    supersededBy?: string
    authorityLevel?: 1 | 2 | 3 | 4 | 5 | 6
    authorityLevelRationale?: string
    tags?: string[]
  }>({})
  const [tagInput, setTagInput] = useState("")
  const [detailsFile, setDetailsFile] = useState<File | null>(null)
  const [selectedStates, setSelectedStates] = useState<string[]>([])
  const [stateDropdownOpen, setStateDropdownOpen] = useState(false)
  const stateDropdownRef = useRef<HTMLDivElement>(null)

  const allTags = Array.from(new Set(files.flatMap((f) => f.tags)))
  const sortedTags = allTags.sort((a, b) => {
    // Sort tags: jurisdiction tags first, then others
    const aIsJurisdiction = JURISDICTION_TAGS.includes(a)
    const bIsJurisdiction = JURISDICTION_TAGS.includes(b)
    if (aIsJurisdiction !== bIsJurisdiction) return aIsJurisdiction ? -1 : 1
    return a.localeCompare(b)
  })

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (kbDropdownRef.current && !kbDropdownRef.current.contains(event.target as Node)) {
        setKbDropdownOpen(false)
      }
      if (governanceFilterDropdownRef.current && !governanceFilterDropdownRef.current.contains(event.target as Node)) {
        setGovernanceFilterDropdownOpen(false)
      }
      if (stateDropdownRef.current && !stateDropdownRef.current.contains(event.target as Node)) {
        setStateDropdownOpen(false)
      }
      Object.keys(governanceStateDropdownRef.current).forEach((fileId) => {
        const ref = governanceStateDropdownRef.current[fileId]
        if (ref && !ref.contains(event.target as Node)) {
          setGovernanceStateDropdownOpen((prev) => ({ ...prev, [fileId]: false }))
        }
      })
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const filteredFiles = files.filter((f) => {
    const matchesTags = selectedTags.length === 0 || selectedTags.some((tag) => f.tags.includes(tag))
    const matchesKB = selectedKB === "all" || f.knowledgeBaseId === selectedKB
    const matchesAuthority = selectedAuthorityLevel === "all" || f.authorityLevel === selectedAuthorityLevel
    const matchesGovernanceState = selectedGovernanceStates.length === 0 || selectedGovernanceStates.includes(f.governanceState as GovernanceState)
    const matchesReviewStatus = 
      selectedReviewStatus === "all" || 
      (selectedReviewStatus === "needs_review" && f.needsHumanReview) ||
      (selectedReviewStatus === "reviewed" && !f.needsHumanReview && f.reviewedAt)
    const matchesState = selectedStates.length === 0 || 
      (f.appliesToJurisdictions && selectedStates.some(state => 
        f.appliesToJurisdictions!.includes(state) || 
        f.appliesToJurisdictions!.includes(state.toUpperCase()) ||
        f.appliesToJurisdictions!.some(j => j.toLowerCase() === state.toLowerCase())
      ))
    const matchesSearch =
      searchQuery === "" ||
      f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesTags && matchesKB && matchesAuthority && matchesGovernanceState && matchesReviewStatus && matchesState && matchesSearch
  })

  const totalPages = Math.ceil(filteredFiles.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const paginatedFiles = filteredFiles.slice(startIndex, endIndex)

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]))
    setCurrentPage(1) // Reset to first page when filters change
  }

  const deleteFile = (id: string) => {
    setFiles(files.filter((f) => f.id !== id))
  }

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)))
  }

  const toggleRagVisibility = (fileId: string) => {
    setExpandedRagFiles((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(fileId)) {
        newSet.delete(fileId)
      } else {
        newSet.add(fileId)
      }
      return newSet
    })
  }

  const toggleFileSelection = (fileId: string) => {
    setSelectedFiles((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(fileId)) {
        newSet.delete(fileId)
      } else {
        newSet.add(fileId)
      }
      return newSet
    })
  }

  const updateGovernanceState = (fileId: string, newState: GovernanceState) => {
    const file = files.find(f => f.id === fileId)
    if (!file) return

    const previousState = file.governanceState || "Draft"

    // Log the governance action
    addLog(
      fileId,
      file.name,
      "state_changed",
      "governanceState",
      previousState,
      newState,
      `Governance state changed from ${previousState} to ${newState}`,
      "current-user@example.com",
      "current-user@example.com"
    )

    // Update file with new state AND add to governanceHistory
    setFiles((prevFiles) =>
      prevFiles.map((f) => {
        if (f.id === fileId) {
          const newHistoryEntry: GovernanceHistoryEvent = {
            timestamp: new Date().toISOString(),
            action: "state_changed",
            userId: "current-user@example.com",
            previousValue: previousState,
            newValue: newState,
            reason: `Governance state changed from ${previousState} to ${newState}`,
          }
          return {
            ...f,
            governanceState: newState,
            governanceHistory: [...(f.governanceHistory || []), newHistoryEntry],
          }
        }
        return f
      })
    )
    setGovernanceStateDropdownOpen((prev) => ({ ...prev, [fileId]: false }))
  }

  const handleEditFile = (file: File) => {
    setEditingFileId(file.id)
    setEditingFile(file)
    setEditFormData({
      effectiveFrom: file.effectiveFrom,
      effectiveTo: file.effectiveTo,
      appliesToTaxYears: file.appliesToTaxYears || (file.taxYear ? [file.taxYear] : []),
      appliesToJurisdictions: file.appliesToJurisdictions || [],
      supersededBy: file.supersededBy || file.replacedBy,
      authorityLevel: file.authorityLevel,
      authorityLevelRationale: "",  // Reset rationale for new edit session
      tags: file.tags || [],
    })
    setTagInput("")
  }

  const handleSaveGovernanceMetadata = () => {
    if (!editingFileId || !editingFile) return

    // Validate date range
    if (!validateDateRange(editFormData.effectiveFrom, editFormData.effectiveTo)) {
      alert("Effective To date must be after or equal to Effective From date")
      return
    }

    const file = files.find(f => f.id === editingFileId)
    if (!file) return

    // Log each changed field separately
    const newGovernanceHistory: GovernanceHistoryEvent[] = []
    const timestamp = new Date().toISOString()

    if (editFormData.effectiveFrom !== file.effectiveFrom) {
      addLog(
        editingFileId,
        file.name,
        "metadata_updated",
        "effectiveFrom",
        file.effectiveFrom,
        editFormData.effectiveFrom,
        "Effective From date updated via governance metadata editor",
        "current-user@example.com",
        "current-user@example.com"
      )
      newGovernanceHistory.push({
        timestamp,
        action: "metadata_updated",
        userId: "current-user@example.com",
        previousValue: file.effectiveFrom,
        newValue: editFormData.effectiveFrom || "",
        reason: "Effective From date updated",
      })
    }

    if (editFormData.effectiveTo !== file.effectiveTo) {
      addLog(
        editingFileId,
        file.name,
        "metadata_updated",
        "effectiveTo",
        file.effectiveTo,
        editFormData.effectiveTo,
        "Effective To date updated via governance metadata editor",
        "current-user@example.com",
        "current-user@example.com"
      )
      newGovernanceHistory.push({
        timestamp,
        action: "metadata_updated",
        userId: "current-user@example.com",
        previousValue: file.effectiveTo,
        newValue: editFormData.effectiveTo || "",
        reason: "Effective To date updated",
      })
    }

    if (JSON.stringify(editFormData.appliesToTaxYears) !== JSON.stringify(file.appliesToTaxYears)) {
      addLog(
        editingFileId,
        file.name,
        "metadata_updated",
        "appliesToTaxYears",
        file.appliesToTaxYears,
        editFormData.appliesToTaxYears,
        "Applies To Tax Years updated via governance metadata editor",
        "current-user@example.com",
        "current-user@example.com"
      )
      newGovernanceHistory.push({
        timestamp,
        action: "metadata_updated",
        userId: "current-user@example.com",
        previousValue: file.appliesToTaxYears?.join(", "),
        newValue: editFormData.appliesToTaxYears?.join(", ") || "",
        reason: "Applies To Tax Years updated",
      })
    }

    if (JSON.stringify(editFormData.appliesToJurisdictions) !== JSON.stringify(file.appliesToJurisdictions)) {
      addLog(
        editingFileId,
        file.name,
        "metadata_updated",
        "appliesToJurisdictions",
        file.appliesToJurisdictions,
        editFormData.appliesToJurisdictions,
        "Applies To Jurisdictions updated via governance metadata editor",
        "current-user@example.com",
        "current-user@example.com"
      )
      newGovernanceHistory.push({
        timestamp,
        action: "metadata_updated",
        userId: "current-user@example.com",
        previousValue: file.appliesToJurisdictions?.join(", "),
        newValue: editFormData.appliesToJurisdictions?.join(", ") || "",
        reason: "Applies To Jurisdictions updated",
      })
    }

    if (editFormData.supersededBy !== (file.supersededBy || file.replacedBy)) {
      addLog(
        editingFileId,
        file.name,
        "metadata_updated",
        "supersededBy",
        file.supersededBy || file.replacedBy,
        editFormData.supersededBy,
        "Superseded By updated via governance metadata editor",
        "current-user@example.com",
        "current-user@example.com"
      )
      newGovernanceHistory.push({
        timestamp,
        action: "metadata_updated",
        userId: "current-user@example.com",
        previousValue: file.supersededBy || file.replacedBy,
        newValue: editFormData.supersededBy || "",
        reason: "Superseded By updated",
      })
    }

    // Check if tags changed
    if (JSON.stringify(editFormData.tags) !== JSON.stringify(file.tags)) {
      addLog(
        editingFileId,
        file.name,
        "metadata_updated",
        "tags",
        file.tags,
        editFormData.tags,
        "Tags updated via governance metadata editor",
        "current-user@example.com",
        "current-user@example.com"
      )
      newGovernanceHistory.push({
        timestamp,
        action: "metadata_updated",
        userId: "current-user@example.com",
        previousValue: file.tags?.join(", "),
        newValue: editFormData.tags?.join(", ") || "",
        reason: "Tags updated",
      })
    }

    // Check if authority level changed (Human-in-the-loop override)
    if (editFormData.authorityLevel !== file.authorityLevel) {
      // Require rationale for authority level changes
      if (!editFormData.authorityLevelRationale?.trim()) {
        alert("Please provide a reason for overriding the authority level classification")
        return
      }
      
      addLog(
        editingFileId,
        file.name,
        "authority_changed",
        "authorityLevel",
        file.authorityLevel,
        editFormData.authorityLevel,
        editFormData.authorityLevelRationale,
        "current-user@example.com",
        "current-user@example.com"
      )
      newGovernanceHistory.push({
        timestamp,
        action: "authority_changed",
        userId: "current-user@example.com",
        previousValue: file.authorityLevel ? `Level ${file.authorityLevel}` : "unset",
        newValue: `Level ${editFormData.authorityLevel}`,
        reason: `Manual override: ${editFormData.authorityLevelRationale}`,
      })
    }

    setFiles((prevFiles) =>
      prevFiles.map((f) => {
        if (f.id === editingFileId) {
          const timestamp = new Date().toISOString()
          return {
            ...f,
            effectiveFrom: editFormData.effectiveFrom,
            effectiveTo: editFormData.effectiveTo,
            appliesToTaxYears: editFormData.appliesToTaxYears,
            appliesToJurisdictions: editFormData.appliesToJurisdictions,
            supersededBy: editFormData.supersededBy,
            // Update tags
            tags: editFormData.tags || f.tags,
            // Keep taxYear for backward compatibility if appliesToTaxYears has one value
            taxYear: editFormData.appliesToTaxYears && editFormData.appliesToTaxYears.length === 1
              ? editFormData.appliesToTaxYears[0]
              : f.taxYear,
            // Keep replacedBy for backward compatibility
            replacedBy: editFormData.supersededBy || f.replacedBy,
            // Update authority level if changed (Human-in-the-loop override)
            authorityLevel: editFormData.authorityLevel,
            authorityLevelRationale: editFormData.authorityLevel !== f.authorityLevel
              ? `${editFormData.authorityLevelRationale} (Manual override by current-user@example.com on ${timestamp})`
              : f.authorityLevelRationale,
            // Clear review flag when authority level is manually set (human has reviewed)
            needsHumanReview: editFormData.authorityLevel !== f.authorityLevel ? false : f.needsHumanReview,
            reviewedAt: editFormData.authorityLevel !== f.authorityLevel ? timestamp : f.reviewedAt,
            reviewedBy: editFormData.authorityLevel !== f.authorityLevel ? "current-user@example.com" : f.reviewedBy,
            // Add to governance history
            governanceHistory: [...(f.governanceHistory || []), ...newGovernanceHistory],
          }
        }
        return f
      })
    )

    setEditingFileId(null)
    setEditingFile(null)
    setEditFormData({})
  }

  const handleCancelEdit = () => {
    setEditingFileId(null)
    setEditingFile(null)
    setEditFormData({})
  }

  const toggleSelectAll = () => {
    if (selectedFiles.size === paginatedFiles.length) {
      setSelectedFiles(new Set())
    } else {
      setSelectedFiles(new Set(paginatedFiles.map((f) => f.id)))
    }
  }

  const handleBulkReCrawl = () => {
    const selectedIds = Array.from(selectedFiles)
    console.log("Re-crawling files:", selectedIds)
    // Update sync status to "syncing" for selected files
    setFiles((prevFiles) =>
      prevFiles.map((file) =>
        selectedIds.includes(file.id) && file.syncStatus !== "syncing"
          ? { ...file, syncStatus: "syncing" as const }
          : file
      )
    )
    setSelectedFiles(new Set())
    // In a real app, this would trigger an API call
  }

  const handleBulkReIndex = () => {
    const selectedIds = Array.from(selectedFiles)
    console.log("Re-indexing files:", selectedIds)
    // Update index status to "indexing" for selected files
    setFiles((prevFiles) =>
      prevFiles.map((file) =>
        selectedIds.includes(file.id) && file.indexStatus !== "indexing"
          ? { ...file, indexStatus: "indexing" as const }
          : file
      )
    )
    setSelectedFiles(new Set())
    // In a real app, this would trigger an API call
  }

  const handleBulkUnlinkFromKB = () => {
    const selectedIds = Array.from(selectedFiles)
    console.log("Unlinking files from KB:", selectedIds)
    // Remove KB mapping but keep the file
    setFiles((prevFiles) =>
      prevFiles.map((file) =>
        selectedIds.includes(file.id)
          ? { ...file, knowledgeBaseId: undefined, knowledgeBaseName: undefined }
          : file
      )
    )
    setSelectedFiles(new Set())
    // In a real app, this would trigger an API call to remove from search index
  }

  const handleBulkArchive = () => {
    const selectedIds = Array.from(selectedFiles)
    console.log("Archiving files:", selectedIds)
    // Remove archived files from the list (in a real app, they'd be moved to an archive)
    setFiles((prevFiles) => prevFiles.filter((file) => !selectedIds.includes(file.id)))
    setSelectedFiles(new Set())
    // In a real app, this would trigger an API call to archive
  }

  // Generate mock diff content for version comparison
  const generateDiffContent = (version1: File, version2: File) => {
    // Mock diff content - in production, this would fetch actual document content
    const mockContent1 = [
      "Form 1040 - U.S. Individual Income Tax Return",
      "Tax Year 2023",
      "",
      "Standard Deduction:",
      "Single: $13,850",
      "Married Filing Jointly: $27,700",
      "",
      "Tax Rates:",
      "10% on income up to $11,000",
      "12% on income $11,001 to $44,725",
      "22% on income $44,726 to $95,375",
    ]

    const mockContent2 = [
      "Form 1040 - U.S. Individual Income Tax Return",
      "Tax Year 2024",
      "",
      "Standard Deduction:",
      "Single: $14,600",
      "Married Filing Jointly: $29,200",
      "",
      "Tax Rates:",
      "10% on income up to $11,600",
      "12% on income $11,601 to $47,150",
      "22% on income $47,151 to $100,525",
    ]

    setDiffContent({
      version1: mockContent1,
      version2: mockContent2,
    })
  }

  // Helper function to get status display text
  const getStatusDisplay = (syncStatus: string, indexStatus: string): string => {
    const syncText = syncStatus === "synced" ? "Synced" : syncStatus === "syncing" ? "Syncing" : "Sync Failed"
    const indexText = 
      indexStatus === "indexed" ? "Indexed" : 
      indexStatus === "indexing" ? "Indexing..." : 
      indexStatus === "index_failed" ? "Index Failed" : 
      "Not Indexed"
    
    return `${syncText} · ${indexText}`
  }

  // Helper function to get status badge colors
  const getStatusBadgeClass = (syncStatus: string, indexStatus: string): string => {
    // If either status is failed, show red
    if (syncStatus === "sync_failed" || indexStatus === "index_failed") {
      return "bg-destructive/20 text-destructive cursor-pointer hover:bg-destructive/30"
    }
    // If syncing or indexing, show accent with pulse
    if (syncStatus === "syncing" || indexStatus === "indexing") {
      return "bg-accent/20 text-accent animate-pulse-glow"
    }
    // If both are complete, show green
    if (syncStatus === "synced" && indexStatus === "indexed") {
      return "bg-green-500/20 text-green-500"
    }
    // If synced but not indexed, show yellow
    if (syncStatus === "synced" && indexStatus === "not_indexed") {
      return "bg-yellow-500/20 text-yellow-500"
    }
    // Default
    return "bg-muted/50 text-muted-foreground"
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground mb-2">EL Cloud Files</h1>
        <p className="text-muted-foreground">Manage synchronized tax document files with tag-based organization</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value)
            setCurrentPage(1)
          }}
          placeholder="Search files..."
          className="w-80 pl-10 pr-4 py-2.5 rounded-lg bg-card border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
        />
        {searchQuery && (
          <button
            onClick={() => {
              setSearchQuery("")
              setCurrentPage(1)
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground hover:text-foreground transition-colors font-medium"
          >
            Clear
          </button>
        )}
      </div>

      {/* Knowledge Base Filter - Above Tag Filters */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-foreground font-semibold">
          <Filter size={18} /> Filters
        </div>
        
        {/* KB Filter Dropdown */}
        <div className="relative inline-block" ref={kbDropdownRef}>
          <label className="block text-xs font-semibold text-muted-foreground uppercase mb-2">Knowledge Base</label>
          <div className="relative">
            <button
              type="button"
              onClick={() => setKbDropdownOpen(!kbDropdownOpen)}
              className="px-4 py-2.5 rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary flex items-center justify-between hover:bg-muted/50 transition-colors min-w-[200px]"
            >
              <span className="text-sm">
                {KNOWLEDGE_BASES.find((kb) => kb.id === selectedKB)?.name || "All"}
              </span>
              <ChevronDown
                size={16}
                className={`text-muted-foreground transition-transform ${kbDropdownOpen ? "rotate-180" : ""}`}
              />
            </button>
            {kbDropdownOpen && (
              <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-xl overflow-hidden">
                {KNOWLEDGE_BASES.map((kb) => (
                  <button
                    key={kb.id}
                    onClick={() => {
                      setSelectedKB(kb.id)
                      setKbDropdownOpen(false)
                      setCurrentPage(1)
                    }}
                    className={`w-full px-4 py-2.5 text-left hover:bg-muted/50 transition-colors flex items-center justify-between text-sm border-b border-border last:border-b-0 ${
                      selectedKB === kb.id ? "bg-accent/10" : ""
                    }`}
                  >
                    <span className="text-foreground">{kb.name}</span>
                    {selectedKB === kb.id && <Check size={16} className="text-accent" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Tag Filter */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-foreground font-semibold">
            <Filter size={18} /> Tag Filter
          </div>
        <div className="space-y-4">
          {/* Jurisdiction Section */}
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase mb-2">Jurisdiction</p>
            <div className="flex flex-wrap gap-2">
              {sortedTags
                .filter((tag) => JURISDICTION_TAGS.includes(tag))
                .map((tag) => {
                  if (tag === "state") {
                    // Special handling for "state" tag - show dropdown
                    return (
                      <div key={tag} ref={stateDropdownRef} className="relative inline-block">
                        <button
                          onClick={() => {
                            setStateDropdownOpen(!stateDropdownOpen)
                            // Also toggle the "state" tag if not already selected
                            if (!selectedTags.includes(tag)) {
                              toggleTag(tag)
                            }
                          }}
                          className={`px-3 py-1 rounded-full text-sm font-medium transition-colors capitalize flex items-center gap-1.5 ${
                            selectedTags.includes(tag) || selectedStates.length > 0
                              ? "bg-accent text-accent-foreground"
                              : "bg-muted text-foreground hover:bg-muted/80"
                          }`}
                        >
                          {tag}
                          {(selectedTags.includes(tag) || selectedStates.length > 0) && " ✓"}
                          <ChevronDown 
                            size={14} 
                            className={`opacity-60 transition-transform duration-200 ${stateDropdownOpen ? "rotate-180" : ""}`}
                          />
                        </button>
                        
                        {stateDropdownOpen && (
                          <div className="absolute z-50 top-full left-0 mt-1.5 min-w-[200px] max-h-[300px] overflow-y-auto bg-card border border-border rounded-lg shadow-xl">
                            <div className="p-2">
                              <div className="flex items-center justify-between px-2 py-1.5 border-b border-border mb-1">
                                <button
                                  onClick={() => {
                                    setSelectedStates([])
                                    setCurrentPage(1)
                                  }}
                                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                                >
                                  Clear All
                                </button>
                                <button
                                  onClick={() => {
                                    setSelectedStates([...US_STATES])
                                    setCurrentPage(1)
                                  }}
                                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                                >
                                  Select All
                                </button>
                              </div>
                              <div className="space-y-1 max-h-[240px] overflow-y-auto">
                                {US_STATES.map((state) => {
                                  const isSelected = selectedStates.includes(state)
                                  return (
                                    <div
                                      key={state}
                                      onClick={() => {
                                        setSelectedStates((prev) => 
                                          prev.includes(state)
                                            ? prev.filter((s) => s !== state)
                                            : [...prev, state]
                                        )
                                        setCurrentPage(1)
                                      }}
                                      className={`flex items-center gap-2 px-2 py-1.5 text-sm cursor-pointer rounded hover:bg-muted/60 transition-colors ${
                                        isSelected ? "bg-accent/10" : ""
                                      }`}
                                    >
                                      <span className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                                        isSelected ? "bg-accent border-accent" : "border-border"
                                      }`}>
                                        {isSelected && <Check size={12} className="text-accent-foreground" />}
                                      </span>
                                      <span className={isSelected ? "font-medium text-foreground" : "text-foreground/80"}>
                                        {state}
                                      </span>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  } else {
                    // Regular tag button for "federal" and "local"
                    return (
                      <button
                        key={tag}
                        onClick={() => toggleTag(tag)}
                        className={`px-3 py-1 rounded-full text-sm font-medium transition-colors capitalize ${
                          selectedTags.includes(tag)
                            ? "bg-accent text-accent-foreground"
                            : "bg-muted text-foreground hover:bg-muted/80"
                        }`}
                      >
                        {tag}
                        {selectedTags.includes(tag) && " ✓"}
                      </button>
                    )
                  }
                })}
            </div>
            {/* Show selected states count if any are selected */}
            {selectedStates.length > 0 && (
              <div className="mt-2 text-xs text-muted-foreground">
                {selectedStates.length} state{selectedStates.length !== 1 ? 's' : ''} selected
              </div>
            )}
          </div>
        </div>

        {/* Authority Level Filter */}
        <div>
          <label className="block text-xs font-semibold text-muted-foreground uppercase mb-2">Authority Level</label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => {
                setSelectedAuthorityLevel("all")
                setCurrentPage(1)
              }}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                selectedAuthorityLevel === "all"
                  ? "bg-accent text-accent-foreground"
                  : "bg-muted text-foreground hover:bg-muted/80"
              }`}
            >
              All
            </button>
            {Object.entries(AUTHORITY_LEVELS).map(([level, info]) => (
              <button
                key={level}
                onClick={() => {
                  setSelectedAuthorityLevel(Number(level) as 1 | 2 | 3 | 4 | 5 | 6)
                  setCurrentPage(1)
                }}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                  selectedAuthorityLevel === Number(level)
                    ? `${info.color} border-current`
                    : "bg-muted text-foreground hover:bg-muted/80 border-border"
                }`}
                title={info.description}
              >
                Level {level}
              </button>
            ))}
          </div>
        </div>

        {/* Governance State Filter - Dropdown with Multi-Select */}
        <div>
          <label className="block text-xs font-semibold text-muted-foreground uppercase mb-2">Governance State</label>
          <div ref={governanceFilterDropdownRef} className="relative">
            <button
              onClick={() => setGovernanceFilterDropdownOpen(!governanceFilterDropdownOpen)}
              className="w-full px-4 py-2.5 rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-accent flex items-center justify-between hover:bg-muted/50 transition-colors"
            >
              <span className="text-sm flex items-center gap-2">
                <Filter size={16} className="text-muted-foreground" />
                {selectedGovernanceStates.length === 0 
                  ? "All States" 
                  : selectedGovernanceStates.length === 1
                    ? selectedGovernanceStates[0]
                    : `${selectedGovernanceStates.length} states selected`}
              </span>
              <ChevronDown
                size={16}
                className={`text-muted-foreground transition-transform ${governanceFilterDropdownOpen ? "rotate-180" : ""}`}
              />
            </button>
            {governanceFilterDropdownOpen && (
              <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-xl overflow-hidden">
                {/* Clear All / Select All */}
                <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
                  <button
                    onClick={() => {
                      setSelectedGovernanceStates([])
                      setCurrentPage(1)
                    }}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Clear All
                  </button>
                  <button
                    onClick={() => {
                      setSelectedGovernanceStates([...GOVERNANCE_STATES])
                      setCurrentPage(1)
                    }}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Select All
                  </button>
                </div>
                {GOVERNANCE_STATES.map((state) => {
                  const count = files.filter(f => f.governanceState === state).length
                  const isSelected = selectedGovernanceStates.includes(state)
                  return (
                    <div
                      key={state}
                      onClick={() => {
                        if (isSelected) {
                          setSelectedGovernanceStates(selectedGovernanceStates.filter(s => s !== state))
                        } else {
                          setSelectedGovernanceStates([...selectedGovernanceStates, state])
                        }
                        setCurrentPage(1)
                      }}
                      className={`px-4 py-2.5 hover:bg-muted/50 cursor-pointer transition-colors flex items-center justify-between text-sm border-b border-border last:border-b-0 ${
                        isSelected ? "bg-muted/30" : ""
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                          isSelected 
                            ? "bg-accent border-accent" 
                            : "border-border"
                        }`}>
                          {isSelected && <Check size={12} className="text-accent-foreground" />}
                        </div>
                        <span className={`${GOVERNANCE_STATE_STYLES[state].text}`}>{state}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${GOVERNANCE_STATE_STYLES[state].badge}`}>
                        {count}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Review Status Filter - Red Flag System */}
        <div>
          <label className="block text-xs font-semibold text-muted-foreground uppercase mb-2">AI Review Status</label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => {
                setSelectedReviewStatus("all")
                setCurrentPage(1)
              }}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                selectedReviewStatus === "all"
                  ? "bg-accent text-accent-foreground"
                  : "bg-muted text-foreground hover:bg-muted/80"
              }`}
            >
              All
            </button>
            <button
              onClick={() => {
                setSelectedReviewStatus("needs_review")
                setCurrentPage(1)
              }}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border flex items-center gap-1.5 ${
                selectedReviewStatus === "needs_review"
                  ? "bg-red-500/20 text-red-600 border-red-500/30"
                  : "bg-muted text-foreground hover:bg-muted/80 border-border"
              }`}
            >
              <AlertTriangle size={14} />
              Needs Review
            </button>
            <button
              onClick={() => {
                setSelectedReviewStatus("reviewed")
                setCurrentPage(1)
              }}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border flex items-center gap-1.5 ${
                selectedReviewStatus === "reviewed"
                  ? "bg-green-500/20 text-green-600 border-green-500/30"
                  : "bg-muted text-foreground hover:bg-muted/80 border-border"
              }`}
            >
              <CheckCircle2 size={14} />
              Reviewed
            </button>
          </div>
        </div>

        {(selectedTags.length > 0 || selectedKB !== "all" || selectedAuthorityLevel !== "all" || selectedGovernanceStates.length > 0 || selectedReviewStatus !== "all" || selectedStates.length > 0) && (
          <button
            onClick={() => {
              setSelectedTags([])
              setSelectedKB("all")
              setSelectedAuthorityLevel("all")
              setSelectedGovernanceStates([])
              setSelectedReviewStatus("all")
              setSelectedStates([])
            }}
            className="text-sm text-muted-foreground hover:text-foreground underline"
          >
            Clear all filters
          </button>
        )}
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Showing {startIndex + 1}-{Math.min(endIndex, filteredFiles.length)} of {filteredFiles.length} files
        </span>
      </div>

      {/* Bulk Actions Toolbar */}
      {selectedFiles.size > 0 && (
        <div className="p-4 rounded-lg bg-accent/10 border border-accent/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-foreground">
              {selectedFiles.size} file{selectedFiles.size !== 1 ? "s" : ""} selected
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleBulkReCrawl}
              className="px-3 py-1.5 rounded-lg bg-card border border-border text-foreground hover:bg-muted/50 transition-colors flex items-center gap-2 text-sm font-medium"
              title="Re-crawl selected files from their source URLs"
            >
              <RefreshCw size={16} />
              Re-crawl selected
            </button>
            <button
              onClick={handleBulkReIndex}
              className="px-3 py-1.5 rounded-lg bg-card border border-border text-foreground hover:bg-muted/50 transition-colors flex items-center gap-2 text-sm font-medium"
              title="Re-index selected files (chunk, embed, add to vector DB)"
            >
              <Database size={16} />
              Re-index selected
            </button>
            <button
              onClick={handleBulkUnlinkFromKB}
              className="px-3 py-1.5 rounded-lg bg-card border border-border text-foreground hover:bg-muted/50 transition-colors flex items-center gap-2 text-sm font-medium"
              title="Remove selected files from Knowledge Base search (keep files)"
            >
              <Unlink size={16} />
              Unlink from KB
            </button>
            <button
              onClick={handleBulkArchive}
              className="px-3 py-1.5 rounded-lg bg-card border border-border text-foreground hover:bg-muted/50 transition-colors flex items-center gap-2 text-sm font-medium"
              title="Archive older versions of selected files"
            >
              <Archive size={16} />
              Archive older versions
            </button>
            <button
              onClick={() => setSelectedFiles(new Set())}
              className="px-3 py-1.5 rounded-lg bg-muted/50 text-muted-foreground hover:bg-muted transition-colors text-sm font-medium"
            >
              Clear selection
            </button>
          </div>
        </div>
      )}

      {/* Files List */}
      <div className="space-y-3">
        {/* Select All Checkbox */}
        {paginatedFiles.length > 0 && (
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <input
              type="checkbox"
              checked={selectedFiles.size === paginatedFiles.length && paginatedFiles.length > 0}
              onChange={toggleSelectAll}
              className="w-4 h-4 rounded border-border text-accent focus:ring-accent focus:ring-2 cursor-pointer"
            />
            <label className="text-sm font-medium text-foreground cursor-pointer">
              Select all ({paginatedFiles.length} files on this page)
            </label>
          </div>
        )}
        
        {paginatedFiles.map((file) => (
          <div
            key={file.id}
            className={`p-4 rounded-lg bg-card border transition-colors ${
              selectedFiles.has(file.id)
                ? "border-accent bg-accent/5 hover:border-accent/80"
                : "border-border hover:border-primary/30"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4 flex-1">
                <div className="flex items-start gap-3 mt-1">
                  <input
                    type="checkbox"
                    checked={selectedFiles.has(file.id)}
                    onChange={() => toggleFileSelection(file.id)}
                    className="w-4 h-4 rounded border-border text-accent focus:ring-accent focus:ring-2 cursor-pointer mt-1"
                  />
                  <FileText size={24} className="text-accent" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="text-foreground font-semibold">{file.name}</h3>
                    {file.hasNewerVersion && (
                      <div 
                        className="group relative"
                        title="A newer version of this document exists from the same source URL"
                      >
                        <AlertTriangle 
                          size={16} 
                          className="text-yellow-500 cursor-help" 
                        />
                      </div>
                    )}
                    {file.authorityLevel && (
                      <div
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${
                          AUTHORITY_LEVELS[file.authorityLevel].color
                        }`}
                        title={AUTHORITY_LEVELS[file.authorityLevel].description}
                      >
                        <span className={`w-2 h-2 rounded-full ${AUTHORITY_LEVELS[file.authorityLevel].badgeColor}`}></span>
                        <span>Authority: {AUTHORITY_LEVELS[file.authorityLevel].label}</span>
                      </div>
                    )}
                    {/* Citability Badge */}
                    {computeCitability(file).isCitable ? (
                      <span 
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-500/20 text-green-600 border border-green-500/30"
                        title="Citable in RAG Answers - Click Info for details"
                      >
                        <CheckCircle2 size={12} />
                        Citable
                      </span>
                    ) : (
                      <span 
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-500/20 text-gray-500 border border-gray-500/30"
                        title="Not citable in RAG Answers - Click Info for details"
                      >
                        <XCircle size={12} />
                        Not Citable
                      </span>
                    )}
                    {/* Red Flag - Needs Human Review */}
                    {file.needsHumanReview && (
                      <div 
                        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold bg-red-500/20 text-red-600 border border-red-500/30 cursor-pointer hover:bg-red-500/30 transition-colors animate-pulse"
                        title={file.reviewReason || "AI classification needs human review"}
                        onClick={() => handleEditFile(file)}
                      >
                        <AlertTriangle size={12} />
                        Needs Review
                        {file.classificationConfidence !== undefined && (
                          <span className="text-red-500">({file.classificationConfidence}%)</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground mb-2">
                    <span>{file.size}</span>
                    <span>{file.uploadedDate}</span>
                  </div>
                  
                  {/* Tax Year Applicability Section - PRIMARY VALIDITY */}
                  {(file.taxYear || file.appliesToTaxYears || file.effectiveFrom || file.effectiveTo || file.appliesToJurisdictions || file.replacedBy || file.supersededBy) && (
                    <div className="mb-3 p-2.5 rounded-lg bg-accent/5 border border-accent/20">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-accent uppercase">Tax Year Applicability</span>
                        <button
                          onClick={() => handleEditFile(file)}
                          className="p-1 rounded hover:bg-muted/50 transition-colors"
                          title="Edit governance metadata"
                        >
                          <Edit2 size={12} className="text-muted-foreground" />
                        </button>
                      </div>
                      <div className="space-y-2 text-xs">
                        {/* Tax Years - PRIMARY VALIDITY INDICATOR */}
                        {(file.appliesToTaxYears && file.appliesToTaxYears.length > 0) || file.taxYear ? (
                          <div className="flex items-center gap-1.5">
                            <Calendar size={12} className="text-accent" />
                            <span className="text-muted-foreground font-medium">Tax Years:</span>
                            <span className="px-2 py-0.5 rounded text-xs font-bold bg-accent/20 text-accent border border-accent/30">
                              {formatTaxYears(file.appliesToTaxYears, file.taxYear)}
                            </span>
                          </div>
                        ) : null}
                        
                        {/* Applies To Jurisdictions */}
                        {file.appliesToJurisdictions && file.appliesToJurisdictions.length > 0 && (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-muted-foreground font-medium">Jurisdictions:</span>
                            <div className="flex flex-wrap gap-1.5">
                              {file.appliesToJurisdictions.map((jurisdiction) => (
                                <span
                                  key={jurisdiction}
                                  className="px-2 py-0.5 rounded-full text-xs bg-primary/20 text-primary border border-primary/30"
                                >
                                  {jurisdiction === "federal" ? "Federal" : jurisdiction === "state" ? "State" : jurisdiction === "local" ? "Local" : jurisdiction}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Revision Metadata - SECONDARY (not validity) */}
                        {(file.effectiveFrom || file.effectiveTo) && (
                          <div className="flex flex-wrap items-center gap-3 pt-1.5 mt-1.5 border-t border-border/30">
                            <span className="text-muted-foreground/70 text-[10px] uppercase">Revision:</span>
                            {file.effectiveFrom && (
                              <span className="text-muted-foreground text-[11px]">
                                Published {formatEffectiveDate(file.effectiveFrom)}
                              </span>
                            )}
                            {file.effectiveTo && (
                              <span className="text-muted-foreground text-[11px]">
                                - Ends {formatEffectiveDate(file.effectiveTo)}
                              </span>
                            )}
                          </div>
                        )}
                        
                        {/* Superseded By / Replaced By */}
                        {(file.supersededBy || file.replacedBy) && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-muted-foreground font-medium">
                              {file.supersededBy ? "Superseded by:" : "Replaced by:"}
                            </span>
                            <span className="text-accent hover:underline cursor-pointer">
                              {file.supersededBy || file.replacedBy}
                            </span>
                          </div>
                        )}
                      </div>
                      {/* Compare Versions Button */}
                      {(file.replacedBy || file.supersededBy || file.hasNewerVersion) && (
                        <div className="mt-2 pt-2 border-t border-border/50">
                          <button
                            onClick={() => {
                              setSelectedVersion1(file)
                              // Find the replacedBy file or create a mock newer version
                              const newerVersion = files.find(f => f.name === file.replacedBy) || {
                                ...file,
                                id: `new-${file.id}`,
                                name: file.replacedBy || file.name.replace(/\d{4}/, String((file.taxYear || 2024) + 1)),
                                taxYear: (file.taxYear || 2024) + 1,
                              }
                              setSelectedVersion2(newerVersion)
                              generateDiffContent(file, newerVersion)
                              setVersionDiffModalOpen(true)
                            }}
                            className="w-full px-3 py-1.5 rounded-lg bg-accent/10 text-accent hover:bg-accent/20 transition-colors flex items-center justify-center gap-2 text-xs font-medium"
                          >
                            <GitCompare size={14} />
                            Compare Versions
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Source URL Display */}
                  {file.sourceUrl && (
                    <div className="mb-3">
                      <a
                        href={file.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-accent transition-colors group"
                        title={file.sourceUrl}
                      >
                        <Globe size={14} className="text-accent/70 group-hover:text-accent" />
                        <span className="max-w-md truncate">
                          {formatSourcePath(file.sourceUrl)}
                        </span>
                        <ExternalLink size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                      </a>
                      {file.sourceDomain && (
                        <div className="mt-1">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-muted/50 text-muted-foreground border border-border/50">
                            <Globe size={10} />
                            {file.sourceDomain}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Knowledge Base Badge */}
                  {file.knowledgeBaseName && (
                    <div className="mb-2">
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-500/20 text-blue-500 border border-blue-500/30 font-medium">
                        <FileText size={10} />
                        KB: {file.knowledgeBaseName}
                      </span>
                    </div>
                  )}
                  
                  <div className="flex flex-wrap gap-2">
                    {file.tags.map((tag) => (
                      <span key={tag} className="px-2 py-1 rounded-full text-xs bg-primary/20 text-primary">
                        {tag}
                      </span>
                    ))}
                  </div>
                  
                  {/* RAG Pipeline Visibility - Collapsible Section */}
                  {(file.lastCrawled || file.chunkCount !== undefined || file.embeddingModel || file.tokensIndexed !== undefined) && (
                    <div className="mt-4 border-t border-border pt-3">
                      <button
                        onClick={() => toggleRagVisibility(file.id)}
                        className="w-full flex items-center justify-between text-sm font-semibold text-foreground hover:text-accent transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Database size={16} className="text-accent" />
                          <span>RAG Pipeline Details</span>
                        </div>
                        {expandedRagFiles.has(file.id) ? (
                          <ChevronUp size={16} className="text-muted-foreground" />
                        ) : (
                          <ChevronDown size={16} className="text-muted-foreground" />
                        )}
                      </button>
                      
                      {expandedRagFiles.has(file.id) && (
                        <div className="mt-3 p-3 rounded-lg bg-muted/20 border border-border/50 space-y-2.5">
                          {file.lastCrawled && (
                            <div className="flex items-start justify-between text-xs">
                              <span className="text-muted-foreground font-medium">Last crawled:</span>
                              <span className="text-foreground font-mono">{file.lastCrawled}</span>
                            </div>
                          )}
                          {file.chunkCount !== undefined && (
                            <div className="flex items-start justify-between text-xs">
                              <span className="text-muted-foreground font-medium">Chunk count:</span>
                              <span className="text-foreground font-semibold">{file.chunkCount.toLocaleString()} chunks</span>
                            </div>
                          )}
                          {file.embeddingModel && (
                            <div className="flex items-start justify-between text-xs">
                              <span className="text-muted-foreground font-medium">Embedding model:</span>
                              <div className="flex items-center gap-1.5">
                                <Cpu size={12} className="text-accent" />
                                <span className="text-foreground font-mono">{file.embeddingModel}</span>
                              </div>
                            </div>
                          )}
                          {file.tokensIndexed !== undefined && (
                            <div className="flex items-start justify-between text-xs">
                              <span className="text-muted-foreground font-medium">Tokens indexed:</span>
                              <span className="text-foreground font-semibold">~{file.tokensIndexed.toLocaleString()} tokens</span>
                            </div>
                          )}
                          {file.ragErrors !== undefined && (
                            <div className="flex items-start justify-between text-xs">
                              <span className="text-muted-foreground font-medium">Errors:</span>
                              <span className={`font-medium ${
                                file.ragErrors === "0" ? "text-green-500" : "text-yellow-500"
                              }`}>
                                {file.ragErrors}
                              </span>
                            </div>
                          )}
                          {file.lastEmbedded && (
                            <div className="flex items-start justify-between text-xs">
                              <span className="text-muted-foreground font-medium">Last embedded:</span>
                              <span className="text-foreground font-mono">{file.lastEmbedded}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                {/* Governance State Badge with Dropdown */}
                <div
                  ref={(el) => {
                    governanceStateDropdownRef.current[file.id] = el
                  }}
                  className="relative"
                >
                  <button
                    onClick={() => {
                      setGovernanceStateDropdownOpen((prev) => ({
                        ...prev,
                        [file.id]: !prev[file.id],
                      }))
                    }}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors flex items-center gap-1.5 border ${
                      getGovernanceStateBadgeClass(file.governanceState)
                    }`}
                    title="Click to change governance state"
                  >
                    <span>{file.governanceState || "Draft"}</span>
                    <ChevronDown
                      size={12}
                      className={`transition-transform ${governanceStateDropdownOpen[file.id] ? "rotate-180" : ""}`}
                    />
                  </button>
                  {governanceStateDropdownOpen[file.id] && (
                    <div className="absolute z-50 top-full left-0 mt-1.5 min-w-[160px] bg-card border border-border rounded-lg shadow-xl overflow-hidden animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-150">
                      <div className="py-1">
                        {GOVERNANCE_STATES.map((state) => (
                          <button
                            key={state}
                            onClick={() => updateGovernanceState(file.id, state)}
                            className={`w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium transition-colors ${
                              file.governanceState === state
                                ? `${GOVERNANCE_STATE_STYLES[state].badge}`
                                : "text-foreground/80 hover:bg-muted/60"
                            }`}
                          >
                            <span>{state}</span>
                            {file.governanceState === state && <Check size={14} className="ml-auto" />}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Dual Status Badge */}
                <button
                  onClick={() => {
                    if (file.syncStatus === "sync_failed" || file.indexStatus === "index_failed") {
                      setErrorDetailsFile(file)
                    }
                  }}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                    getStatusBadgeClass(file.syncStatus, file.indexStatus)
                  }`}
                  title={
                    file.syncStatus === "sync_failed" || file.indexStatus === "index_failed"
                      ? "Click to view error details"
                      : undefined
                  }
                >
                  {(file.syncStatus === "syncing" || file.indexStatus === "indexing") && (
                    <span className="animate-spin">⟳</span>
                  )}
                  {(file.syncStatus === "sync_failed" || file.indexStatus === "index_failed") && (
                    <AlertCircle size={12} />
                  )}
                  <span>{getStatusDisplay(file.syncStatus, file.indexStatus)}</span>
                </button>
                <button
                  onClick={() => setDetailsFile(file)}
                  className="p-2 rounded-lg hover:bg-muted/50 transition-colors"
                  title="View governance details"
                >
                  <Info size={18} className="text-muted-foreground" />
                </button>
                <button className="p-2 rounded-lg hover:bg-muted/50 transition-colors">
                  <Download size={18} className="text-muted-foreground" />
                </button>
                <button
                  onClick={() => deleteFile(file.id)}
                  className="p-2 rounded-lg hover:bg-destructive/20 transition-colors"
                >
                  <Trash2 size={18} className="text-destructive" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
            className="p-2 rounded-lg bg-card border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft size={20} />
          </button>
          <div className="flex items-center gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => goToPage(page)}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  currentPage === page
                    ? "bg-accent text-accent-foreground"
                    : "bg-card border border-border hover:bg-muted text-foreground"
                }`}
              >
                {page}
              </button>
            ))}
          </div>
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="p-2 rounded-lg bg-card border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      )}

      {/* Error Details Modal */}
      {errorDetailsFile && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-xl max-w-2xl w-full p-6 shadow-2xl animate-in fade-in-0 zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <AlertCircle size={20} className="text-destructive" />
                Error Details
              </h2>
              <button
                onClick={() => setErrorDetailsFile(null)}
                className="p-1 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <X size={20} className="text-muted-foreground" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-2">{errorDetailsFile.name}</h3>
                <div className="text-xs text-muted-foreground mb-4">
                  {errorDetailsFile.sourceUrl && (
                    <div className="flex items-center gap-1">
                      <Globe size={12} />
                      <span className="truncate">{errorDetailsFile.sourceUrl}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Sync Error */}
              {errorDetailsFile.syncStatus === "sync_failed" && errorDetailsFile.syncError && (
                <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle size={16} className="text-destructive" />
                    <span className="text-sm font-semibold text-destructive">Sync Failed</span>
                  </div>
                  <p className="text-sm text-foreground">{errorDetailsFile.syncError}</p>
                  <div className="mt-3 text-xs text-muted-foreground">
                    <p className="font-medium mb-1">What this means:</p>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                      <li>The file could not be downloaded from the source URL</li>
                      <li>The file was not added to local storage</li>
                      <li>Indexing cannot proceed until sync is successful</li>
                    </ul>
                  </div>
                </div>
              )}

              {/* Index Error */}
              {errorDetailsFile.indexStatus === "index_failed" && errorDetailsFile.indexError && (
                <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle size={16} className="text-destructive" />
                    <span className="text-sm font-semibold text-destructive">Index Failed</span>
                  </div>
                  <p className="text-sm text-foreground">{errorDetailsFile.indexError}</p>
                  <div className="mt-3 text-xs text-muted-foreground">
                    <p className="font-medium mb-1">What this means:</p>
                    <ul className="list-disc list-inside space-y-1 ml-2">
                      <li>The file was downloaded but could not be processed</li>
                      <li>One or more steps failed: Chunking, Embedding, Vector DB insertion, KB mapping, OCR, or Validation</li>
                      <li>The file is not searchable in the Knowledge Base</li>
                    </ul>
                    <div className="mt-2 pt-2 border-t border-border/50">
                      <p className="font-medium mb-1">Indexing process includes:</p>
                      <ul className="list-disc list-inside space-y-1 ml-2">
                        <li>Chunking - Breaking document into searchable pieces</li>
                        <li>Embedding - Converting text to vector representations</li>
                        <li>Vector DB - Storing embeddings for semantic search</li>
                        <li>KB Mapping - Adding to Knowledge Base collections</li>
                        <li>OCR - Optical Character Recognition (if needed)</li>
                        <li>Validation - Quality checks and verification</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Status Summary */}
              <div className="p-4 rounded-lg bg-muted/30 border border-border">
                <p className="text-xs font-semibold text-muted-foreground uppercase mb-2">Current Status</p>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-foreground">Governance State:</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                      getGovernanceStateBadgeClass(errorDetailsFile.governanceState)
                    }`}>
                      {errorDetailsFile.governanceState || "Draft"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-foreground">Sync Status:</span>
                    <span className={`font-semibold ${
                      errorDetailsFile.syncStatus === "synced" ? "text-green-500" :
                      errorDetailsFile.syncStatus === "syncing" ? "text-accent" :
                      "text-destructive"
                    }`}>
                      {errorDetailsFile.syncStatus === "synced" ? "Synced" :
                       errorDetailsFile.syncStatus === "syncing" ? "Syncing" :
                       "Sync Failed"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-foreground">Index Status:</span>
                    <span className={`font-semibold ${
                      errorDetailsFile.indexStatus === "indexed" ? "text-green-500" :
                      errorDetailsFile.indexStatus === "indexing" ? "text-accent" :
                      errorDetailsFile.indexStatus === "index_failed" ? "text-destructive" :
                      "text-yellow-500"
                    }`}>
                      {errorDetailsFile.indexStatus === "indexed" ? "Indexed" :
                       errorDetailsFile.indexStatus === "indexing" ? "Indexing..." :
                       errorDetailsFile.indexStatus === "index_failed" ? "Index Failed" :
                       "Not Indexed"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => setErrorDetailsFile(null)}
              className="mt-6 w-full px-4 py-2.5 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:bg-accent/90 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Version Diff Modal */}
      {versionDiffModalOpen && selectedVersion1 && selectedVersion2 && diffContent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-lg w-full max-w-7xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <GitCompare size={24} className="text-accent" />
                <div>
                  <h2 className="text-xl font-bold text-foreground">Version Comparison</h2>
                  <p className="text-sm text-muted-foreground">
                    Compare document versions to see changes over time
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setVersionDiffModalOpen(false)
                  setSelectedVersion1(null)
                  setSelectedVersion2(null)
                  setDiffContent(null)
                }}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <X size={20} className="text-muted-foreground" />
              </button>
            </div>

            {/* File Metadata */}
            <div className="p-4 border-b border-border bg-muted/30 grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Version 1 (Older)</p>
                <p className="text-sm font-semibold text-foreground">{selectedVersion1.name}</p>
                <div className="flex items-center gap-3 mt-1">
                  {selectedVersion1.taxYear && (
                    <span className="text-xs text-muted-foreground">Tax Year: {selectedVersion1.taxYear}</span>
                  )}
                  {selectedVersion1.effectiveFrom && (
                    <span className="text-xs text-muted-foreground">Effective: {selectedVersion1.effectiveFrom}</span>
                  )}
                  {selectedVersion1.authorityLevel && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-600">
                      Level {selectedVersion1.authorityLevel}
                    </span>
                  )}
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Version 2 (Newer)</p>
                <p className="text-sm font-semibold text-foreground">{selectedVersion2.name}</p>
                <div className="flex items-center gap-3 mt-1">
                  {selectedVersion2.taxYear && (
                    <span className="text-xs text-muted-foreground">Tax Year: {selectedVersion2.taxYear}</span>
                  )}
                  {selectedVersion2.effectiveFrom && (
                    <span className="text-xs text-muted-foreground">Effective: {selectedVersion2.effectiveFrom}</span>
                  )}
                  {selectedVersion2.authorityLevel && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-600">
                      Level {selectedVersion2.authorityLevel}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Diff Content - Side by Side */}
            <div className="flex-1 overflow-auto p-6">
              <div className="grid grid-cols-2 gap-4">
                {/* Version 1 */}
                <div className="border border-border rounded-lg overflow-hidden">
                  <div className="bg-muted/50 p-2 border-b border-border">
                    <p className="text-xs font-semibold text-foreground">{selectedVersion1.name}</p>
                  </div>
                  <div className="p-4 bg-card font-mono text-xs">
                    {diffContent.version1.map((line, index) => {
                      const correspondingLine = diffContent.version2[index]
                      const isChanged = line !== correspondingLine && correspondingLine !== undefined
                      const isDeleted = correspondingLine === undefined
                      
                      return (
                        <div
                          key={index}
                          className={`flex items-start gap-2 ${
                            isChanged || isDeleted ? "bg-yellow-500/20" : ""
                          }`}
                        >
                          <span className="text-muted-foreground w-8 text-right select-none">
                            {index + 1}
                          </span>
                          <span className={isDeleted ? "line-through text-destructive" : ""}>
                            {line || <span className="text-muted-foreground">(empty line)</span>}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Version 2 */}
                <div className="border border-border rounded-lg overflow-hidden">
                  <div className="bg-muted/50 p-2 border-b border-border">
                    <p className="text-xs font-semibold text-foreground">{selectedVersion2.name}</p>
                  </div>
                  <div className="p-4 bg-card font-mono text-xs">
                    {diffContent.version2.map((line, index) => {
                      const correspondingLine = diffContent.version1[index]
                      const isChanged = line !== correspondingLine && correspondingLine !== undefined
                      const isAdded = correspondingLine === undefined
                      
                      return (
                        <div
                          key={index}
                          className={`flex items-start gap-2 ${
                            isChanged || isAdded ? "bg-green-500/20" : ""
                          }`}
                        >
                          <span className="text-muted-foreground w-8 text-right select-none">
                            {index + 1}
                          </span>
                          <span className={isAdded ? "text-green-600 font-semibold" : ""}>
                            {line || <span className="text-muted-foreground">(empty line)</span>}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-border flex items-center justify-end gap-2">
              <button
                onClick={() => {
                  setVersionDiffModalOpen(false)
                  setSelectedVersion1(null)
                  setSelectedVersion2(null)
                  setDiffContent(null)
                }}
                className="px-4 py-2 rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 transition-colors text-sm font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Governance Metadata Edit Modal */}
      {editingFile && editingFileId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-xl max-w-2xl w-full p-6 shadow-2xl animate-in fade-in-0 zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <Edit2 size={20} className="text-accent" />
                Edit Governance Metadata
              </h2>
              <button
                onClick={handleCancelEdit}
                className="p-1 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <X size={20} className="text-muted-foreground" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-2">{editingFile.name}</h3>
              </div>

              {/* Tax Year Applicability - PRIMARY VALIDITY */}
              <div className="p-3 rounded-lg bg-accent/5 border border-accent/20">
                <h4 className="text-xs font-semibold text-accent uppercase mb-3 flex items-center gap-2">
                  <Calendar size={14} />
                  Tax Year Applicability (Primary Validity)
                </h4>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Applies To Tax Years (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={editFormData.appliesToTaxYears?.join(", ") || ""}
                    onChange={(e) => {
                      const values = e.target.value
                        .split(",")
                        .map((v) => parseInt(v.trim()))
                        .filter((v) => !isNaN(v))
                      setEditFormData((prev) => ({ ...prev, appliesToTaxYears: values.length > 0 ? values : undefined }))
                    }}
                    placeholder="e.g., 2023, 2024, 2025"
                    className="w-full px-3 py-2 rounded-lg bg-input border border-accent/30 text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                  <p className="text-xs text-accent/70 mt-1">
                    This is the PRIMARY validity axis - determines which tax years this document applies to
                  </p>
                </div>
              </div>

              {/* Revision Metadata - SECONDARY (not validity) */}
              <div className="p-3 rounded-lg bg-muted/30 border border-border/50">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-3">
                  Revision Metadata (Not Validity)
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Published Date
                    </label>
                    <input
                      type="date"
                      value={editFormData.effectiveFrom || ""}
                      onChange={(e) =>
                        setEditFormData((prev) => ({ ...prev, effectiveFrom: e.target.value }))
                      }
                      className="w-full px-3 py-2 rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <p className="text-xs text-muted-foreground mt-1">When this revision was published</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Revision End Date
                    </label>
                    <input
                      type="date"
                      value={editFormData.effectiveTo || ""}
                      onChange={(e) =>
                        setEditFormData((prev) => ({ ...prev, effectiveTo: e.target.value }))
                      }
                      className="w-full px-3 py-2 rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    {editFormData.effectiveFrom && editFormData.effectiveTo && !validateDateRange(editFormData.effectiveFrom, editFormData.effectiveTo) && (
                      <p className="text-xs text-destructive mt-1">End date must be after Published date</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">When this revision ended (optional)</p>
                  </div>
                </div>
              </div>

              {/* Applies To Jurisdictions */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Applies To Jurisdictions
                </label>
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    {JURISDICTION_TAGS.map((jurisdiction) => (
                      <button
                        key={jurisdiction}
                        type="button"
                        onClick={() => {
                          const current = editFormData.appliesToJurisdictions || []
                          const newJurisdictions = current.includes(jurisdiction)
                            ? current.filter((j) => j !== jurisdiction)
                            : [...current, jurisdiction]
                          setEditFormData((prev) => ({
                            ...prev,
                            appliesToJurisdictions: newJurisdictions.length > 0 ? newJurisdictions : undefined,
                          }))
                        }}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                          editFormData.appliesToJurisdictions?.includes(jurisdiction)
                            ? "bg-accent text-accent-foreground"
                            : "bg-muted text-foreground hover:bg-muted/80"
                        }`}
                      >
                        {jurisdiction.charAt(0).toUpperCase() + jurisdiction.slice(1)}
                        {editFormData.appliesToJurisdictions?.includes(jurisdiction) && " ✓"}
                      </button>
                    ))}
                  </div>
                  {editFormData.appliesToJurisdictions && editFormData.appliesToJurisdictions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {editFormData.appliesToJurisdictions.map((jurisdiction) => (
                        <span
                          key={jurisdiction}
                          className="px-2 py-0.5 rounded-full text-xs bg-primary/20 text-primary border border-primary/30"
                        >
                          {jurisdiction === "federal" ? "Federal" : jurisdiction === "state" ? "State" : jurisdiction === "local" ? "Local" : jurisdiction}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Superseded By */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Superseded By
                </label>
                <input
                  type="text"
                  value={editFormData.supersededBy || ""}
                  onChange={(e) =>
                    setEditFormData((prev) => ({
                      ...prev,
                      supersededBy: e.target.value || undefined,
                    }))
                  }
                  placeholder="Document name or ID that supersedes this document"
                  className="w-full px-3 py-2 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Enter the name or ID of the document that supersedes this one
                </p>
              </div>

              {/* Tags Editing */}
              <div className="p-3 rounded-lg bg-purple-500/5 border border-purple-500/20">
                <h4 className="text-xs font-semibold text-purple-600 uppercase mb-3 flex items-center gap-2">
                  <Filter size={14} />
                  Document Tags
                </h4>
                <div className="space-y-3">
                  {/* Current Tags */}
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">Current Tags</label>
                    <div className="flex flex-wrap gap-2 min-h-[32px]">
                      {editFormData.tags && editFormData.tags.length > 0 ? (
                        editFormData.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-1 rounded-lg text-xs font-medium bg-purple-500/20 text-purple-600 border border-purple-500/30 flex items-center gap-1"
                          >
                            {tag}
                            <button
                              type="button"
                              onClick={() => {
                                setEditFormData((prev) => ({
                                  ...prev,
                                  tags: prev.tags?.filter((t) => t !== tag) || [],
                                }))
                              }}
                              className="ml-1 hover:text-destructive transition-colors"
                            >
                              <X size={12} />
                            </button>
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground italic">No tags</span>
                      )}
                    </div>
                  </div>

                  {/* Add Tag */}
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">Add New Tag</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && tagInput.trim()) {
                            e.preventDefault()
                            const newTag = tagInput.trim().toLowerCase()
                            if (!editFormData.tags?.includes(newTag)) {
                              setEditFormData((prev) => ({
                                ...prev,
                                tags: [...(prev.tags || []), newTag],
                              }))
                            }
                            setTagInput("")
                          }
                        }}
                        placeholder="Type a tag and press Enter"
                        className="flex-1 px-3 py-2 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          if (tagInput.trim()) {
                            const newTag = tagInput.trim().toLowerCase()
                            if (!editFormData.tags?.includes(newTag)) {
                              setEditFormData((prev) => ({
                                ...prev,
                                tags: [...(prev.tags || []), newTag],
                              }))
                            }
                            setTagInput("")
                          }
                        }}
                        className="px-3 py-2 rounded-lg bg-purple-500/20 text-purple-600 hover:bg-purple-500/30 transition-colors text-sm font-medium"
                      >
                        Add
                      </button>
                    </div>
                  </div>

                  {/* Tag Suggestions */}
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-2">Quick Add (Click to Add)</label>
                    <div className="flex flex-wrap gap-1.5">
                      {allTags
                        .filter((tag) => !editFormData.tags?.includes(tag))
                        .slice(0, 10)
                        .map((tag) => (
                          <button
                            key={tag}
                            type="button"
                            onClick={() => {
                              setEditFormData((prev) => ({
                                ...prev,
                                tags: [...(prev.tags || []), tag],
                              }))
                            }}
                            className="px-2 py-1 rounded text-xs font-medium bg-muted text-muted-foreground hover:bg-purple-500/20 hover:text-purple-600 transition-colors border border-border hover:border-purple-500/30"
                          >
                            + {tag}
                          </button>
                        ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

              {/* Authority Level Override - Human-in-the-loop */}
              <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                <h4 className="text-xs font-semibold text-blue-600 uppercase mb-3 flex items-center gap-2">
                  <FileCheck size={14} />
                  Authority Level Override (Human-in-the-loop)
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Authority Level
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(AUTHORITY_LEVELS).map(([level, info]) => (
                        <button
                          key={level}
                          type="button"
                          onClick={() => setEditFormData(prev => ({ 
                            ...prev, 
                            authorityLevel: Number(level) as 1 | 2 | 3 | 4 | 5 | 6 
                          }))}
                          className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors border ${
                            editFormData.authorityLevel === Number(level)
                              ? `${info.color} border-current ring-2 ring-offset-1`
                              : "bg-muted text-foreground hover:bg-muted/80 border-border"
                          }`}
                          title={info.description}
                        >
                          Level {level}
                        </button>
                      ))}
                    </div>
                    {editFormData.authorityLevel !== editingFile?.authorityLevel && (
                      <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                        <AlertTriangle size={12} />
                        Changing from Level {editingFile?.authorityLevel || "unset"} to Level {editFormData.authorityLevel}
                      </p>
                    )}
                  </div>
                  
                  {editFormData.authorityLevel !== editingFile?.authorityLevel && (
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-2">
                        Reason for Override <span className="text-destructive">*</span>
                      </label>
                      <textarea
                        value={editFormData.authorityLevelRationale || ""}
                        onChange={(e) => setEditFormData(prev => ({ 
                          ...prev, 
                          authorityLevelRationale: e.target.value 
                        }))}
                        placeholder="Explain why you are overriding the AI classification..."
                        rows={2}
                        className="w-full px-3 py-2 rounded-lg bg-input border border-amber-500/30 text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-500"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Required. This will be logged in the governance audit trail.
                      </p>
                    </div>
                  )}
                </div>
              </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleSaveGovernanceMetadata}
                className="flex-1 px-4 py-2.5 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:bg-accent/90 transition-colors"
              >
                Save Changes
              </button>
              <button
                onClick={handleCancelEdit}
                className="px-4 py-2.5 rounded-lg bg-muted text-foreground text-sm font-medium hover:bg-muted/80 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Governance Details Modal */}
      {detailsFile && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl animate-in fade-in-0 zoom-in-95 duration-200">
            {/* Header */}
            <div className="p-6 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-accent/10">
                  <Info size={24} className="text-accent" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-foreground">Document Governance Details</h2>
                  <p className="text-sm text-muted-foreground">{detailsFile.name}</p>
                </div>
              </div>
              <button
                onClick={() => setDetailsFile(null)}
                className="p-2 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <X size={20} className="text-muted-foreground" />
              </button>
            </div>

            {/* Content - Scrollable */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Sources/Provenance Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <Globe size={16} className="text-accent" />
                  Sources & Provenance
                </h3>
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50 space-y-2 text-sm">
                  {detailsFile.sourceUrl && (
                    <div className="flex items-start gap-2">
                      <span className="text-muted-foreground font-medium min-w-[120px]">Source URL:</span>
                      <a
                        href={detailsFile.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent hover:underline flex items-center gap-1 flex-1"
                      >
                        <span className="truncate">{detailsFile.sourceUrl}</span>
                        <ExternalLink size={14} />
                      </a>
                    </div>
                  )}
                  {detailsFile.sourceDomain && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[120px]">Domain:</span>
                      <span className="text-foreground">{detailsFile.sourceDomain}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground font-medium min-w-[120px]">Ingestion Source:</span>
                    <span className="text-foreground">
                      {detailsFile.sourceUrl ? "URL Scraping" : "File Upload"}
                    </span>
                  </div>
                  {detailsFile.uploadedDate && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[120px]">Uploaded:</span>
                      <span className="text-foreground">{detailsFile.uploadedDate}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* AI Classification Confidence Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <Cpu size={16} className="text-accent" />
                  AI Classification
                </h3>
                <div className={`p-4 rounded-lg border space-y-3 text-sm ${
                  detailsFile.needsHumanReview 
                    ? "bg-red-500/5 border-red-500/20" 
                    : "bg-muted/30 border-border/50"
                }`}>
                  {/* Confidence Score */}
                  {detailsFile.classificationConfidence !== undefined && (
                    <div className="flex items-center gap-3">
                      <span className="text-muted-foreground font-medium min-w-[120px]">Confidence:</span>
                      <div className="flex items-center gap-2 flex-1">
                        <div className="flex-1 max-w-[150px] h-2.5 bg-muted rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all ${getConfidenceColor(detailsFile.classificationConfidence)}`}
                            style={{ width: `${detailsFile.classificationConfidence}%` }}
                          />
                        </div>
                        <span className={`font-bold ${getConfidenceTextColor(detailsFile.classificationConfidence)}`}>
                          {detailsFile.classificationConfidence}%
                        </span>
                      </div>
                    </div>
                  )}
                  
                  {/* Needs Review Alert */}
                  {detailsFile.needsHumanReview && (
                    <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                      <AlertTriangle size={18} className="text-red-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="text-red-600 font-semibold text-sm block">Needs Human Review</span>
                        {detailsFile.reviewReason && (
                          <p className="text-xs text-red-500 mt-1">{detailsFile.reviewReason}</p>
                        )}
                        <button
                          onClick={() => {
                            setDetailsFile(null)
                            handleEditFile(detailsFile)
                          }}
                          className="mt-2 px-3 py-1.5 rounded-lg bg-red-600 text-white text-xs font-medium hover:bg-red-700 transition-colors"
                        >
                          Review & Confirm Classification
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {/* Reviewed Status */}
                  {detailsFile.reviewedAt && !detailsFile.needsHumanReview && (
                    <div className="flex items-center gap-2 text-green-600 pt-2 border-t border-border/50">
                      <CheckCircle2 size={16} />
                      <span className="text-sm">
                        Reviewed by {detailsFile.reviewedBy || "admin"} on {detailsFile.reviewedAt}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Authority Level Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <FileCheck size={16} className="text-accent" />
                  Authority Level
                </h3>
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50 space-y-3">
                  {detailsFile.authorityLevel && (
                    <div className="flex items-center gap-3">
                      <div
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-semibold border ${
                          AUTHORITY_LEVELS[detailsFile.authorityLevel].color
                        }`}
                      >
                        <span className={`w-2 h-2 rounded-full ${AUTHORITY_LEVELS[detailsFile.authorityLevel].badgeColor}`}></span>
                        <span>Level {detailsFile.authorityLevel}: {AUTHORITY_LEVELS[detailsFile.authorityLevel].label}</span>
                      </div>
                    </div>
                  )}
                  {detailsFile.authorityLevelRationale && (
                    <div className="pt-2 border-t border-border/50">
                      <p className="text-xs text-muted-foreground font-medium mb-1">Rationale:</p>
                      <p className="text-sm text-foreground">{detailsFile.authorityLevelRationale}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Citability Status Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-accent" />
                  Citability Status
                </h3>
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50 space-y-3">
                  {/* Citable indicator */}
                  <div className="flex items-center gap-3">
                    {computeCitability(detailsFile).isCitable ? (
                      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/20 border border-green-500/30">
                        <CheckCircle2 size={18} className="text-green-600" />
                        <span className="text-sm font-semibold text-green-600">Citable in RAG Answers: Yes</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/20 border border-red-500/30">
                        <XCircle size={18} className="text-red-600" />
                        <span className="text-sm font-semibold text-red-600">Citable in RAG Answers: No</span>
                      </div>
                    )}
                  </div>
                  
                  {/* Reasons list */}
                  <div className="pt-2 border-t border-border/50">
                    <p className="text-xs text-muted-foreground font-medium mb-2">Reason:</p>
                    <ul className="space-y-1">
                      {computeCitability(detailsFile).reasons.map((reason, idx) => (
                        <li key={idx} className="flex items-center gap-2 text-sm">
                          {reason.includes("not") || reason.includes("needs") || reason.includes("Superseded") || reason.includes("partial") || reason.includes("failed") ? (
                            <XCircle size={14} className="text-red-500 flex-shrink-0" />
                          ) : (
                            <CheckCircle2 size={14} className="text-green-500 flex-shrink-0" />
                          )}
                          <span className="text-foreground">{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Version Lineage Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <History size={16} className="text-accent" />
                  Version Lineage
                </h3>
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50 space-y-2 text-sm">
                  {detailsFile.docType && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Doc Type:</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${DOC_TYPES[detailsFile.docType]?.color || DOC_TYPES.other.color}`}>
                        {DOC_TYPES[detailsFile.docType]?.label || detailsFile.docType}
                      </span>
                    </div>
                  )}
                  {detailsFile.formFamily && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Form Family:</span>
                      <span className="text-foreground font-semibold">{detailsFile.formFamily}</span>
                    </div>
                  )}
                  {detailsFile.version && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Version:</span>
                      <span className="text-foreground">{detailsFile.version}</span>
                    </div>
                  )}
                  {detailsFile.revisionDate && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Revision Date:</span>
                      <span className="text-foreground">{formatEffectiveDate(detailsFile.revisionDate)}</span>
                    </div>
                  )}
                  {detailsFile.parsingQuality && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Parsing Quality:</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${
                        detailsFile.parsingQuality === "ok" 
                          ? "bg-green-500/20 text-green-600 border-green-500/30" 
                          : detailsFile.parsingQuality === "partial"
                            ? "bg-amber-500/20 text-amber-600 border-amber-500/30"
                            : "bg-red-500/20 text-red-600 border-red-500/30"
                      }`}>
                        {detailsFile.parsingQuality === "ok" ? "OK" : detailsFile.parsingQuality === "partial" ? "Partial" : "Failed"}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground font-medium min-w-[140px]">Latest for Tax Year:</span>
                    {detailsFile.isLatestForTaxYear ? (
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-500/20 text-green-600 border border-green-500/30">Yes</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-600 border border-amber-500/30">No</span>
                    )}
                  </div>
                  {detailsFile.supersededByVersionId && (
                    <div className="flex items-center gap-2 pt-2 border-t border-border/50 mt-2">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Superseded By Version:</span>
                      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-600 border border-amber-500/30">
                        {detailsFile.supersededByVersionId}
                      </span>
                      <span className="text-xs text-muted-foreground">(same tax year)</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Tax Year Applicability Section - PRIMARY VALIDITY AXIS */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <Calendar size={16} className="text-accent" />
                  Tax Year Applicability
                  <span className="text-xs font-normal text-accent bg-accent/10 px-2 py-0.5 rounded">(Primary Validity)</span>
                </h3>
                <div className="p-4 rounded-lg bg-accent/5 border border-accent/20 space-y-3 text-sm">
                  {/* Tax Years - PRIMARY */}
                  {(detailsFile.appliesToTaxYears && detailsFile.appliesToTaxYears.length > 0) || detailsFile.taxYear ? (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Applies To Tax Years:</span>
                      <span className="px-3 py-1 rounded-lg text-sm font-bold bg-accent/20 text-accent border border-accent/30">
                        {formatTaxYears(detailsFile.appliesToTaxYears, detailsFile.taxYear)}
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Applies To Tax Years:</span>
                      <span className="text-amber-600 text-sm">Not specified</span>
                    </div>
                  )}
                  {/* Jurisdictions */}
                  {detailsFile.appliesToJurisdictions && detailsFile.appliesToJurisdictions.length > 0 && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-muted-foreground font-medium min-w-[140px]">Applies To Jurisdictions:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {detailsFile.appliesToJurisdictions.map((jurisdiction) => (
                          <span
                            key={jurisdiction}
                            className="px-2 py-0.5 rounded-full text-xs bg-primary/20 text-primary border border-primary/30"
                          >
                            {jurisdiction === "federal" ? "Federal" : jurisdiction === "state" ? "State" : jurisdiction === "local" ? "Local" : jurisdiction}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Revision Metadata - SECONDARY (moved from separate section) */}
                  {(detailsFile.effectiveFrom || detailsFile.effectiveTo) && (
                    <div className="pt-2 mt-2 border-t border-border/50">
                      <p className="text-xs text-muted-foreground font-medium mb-2">Revision Metadata:</p>
                      <div className="flex flex-wrap gap-4">
                        {detailsFile.effectiveFrom && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-muted-foreground text-xs">Published:</span>
                            <span className="text-foreground text-xs">{formatEffectiveDate(detailsFile.effectiveFrom)}</span>
                          </div>
                        )}
                        {detailsFile.effectiveTo && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-muted-foreground text-xs">Revision End:</span>
                            <span className="text-foreground text-xs">{formatEffectiveDate(detailsFile.effectiveTo)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Supersession Chain Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <GitCompare size={16} className="text-accent" />
                  Supersession Chain
                </h3>
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50 space-y-2 text-sm">
                  {detailsFile.supersededBy && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[120px]">Superseded By:</span>
                      <span className="text-accent hover:underline cursor-pointer">{detailsFile.supersededBy}</span>
                    </div>
                  )}
                  {detailsFile.replacedBy && !detailsFile.supersededBy && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-medium min-w-[120px]">Replaced By:</span>
                      <span className="text-accent hover:underline cursor-pointer">{detailsFile.replacedBy}</span>
                    </div>
                  )}
                  {detailsFile.supersessionChain && detailsFile.supersessionChain.length > 0 && (
                    <div className="pt-2 border-t border-border/50">
                      <p className="text-xs text-muted-foreground font-medium mb-2">Full Chain:</p>
                      <div className="flex flex-col gap-1.5">
                        {detailsFile.supersessionChain.map((doc, index) => (
                          <div key={index} className="flex items-center gap-2 text-sm">
                            <span className="text-muted-foreground">{index + 1}.</span>
                            <span className="text-foreground">{doc}</span>
                            {index < detailsFile.supersessionChain!.length - 1 && (
                              <ArrowRight size={12} className="text-muted-foreground ml-2" />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {!detailsFile.supersededBy && !detailsFile.replacedBy && (!detailsFile.supersessionChain || detailsFile.supersessionChain.length === 0) && (
                    <p className="text-sm text-muted-foreground">No supersession information available</p>
                  )}
                </div>
              </div>

              {/* Ingestion History Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <History size={16} className="text-accent" />
                  Ingestion History
                </h3>
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                  {detailsFile.ingestionHistory && detailsFile.ingestionHistory.length > 0 ? (
                    <div className="space-y-3">
                      {detailsFile.ingestionHistory.map((event, index) => (
                        <div key={index} className="flex items-start gap-3 pb-3 border-b border-border/50 last:border-0 last:pb-0">
                          <div className="mt-0.5">
                            {event.status === "success" && <CheckCircle2 size={16} className="text-green-500" />}
                            {event.status === "failed" && <XCircle size={16} className="text-destructive" />}
                            {event.status === "in_progress" && <Clock size={16} className="text-accent" />}
                          </div>
                          <div className="flex-1 space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-sm font-medium text-foreground capitalize">{event.action.replace("_", " ")}</span>
                              <span className="text-xs text-muted-foreground">{event.timestamp}</span>
                              {event.userId && (
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <User size={12} />
                                  {event.userId}
                                </span>
                              )}
                            </div>
                            {event.details && (
                              <p className="text-xs text-muted-foreground">{event.details}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No ingestion history available</p>
                  )}
                </div>
              </div>

              {/* Error History Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <AlertCircle size={16} className="text-accent" />
                  Error History
                </h3>
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                  {detailsFile.errorHistory && detailsFile.errorHistory.length > 0 ? (
                    <div className="space-y-3">
                      {detailsFile.errorHistory.map((error, index) => (
                        <div key={index} className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                              error.severity === "critical" ? "bg-destructive/20 text-destructive" :
                              error.severity === "warning" ? "bg-yellow-500/20 text-yellow-600" :
                              "bg-blue-500/20 text-blue-600"
                            }`}>
                              {error.severity.toUpperCase()}
                            </span>
                            <span className="text-xs text-muted-foreground capitalize">{error.type.replace("_", " ")}</span>
                            <span className="text-xs text-muted-foreground">{error.timestamp}</span>
                            {error.resolved && (
                              <span className="text-xs text-green-500 flex items-center gap-1">
                                <Check size={12} />
                                Resolved {error.resolvedAt && `on ${error.resolvedAt}`}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-foreground">{error.message}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No error history available</p>
                  )}
                </div>
              </div>

              {/* Governance History Section */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground uppercase flex items-center gap-2">
                  <FileCheck size={16} className="text-accent" />
                  Governance History
                </h3>
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                  {detailsFile.governanceHistory && detailsFile.governanceHistory.length > 0 ? (
                    <div className="space-y-3">
                      {detailsFile.governanceHistory.map((event, index) => (
                        <div key={index} className="flex items-start gap-3 pb-3 border-b border-border/50 last:border-0 last:pb-0">
                          <Clock size={16} className="text-muted-foreground mt-0.5" />
                          <div className="flex-1 space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-sm font-medium text-foreground capitalize">{event.action.replace("_", " ")}</span>
                              <span className="text-xs text-muted-foreground">{event.timestamp}</span>
                              {event.userId && (
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <User size={12} />
                                  {event.userId}
                                </span>
                              )}
                            </div>
                            {event.previousValue && (
                              <div className="flex items-center gap-2 text-xs">
                                <span className="text-muted-foreground">Previous:</span>
                                <span className="text-foreground line-through">{event.previousValue}</span>
                                <ArrowRight size={12} className="text-muted-foreground" />
                                <span className="text-foreground font-medium">{event.newValue}</span>
                              </div>
                            )}
                            {!event.previousValue && (
                              <div className="text-xs">
                                <span className="text-muted-foreground">New value: </span>
                                <span className="text-foreground font-medium">{event.newValue}</span>
                              </div>
                            )}
                            {event.reason && (
                              <p className="text-xs text-muted-foreground italic mt-1">Reason: {event.reason}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No governance history available</p>
                  )}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-border">
              <button
                onClick={() => setDetailsFile(null)}
                className="w-full px-4 py-2.5 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:bg-accent/90 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
