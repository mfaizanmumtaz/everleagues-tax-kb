"use client"

import type React from "react"
import { LayoutDashboard, Link2, Files, MessageSquare, Shield } from "lucide-react"

type Section = "dashboard" | "urls" | "files" | "chatbot" | "governance-logs"

interface NavItem {
  id: Section
  label: string
  icon: React.ReactNode
}

const navItems: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={20} /> },
  { id: "urls", label: "URL Management", icon: <Link2 size={20} /> },
  { id: "files", label: "EL Cloud Files", icon: <Files size={20} /> },
  { id: "chatbot", label: "Knowledge Base", icon: <MessageSquare size={20} /> },
  { id: "governance-logs", label: "Governance Audit Log", icon: <Shield size={20} /> },
]

export default function DashboardLayout({ activeSection, setActiveSection, children }: any) {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar Navigation */}
      <nav className="w-64 bg-sidebar border-r border-sidebar-border flex flex-col">
        <div className="p-6 border-b border-sidebar-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-sidebar-primary flex items-center justify-center">
              <span className="text-sidebar-primary-foreground font-bold text-lg">T</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-sidebar-foreground">Tax Docs</h1>
              <p className="text-xs text-muted-foreground">Admin Dashboard</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium ${
                activeSection === item.id
                  ? "bg-sidebar-primary text-sidebar-primary-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/10"
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        {/* Removed the footer section as per updates */}
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">{children}</div>
      </main>
    </div>
  )
}
