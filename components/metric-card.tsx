"use client"

import type React from "react"

import { TrendingUp, TrendingDown } from "lucide-react"

interface MetricCardProps {
  label: string
  value: string
  change: string
  icon: React.ReactNode
  trend: "up" | "down"
}

export default function MetricCard({ label, value, change, icon, trend }: MetricCardProps) {
  return (
    <div className="p-6 rounded-lg bg-card border border-border hover:border-primary/30 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="w-12 h-12 rounded-lg bg-accent/20 flex items-center justify-center text-accent">{icon}</div>
        <div
          className={`flex items-center gap-1 text-sm font-semibold ${
            trend === "up" ? "text-green-500" : "text-destructive"
          }`}
        >
          {trend === "up" ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
          {change}
        </div>
      </div>
      <p className="text-sm text-muted-foreground mb-1">{label}</p>
      <p className="text-3xl font-bold text-foreground">{value}</p>
    </div>
  )
}
