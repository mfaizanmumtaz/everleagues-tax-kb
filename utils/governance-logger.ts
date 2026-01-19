// Governance Action Logger
// Creates immutable log entries for all governance actions
// Required for compliance: Tax audits, Legal discovery, Healthcare compliance

export interface GovernanceLogEntry {
  id: string // Immutable unique ID (timestamp + random)
  timestamp: string // ISO 8601 format - When
  userId: string // Who performed the action
  userEmail?: string // User email for display
  documentId: string // Which document was changed
  documentName: string // Document name for display
  action: "state_changed" | "metadata_updated" | "authority_changed" | "bulk_action" | "document_published" | "document_deprecated"
  fieldChanged: string // Specific field that was changed
  previousValue?: string // Previous value (stringified)
  newValue: string // New value (stringified)
  reason?: string // Reason for change (required for deprecations)
  ipAddress?: string // For compliance tracking
  sessionId?: string // For audit trail
  metadata?: Record<string, unknown> // Additional context
}

export interface GovernanceLogFilter {
  dateFrom?: string
  dateTo?: string
  userId?: string
  documentId?: string
  documentName?: string
  action?: string
  fieldChanged?: string
  searchQuery?: string
}

// Generate immutable unique ID
const generateLogId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

// Format timestamp for display - Short format (time only) for table
export const formatLogTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp)
    return date.toLocaleString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    })
  } catch {
    return timestamp
  }
}

// Create a governance log entry - IMMUTABLE after creation
export function createGovernanceLogEntry(
  documentId: string,
  documentName: string,
  action: GovernanceLogEntry["action"],
  fieldChanged: string,
  previousValue: unknown,
  newValue: unknown,
  reason?: string,
  userId?: string,
  userEmail?: string
): GovernanceLogEntry {
  return Object.freeze({
    id: generateLogId(),
    timestamp: new Date().toISOString(),
    userId: userId || "system",
    userEmail: userEmail || "system@everleagues.com",
    documentId,
    documentName,
    action,
    fieldChanged,
    previousValue: previousValue !== undefined && previousValue !== null 
      ? typeof previousValue === "object" 
        ? JSON.stringify(previousValue) 
        : String(previousValue)
      : undefined,
    newValue: newValue !== undefined && newValue !== null
      ? typeof newValue === "object"
        ? JSON.stringify(newValue)
        : String(newValue)
      : "",
    reason,
  }) as GovernanceLogEntry
}

// Filter logs based on criteria
export function filterGovernanceLogs(
  logs: GovernanceLogEntry[],
  filter: GovernanceLogFilter
): GovernanceLogEntry[] {
  return logs.filter((log) => {
    // Date range filter
    if (filter.dateFrom) {
      const fromDate = new Date(filter.dateFrom)
      const logDate = new Date(log.timestamp)
      if (logDate < fromDate) return false
    }
    if (filter.dateTo) {
      const toDate = new Date(filter.dateTo)
      toDate.setHours(23, 59, 59, 999) // End of day
      const logDate = new Date(log.timestamp)
      if (logDate > toDate) return false
    }

    // User filter
    if (filter.userId && log.userId !== filter.userId) return false

    // Document filter
    if (filter.documentId && log.documentId !== filter.documentId) return false
    if (filter.documentName && !log.documentName.toLowerCase().includes(filter.documentName.toLowerCase())) return false

    // Action filter
    if (filter.action && log.action !== filter.action) return false

    // Field filter
    if (filter.fieldChanged && log.fieldChanged !== filter.fieldChanged) return false

    // Search query (searches across all text fields)
    if (filter.searchQuery) {
      const query = filter.searchQuery.toLowerCase()
      const searchableText = [
        log.documentName,
        log.userId,
        log.userEmail,
        log.action,
        log.fieldChanged,
        log.previousValue,
        log.newValue,
        log.reason,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
      if (!searchableText.includes(query)) return false
    }

    return true
  })
}

// Export logs to CSV format
export function exportLogsToCSV(logs: GovernanceLogEntry[]): string {
  const headers = [
    "ID",
    "Timestamp",
    "User ID",
    "User Email",
    "Document ID",
    "Document Name",
    "Action",
    "Field Changed",
    "Previous Value",
    "New Value",
    "Reason",
  ]

  const rows = logs.map((log) => [
    log.id,
    log.timestamp,
    log.userId,
    log.userEmail || "",
    log.documentId,
    log.documentName,
    log.action,
    log.fieldChanged,
    log.previousValue || "",
    log.newValue,
    log.reason || "",
  ])

  const csvContent = [
    headers.join(","),
    ...rows.map((row) =>
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")
    ),
  ].join("\n")

  return csvContent
}

// Export logs to JSON format
export function exportLogsToJSON(logs: GovernanceLogEntry[]): string {
  return JSON.stringify(logs, null, 2)
}

// Download file helper
export function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// Get unique values for filters
export function getUniqueUsers(logs: GovernanceLogEntry[]): string[] {
  return [...new Set(logs.map((log) => log.userId))].sort()
}

export function getUniqueDocuments(logs: GovernanceLogEntry[]): { id: string; name: string }[] {
  const seen = new Map<string, string>()
  logs.forEach((log) => {
    if (!seen.has(log.documentId)) {
      seen.set(log.documentId, log.documentName)
    }
  })
  return Array.from(seen.entries())
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name))
}

export function getUniqueActions(logs: GovernanceLogEntry[]): string[] {
  return [...new Set(logs.map((log) => log.action))].sort()
}

export function getUniqueFields(logs: GovernanceLogEntry[]): string[] {
  return [...new Set(logs.map((log) => log.fieldChanged))].sort()
}

// Format action for display
export function formatAction(action: string): string {
  return action
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

