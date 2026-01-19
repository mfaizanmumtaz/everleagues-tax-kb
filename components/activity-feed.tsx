"use client"

import { FileText, Settings, Users, Zap, GitBranch } from "lucide-react"

const activities = [
  {
    type: "update",
    icon: <FileText size={18} />,
    title: "Form 1040 Updated",
    description: "IRS form updated from source URL",
    time: "2 hours ago",
  },
  {
    type: "config",
    icon: <Settings size={18} />,
    title: "Configuration Changed",
    description: "Auto-update frequency changed to daily",
    time: "5 hours ago",
  },
  {
    type: "user",
    icon: <Users size={18} />,
    title: "User Added",
    description: "Sarah Operator added to system",
    time: "1 day ago",
  },
  {
    type: "deployment",
    icon: <GitBranch size={18} />,
    title: "Version v2.4.1 Deployed",
    description: "Pushed to production environment",
    time: "2 days ago",
  },
  {
    type: "performance",
    icon: <Zap size={18} />,
    title: "Performance Alert",
    description: "Processing time exceeded threshold",
    time: "3 days ago",
  },
]

export default function ActivityFeed() {
  return (
    <div className="p-6 rounded-lg bg-card border border-border">
      <h2 className="text-xl font-bold text-foreground mb-4">Recent Activity</h2>
      <div className="space-y-3">
        {activities.map((activity, idx) => (
          <div key={idx} className="flex gap-4 pb-3 border-b border-border last:border-0 last:pb-0">
            <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-accent flex-shrink-0">
              {activity.icon}
            </div>
            <div className="flex-1">
              <p className="text-foreground font-semibold text-sm">{activity.title}</p>
              <p className="text-muted-foreground text-xs">{activity.description}</p>
            </div>
            <p className="text-xs text-muted-foreground whitespace-nowrap">{activity.time}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
