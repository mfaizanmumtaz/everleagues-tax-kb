"use client"

import React, { createContext, useContext, useState, useCallback, ReactNode } from "react"
import { GovernanceLogEntry, createGovernanceLogEntry } from "@/utils/governance-logger"

interface GovernanceLogContextType {
  logs: GovernanceLogEntry[]
  addLog: (
    documentId: string,
    documentName: string,
    action: GovernanceLogEntry["action"],
    fieldChanged: string,
    previousValue: unknown,
    newValue: unknown,
    reason?: string,
    userId?: string,
    userEmail?: string
  ) => GovernanceLogEntry
  addMultipleLogs: (entries: GovernanceLogEntry[]) => void
  getLogsByDocument: (documentId: string) => GovernanceLogEntry[]
  getLogsByUser: (userId: string) => GovernanceLogEntry[]
  getLogsByDateRange: (from: Date, to: Date) => GovernanceLogEntry[]
  clearLogs: () => void // Only for testing/demo purposes - in production, logs are immutable
}

const GovernanceLogContext = createContext<GovernanceLogContextType | undefined>(undefined)

// Mock initial logs for demo purposes
const INITIAL_MOCK_LOGS: GovernanceLogEntry[] = [
  {
    id: "1732089600000-abc123def",
    timestamp: "2024-11-20T03:15:00.000Z",
    userId: "admin@example.com",
    userEmail: "admin@example.com",
    documentId: "1",
    documentName: "Form_1040_2024.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: "Draft",
    newValue: "Published",
    reason: "Document verified and ready for use",
  },
  {
    id: "1732003200000-xyz789ghi",
    timestamp: "2024-11-19T14:35:00.000Z",
    userId: "curator@example.com",
    userEmail: "curator@example.com",
    documentId: "2",
    documentName: "Schedule_C_2024.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: "Draft",
    newValue: "Under Review",
    reason: "Pending review for accuracy",
  },
  {
    id: "1731916800000-jkl456mno",
    timestamp: "2024-11-18T09:50:00.000Z",
    userId: "system",
    userEmail: "system@everleagues.com",
    documentId: "3",
    documentName: "State_Tax_Return_CA.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: undefined,
    newValue: "Draft",
    reason: "Auto-assigned Draft state on ingestion",
  },
  {
    id: "1731830400000-pqr123stu",
    timestamp: "2024-11-17T10:05:00.000Z",
    userId: "system",
    userEmail: "system@everleagues.com",
    documentId: "4",
    documentName: "W2_Forms_2024.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: undefined,
    newValue: "Draft",
    reason: "Auto-assigned Draft state on failed ingestion",
  },
  {
    id: "1731657600000-vwx789yza",
    timestamp: "2024-11-15T16:15:00.000Z",
    userId: "admin@example.com",
    userEmail: "admin@example.com",
    documentId: "6",
    documentName: "IRS_Revenue_Ruling_2024.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: "Under Review",
    newValue: "Published",
    reason: "Revenue procedure verified and published",
  },
  {
    id: "1731571200000-bcd456efg",
    timestamp: "2024-11-14T08:50:00.000Z",
    userId: "admin@example.com",
    userEmail: "admin@example.com",
    documentId: "7",
    documentName: "Tax_Code_Title_26.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: undefined,
    newValue: "Published",
    reason: "Initial publication",
  },
  {
    id: "1732089600001-hij789klm",
    timestamp: "2024-11-20T10:05:00.000Z",
    userId: "admin@example.com",
    userEmail: "admin@example.com",
    documentId: "7",
    documentName: "Tax_Code_Title_26.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: "Published",
    newValue: "Deprecated",
    reason: "Superseded by 2024 version",
  },
  {
    id: "1732089600002-nop123qrs",
    timestamp: "2024-11-20T10:05:30.000Z",
    userId: "admin@example.com",
    userEmail: "admin@example.com",
    documentId: "7",
    documentName: "Tax_Code_Title_26.pdf",
    action: "metadata_updated",
    fieldChanged: "supersededBy",
    previousValue: undefined,
    newValue: "Tax_Code_Title_26_2024.pdf",
    reason: "Set supersededBy field",
  },
  {
    id: "1731484800000-tuv456wxy",
    timestamp: "2024-11-13T12:05:00.000Z",
    userId: "system",
    userEmail: "system@everleagues.com",
    documentId: "8",
    documentName: "FAQ_Individual_Taxes.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: undefined,
    newValue: "Draft",
    reason: "Auto-assigned Draft state due to indexing failure",
  },
  {
    id: "1731744000000-zab789cde",
    timestamp: "2024-11-16T11:25:00.000Z",
    userId: "curator@example.com",
    userEmail: "curator@example.com",
    documentId: "5",
    documentName: "Quarterly_Estimated_Q4.pdf",
    action: "state_changed",
    fieldChanged: "governanceState",
    previousValue: "Draft",
    newValue: "Under Review",
    reason: "Pending quarterly review",
  },
]

export function GovernanceLogProvider({ children }: { children: ReactNode }) {
  // Initialize with mock data for demo
  const [logs, setLogs] = useState<GovernanceLogEntry[]>(INITIAL_MOCK_LOGS)

  // Add a single log entry - IMMUTABLE (append only)
  const addLog = useCallback(
    (
      documentId: string,
      documentName: string,
      action: GovernanceLogEntry["action"],
      fieldChanged: string,
      previousValue: unknown,
      newValue: unknown,
      reason?: string,
      userId?: string,
      userEmail?: string
    ): GovernanceLogEntry => {
      const entry = createGovernanceLogEntry(
        documentId,
        documentName,
        action,
        fieldChanged,
        previousValue,
        newValue,
        reason,
        userId,
        userEmail
      )
      setLogs((prev) => [entry, ...prev]) // Newest first
      return entry
    },
    []
  )

  // Add multiple log entries at once
  const addMultipleLogs = useCallback((entries: GovernanceLogEntry[]) => {
    setLogs((prev) => [...entries, ...prev]) // Newest first
  }, [])

  // Get logs for a specific document
  const getLogsByDocument = useCallback(
    (documentId: string): GovernanceLogEntry[] => {
      return logs.filter((log) => log.documentId === documentId)
    },
    [logs]
  )

  // Get logs for a specific user
  const getLogsByUser = useCallback(
    (userId: string): GovernanceLogEntry[] => {
      return logs.filter((log) => log.userId === userId)
    },
    [logs]
  )

  // Get logs within a date range
  const getLogsByDateRange = useCallback(
    (from: Date, to: Date): GovernanceLogEntry[] => {
      return logs.filter((log) => {
        const logDate = new Date(log.timestamp)
        return logDate >= from && logDate <= to
      })
    },
    [logs]
  )

  // Clear logs - for testing only, in production logs are immutable
  const clearLogs = useCallback(() => {
    console.warn("Clearing governance logs - this should only be used in testing/demo mode")
    setLogs([])
  }, [])

  return (
    <GovernanceLogContext.Provider
      value={{
        logs,
        addLog,
        addMultipleLogs,
        getLogsByDocument,
        getLogsByUser,
        getLogsByDateRange,
        clearLogs,
      }}
    >
      {children}
    </GovernanceLogContext.Provider>
  )
}

export function useGovernanceLog() {
  const context = useContext(GovernanceLogContext)
  if (context === undefined) {
    throw new Error("useGovernanceLog must be used within a GovernanceLogProvider")
  }
  return context
}

