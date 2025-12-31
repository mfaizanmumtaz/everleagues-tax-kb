"use client"

import { useState } from "react"
import DashboardLayout from "@/components/dashboard-layout"
import DashboardOverview from "@/components/sections/dashboard-overview"
import URLManagement from "@/components/sections/url-management"
import ELCloudFiles from "@/components/sections/el-cloud-files"
import TaxChatbot from "@/components/sections/tax-chatbot"
import GovernanceAuditLog from "@/components/sections/governance-audit-log"
import { GovernanceLogProvider } from "@/contexts/governance-log-context"

type Section = "dashboard" | "urls" | "files" | "chatbot" | "governance-logs"

export default function Page() {
  const [activeSection, setActiveSection] = useState<Section>("dashboard")

  const renderSection = () => {
    switch (activeSection) {
      case "dashboard":
        return <DashboardOverview />
      case "urls":
        return <URLManagement />
      case "files":
        return <ELCloudFiles />
      case "chatbot":
        return <TaxChatbot />
      case "governance-logs":
        return <GovernanceAuditLog />
      default:
        return <DashboardOverview />
    }
  }

  return (
    <GovernanceLogProvider>
      <DashboardLayout activeSection={activeSection} setActiveSection={setActiveSection}>
        {renderSection()}
      </DashboardLayout>
    </GovernanceLogProvider>
  )
}
