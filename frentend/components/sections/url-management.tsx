"use client"

import { useState, useRef, useEffect } from "react"
import {
  AlertCircle,
  CheckCircle,
  Eye,
  Trash2,
  Key,
  Globe,
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Check,
  Clock,
  Play,
  Upload,
  FileText,
  X,
} from "lucide-react"

interface URL {
  id: string
  url: string
  category: "State" | "Federal"
  state?: string
  active: boolean
  lastUpdated: string
  dataSource: "scrape" | "api" | "file"
  apiKey?: string
  apiEndpoint?: string
  uploadedFile?: File | null
  fileName?: string
  fileSize?: number
  scheduleFrequency?: "on_demand" | "daily" | "weekly" | "monthly" | "quarterly" | "yearly"
  nextScheduledRun?: string
  lastSuccessfulRun?: string
}

const US_STATES = [
  "Alabama",
  "Alaska",
  "Arizona",
  "Arkansas",
  "California",
  "Colorado",
  "Connecticut",
  "Delaware",
  "Florida",
  "Georgia",
  "Hawaii",
  "Idaho",
  "Illinois",
  "Indiana",
  "Iowa",
  "Kansas",
  "Kentucky",
  "Louisiana",
  "Maine",
  "Maryland",
  "Massachusetts",
  "Michigan",
  "Minnesota",
  "Mississippi",
  "Missouri",
  "Montana",
  "Nebraska",
  "Nevada",
  "New Hampshire",
  "New Jersey",
  "New Mexico",
  "New York",
  "North Carolina",
  "North Dakota",
  "Ohio",
  "Oklahoma",
  "Oregon",
  "Pennsylvania",
  "Rhode Island",
  "South Carolina",
  "South Dakota",
  "Tennessee",
  "Texas",
  "Utah",
  "Vermont",
  "Virginia",
  "Washington",
  "West Virginia",
  "Wisconsin",
  "Wyoming",
]

const initialURLs: URL[] = [
  {
    id: "2",
    url: "https://www.tax.ca.gov/forms-publications",
    category: "State",
    state: "California",
    active: true,
    lastUpdated: "4 hours ago",
    dataSource: "scrape",
    scheduleFrequency: "daily",
    nextScheduledRun: "2024-11-21 03:00 UTC",
    lastSuccessfulRun: "2024-11-20 03:00 UTC",
  },
  {
    id: "3",
    url: "https://revenue.texas.gov/forms",
    category: "State",
    state: "Texas",
    active: true,
    lastUpdated: "6 hours ago",
    dataSource: "scrape",
    scheduleFrequency: "weekly",
    nextScheduledRun: "2024-11-25 02:00 UTC",
    lastSuccessfulRun: "2024-11-18 02:00 UTC",
  },
  {
    id: "4",
    url: "https://www.nys.gov/tax-forms",
    category: "State",
    state: "New York",
    active: false,
    lastUpdated: "2 days ago",
    dataSource: "scrape",
    scheduleFrequency: "monthly",
    nextScheduledRun: "2024-12-01 01:00 UTC",
    lastSuccessfulRun: "2024-11-01 01:00 UTC",
  },
  {
    id: "5",
    url: "https://www.mde.maryland.gov/tax",
    category: "State",
    state: "Maryland",
    active: true,
    lastUpdated: "1 day ago",
    dataSource: "scrape",
    scheduleFrequency: "on_demand",
  },
]

const SCHEDULE_FREQUENCIES = [
  { value: "on_demand", label: "On Demand" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "yearly", label: "Yearly" },
] as const

export default function URLManagement() {
  const [urls, setURLs] = useState<URL[]>(initialURLs)
  const [newURL, setNewURL] = useState("")
  const [newCategory, setNewCategory] = useState<"State" | "Federal">("Federal")
  const [newState, setNewState] = useState("")
  const [dataSource, setDataSource] = useState<"scrape" | "api" | "file">("scrape")
  const [apiKey, setApiKey] = useState("")
  const [apiEndpoint, setApiEndpoint] = useState("")
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [showForm, setShowForm] = useState(false)
  const [validationStatus, setValidationStatus] = useState<"none" | "valid" | "invalid">("none")
  const [searchQuery, setSearchQuery] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const urlsPerPage = 5
  const [viewingURL, setViewingURL] = useState<URL | null>(null)
  const [scheduleFrequency, setScheduleFrequency] = useState<"on_demand" | "daily" | "weekly" | "monthly" | "quarterly" | "yearly">("on_demand")
  const [scriptNow, setScriptNow] = useState(false)
  const [scrapingUrlId, setScrapingUrlId] = useState<string | null>(null)
  const [scrapingProgress, setScrapingProgress] = useState<{ current: number; total: number; status: string } | null>(null)
  const [scrapeDelay, setScrapeDelay] = useState<number>(2) // seconds between requests
  const [requestsPerMinute, setRequestsPerMinute] = useState<number>(30)
  const [showRateLimitSettings, setShowRateLimitSettings] = useState(false)
  const [maxFilesPerSession, setMaxFilesPerSession] = useState<number>(10000)
  const [filesScrapedCount, setFilesScrapedCount] = useState<number>(0)
  const [showFileLimitWarning, setShowFileLimitWarning] = useState(false)

  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false)
  const [stateDropdownOpen, setStateDropdownOpen] = useState(false)
  const [stateSearchQuery, setStateSearchQuery] = useState("")
  const [statusDropdownOpen, setStatusDropdownOpen] = useState<string | null>(null)
  const [scheduleDropdownOpen, setScheduleDropdownOpen] = useState(false)
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null)
  const [showDuplicatesOnly, setShowDuplicatesOnly] = useState(false)
  const categoryDropdownRef = useRef<HTMLDivElement>(null)
  const stateDropdownRef = useRef<HTMLDivElement>(null)
  const statusDropdownRef = useRef<HTMLDivElement>(null)
  const scheduleDropdownRef = useRef<HTMLDivElement>(null)

  // Check for duplicate URLs
  const checkDuplicateUrl = (urlToCheck: string): string | null => {
    if (!urlToCheck) return null
    const existingUrl = urls.find(u => u.url.toLowerCase() === urlToCheck.toLowerCase())
    if (existingUrl) {
      return `This URL already exists in the list (added ${existingUrl.lastUpdated})`
    }
    return null
  }

  // Find duplicate URLs in the list
  const findDuplicates = (): Set<string> => {
    const urlCounts = new Map<string, number>()
    urls.forEach(u => {
      const key = u.url.toLowerCase()
      urlCounts.set(key, (urlCounts.get(key) || 0) + 1)
    })
    const duplicates = new Set<string>()
    urls.forEach(u => {
      if ((urlCounts.get(u.url.toLowerCase()) || 0) > 1) {
        duplicates.add(u.id)
      }
    })
    return duplicates
  }

  const duplicateIds = findDuplicates()

  const filteredStates = US_STATES.filter((state) => state.toLowerCase().includes(stateSearchQuery.toLowerCase()))

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (categoryDropdownRef.current && !categoryDropdownRef.current.contains(event.target as Node)) {
        setCategoryDropdownOpen(false)
      }
      if (stateDropdownRef.current && !stateDropdownRef.current.contains(event.target as Node)) {
        setStateDropdownOpen(false)
        setStateSearchQuery("")
      }
      if (statusDropdownRef.current && !statusDropdownRef.current.contains(event.target as Node)) {
        setStatusDropdownOpen(null)
      }
      if (scheduleDropdownRef.current && !scheduleDropdownRef.current.contains(event.target as Node)) {
        setScheduleDropdownOpen(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleAddURL = () => {
    if (dataSource === "file" && !uploadedFile) {
      setValidationStatus("invalid")
      return
    }
    if (dataSource !== "file" && !newURL) {
      setValidationStatus("invalid")
      return
    }
    if (newCategory === "State" && !newState) {
      setValidationStatus("invalid")
      return
    }
    if (dataSource === "api" && (!apiKey || !apiEndpoint)) {
      setValidationStatus("invalid")
      return
    }

    try {
      if (dataSource !== "file") {
        new URL(newURL)
      }
      setValidationStatus("valid")

      const url: URL = {
        id: String(Date.now()),
        url: dataSource === "file" ? uploadedFile?.name || "File Upload" : newURL,
        category: newCategory,
        state: newCategory === "State" ? newState : undefined,
        active: true,
        lastUpdated: "now",
        dataSource,
        apiKey: dataSource === "api" ? apiKey : undefined,
        apiEndpoint: dataSource === "api" ? apiEndpoint : undefined,
        uploadedFile: dataSource === "file" ? uploadedFile : undefined,
        fileName: dataSource === "file" ? uploadedFile?.name : undefined,
        fileSize: dataSource === "file" ? uploadedFile?.size : undefined,
        scheduleFrequency,
        nextScheduledRun: scheduleFrequency !== "on_demand" ? new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() : undefined,
        lastSuccessfulRun: scriptNow ? new Date().toISOString() : undefined,
      }

      setURLs([url, ...urls])
      setNewURL("")
      setNewState("")
      setDataSource("scrape")
      setApiKey("")
      setApiEndpoint("")
      setUploadedFile(null)
      setScheduleFrequency("on_demand")
      setScriptNow(false)
      setShowForm(false)
      setValidationStatus("none")
      setDuplicateWarning(null)
    } catch {
      setValidationStatus("invalid")
    }
  }

  const handleValidateURL = () => {
    if (dataSource === "file") {
      if (uploadedFile) {
        setValidationStatus("valid")
      } else {
        setValidationStatus("invalid")
      }
      return
    }
    try {
      new URL(newURL)
      setValidationStatus("valid")
    } catch {
      setValidationStatus("invalid")
    }
  }

  const handleFileSelect = (file: File) => {
    setUploadedFile(file)
    setValidationStatus("none")
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i]
  }

  const toggleURL = (id: string) => {
    setURLs(urls.map((u) => (u.id === id ? { ...u, active: !u.active } : u)))
  }

  const updateURLStatus = (id: string, active: boolean) => {
    setURLs(urls.map((u) => (u.id === id ? { ...u, active } : u)))
  }

  const deleteURL = (id: string) => {
    setURLs(urls.filter((u) => u.id !== id))
  }

  const handleStartScrape = (id: string, continueFromLimit?: boolean) => {
    if (!continueFromLimit) {
      setFilesScrapedCount(0)
    }
    setShowFileLimitWarning(false)
    setScrapingUrlId(id)
    setScrapingProgress({ current: 0, total: 100, status: "Initializing scrape..." })
    
    // Simulate scraping progress with file counting
    let progress = continueFromLimit ? 50 : 0
    let fileCount = continueFromLimit ? filesScrapedCount : 0
    
    const interval = setInterval(() => {
      progress += Math.random() * 15
      fileCount += Math.floor(Math.random() * 500) + 100
      
      // Check file limit
      if (fileCount >= maxFilesPerSession) {
        clearInterval(interval)
        setFilesScrapedCount(fileCount)
        setScrapingProgress(null)
        setScrapingUrlId(null)
        setShowFileLimitWarning(true)
        return
      }
      
      if (progress >= 100) {
        clearInterval(interval)
        setScrapingProgress(null)
        setScrapingUrlId(null)
        setFilesScrapedCount(0)
        setURLs(prev => prev.map(u => 
          u.id === id 
            ? { ...u, lastUpdated: "just now", lastSuccessfulRun: new Date().toISOString() } 
            : u
        ))
      } else {
        const statuses = [
          "Fetching page content...",
          "Parsing HTML...",
          "Extracting documents...",
          "Processing files...",
          "Updating index..."
        ]
        setFilesScrapedCount(fileCount)
        setScrapingProgress({ 
          current: Math.min(progress, 99), 
          total: 100, 
          status: `${statuses[Math.floor(progress / 20)] || statuses[0]} (${fileCount.toLocaleString()} files)`
        })
      }
    }, 500)
  }

  const handleCancelScrape = () => {
    setScrapingUrlId(null)
    setScrapingProgress(null)
  }

  const filteredURLs = urls.filter((url) => {
    const matchesSearch =
      url.url.toLowerCase().includes(searchQuery.toLowerCase()) ||
      url.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      url.state?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      url.dataSource.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesDuplicateFilter = !showDuplicatesOnly || duplicateIds.has(url.id)
    return matchesSearch && matchesDuplicateFilter
  })

  const totalPages = Math.ceil(filteredURLs.length / urlsPerPage)
  const startIndex = (currentPage - 1) * urlsPerPage
  const endIndex = startIndex + urlsPerPage
  const currentURLs = filteredURLs.slice(startIndex, endIndex)

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    setCurrentPage(1)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground mb-2">URL Management</h1>
        <p className="text-muted-foreground">Add and manage tax document source URLs</p>
      </div>

      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-3 rounded-lg bg-accent text-accent-foreground font-semibold hover:bg-accent/90 transition-colors"
        >
          <Plus size={20} />
          Add New URL
        </button>
      ) : (
        <div className="p-6 rounded-lg bg-card border border-border max-w-2xl overflow-visible">
          <h2 className="text-lg font-bold text-foreground mb-4">Add New URL</h2>
          <div className="space-y-4">
            {dataSource !== "file" && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">URL</label>
                <input
                  type="text"
                  value={newURL}
                  onChange={(e) => {
                    setNewURL(e.target.value)
                    setValidationStatus("none")
                    setDuplicateWarning(checkDuplicateUrl(e.target.value))
                  }}
                  placeholder="https://example.com/tax-forms"
                  className={`w-full px-4 py-2.5 rounded-lg bg-input border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary ${
                    duplicateWarning ? "border-amber-500" : "border-border"
                  }`}
                />
                {validationStatus === "valid" && (
                  <div className="flex items-center gap-2 text-green-500 text-sm mt-2">
                    <CheckCircle size={16} /> Valid URL
                  </div>
                )}
                {duplicateWarning && (
                  <div className="flex items-center gap-2 text-amber-500 text-sm mt-2">
                    <AlertCircle size={16} /> {duplicateWarning}
                  </div>
                )}
                {validationStatus === "invalid" && dataSource !== "file" && (
                  <div className="flex items-center gap-2 text-destructive text-sm mt-2">
                    <AlertCircle size={16} /> Invalid URL format
                    {newCategory === "State" && !newState ? " or state not selected" : ""}
                    {dataSource === "api" && (!apiKey || !apiEndpoint) ? " or API configuration incomplete" : ""}
                  </div>
                )}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Data Source</label>
              <div className="flex gap-3 flex-wrap">
                <button
                  type="button"
                  onClick={() => {
                    setDataSource("scrape")
                    setUploadedFile(null)
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    dataSource === "scrape"
                      ? "bg-accent text-accent-foreground"
                      : "bg-muted text-foreground hover:bg-muted/80"
                  }`}
                >
                  <Globe size={16} />
                  Web Scraping
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDataSource("api")
                    setUploadedFile(null)
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    dataSource === "api"
                      ? "bg-accent text-accent-foreground"
                      : "bg-muted text-foreground hover:bg-muted/80"
                  }`}
                >
                  <Key size={16} />
                  API Integration
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDataSource("file")
                    setNewURL("")
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    dataSource === "file"
                      ? "bg-accent text-accent-foreground"
                      : "bg-muted text-foreground hover:bg-muted/80"
                  }`}
                >
                  <Upload size={16} />
                  File Upload
                </button>
              </div>
            </div>

            {dataSource === "api" && (
              <div className="space-y-4 p-4 rounded-lg bg-muted/30 border border-border">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">API Endpoint</label>
                  <input
                    type="text"
                    value={apiEndpoint}
                    onChange={(e) => setApiEndpoint(e.target.value)}
                    placeholder="https://api.example.com/v1/data"
                    className="w-full px-4 py-2.5 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">API Key</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Enter your API key"
                    className="w-full px-4 py-2.5 rounded-lg bg-input border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
            )}

            {dataSource === "file" && (
              <div className="space-y-4 p-4 rounded-lg bg-muted/30 border border-border">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Upload File</label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileInputChange}
                    className="hidden"
                    accept=".pdf,.doc,.docx,.txt,.xlsx,.xls"
                  />
                  {!uploadedFile ? (
                    <div
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                      className={`w-full px-4 py-8 rounded-lg border-2 border-dashed transition-colors cursor-pointer ${
                        isDragging
                          ? "border-accent bg-accent/10"
                          : "border-border hover:border-accent/50 hover:bg-muted/50"
                      }`}
                    >
                      <div className="flex flex-col items-center justify-center gap-3">
                        <Upload size={32} className="text-muted-foreground" />
                        <div className="text-center">
                          <p className="text-sm font-medium text-foreground">
                            Drag and drop a file here, or click to select
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            Supported formats: PDF, DOC, DOCX, TXT, XLSX, XLS
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full px-4 py-3 rounded-lg bg-input border border-border">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <FileText size={20} className="text-accent flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">{uploadedFile.name}</p>
                            <p className="text-xs text-muted-foreground">{formatFileSize(uploadedFile.size)}</p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setUploadedFile(null)
                            if (fileInputRef.current) {
                              fileInputRef.current.value = ""
                            }
                          }}
                          className="p-1.5 rounded-lg hover:bg-muted transition-colors flex-shrink-0"
                        >
                          <X size={16} className="text-muted-foreground" />
                        </button>
                      </div>
                    </div>
                  )}
                  {validationStatus === "invalid" && dataSource === "file" && !uploadedFile && (
                    <div className="flex items-center gap-2 text-destructive text-sm mt-2">
                      <AlertCircle size={16} /> Please select a file to upload
                    </div>
                  )}
                  {validationStatus === "valid" && dataSource === "file" && uploadedFile && (
                    <div className="flex items-center gap-2 text-green-500 text-sm mt-2">
                      <CheckCircle size={16} /> File selected successfully
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Scheduling Options */}
            <div className="space-y-4 p-4 rounded-lg bg-muted/30 border border-border">
              <label className="block text-sm font-medium text-foreground mb-2">Scheduling Options</label>
              
              {/* Script Now (On-Demand) */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setScriptNow(!scriptNow)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    scriptNow
                      ? "bg-accent text-accent-foreground"
                      : "bg-muted text-foreground hover:bg-muted/80"
                  }`}
                >
                  <Play size={16} />
                  Script Now (On-Demand)
                </button>
                {scriptNow && (
                  <span className="text-xs text-muted-foreground">Will execute immediately after adding</span>
                )}
              </div>

              {/* Update Frequency */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-2">Update Frequency</label>
                <div ref={scheduleDropdownRef} className="relative">
                  <button
                    type="button"
                    onClick={() => setScheduleDropdownOpen(!scheduleDropdownOpen)}
                    className="w-full px-4 py-2.5 rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary flex items-center justify-between hover:bg-muted/50 transition-colors"
                  >
                    <span className="text-sm flex items-center gap-2">
                      <Clock size={16} className="text-muted-foreground" />
                      {SCHEDULE_FREQUENCIES.find((f) => f.value === scheduleFrequency)?.label || "Select frequency"}
                    </span>
                    <ChevronDown
                      size={16}
                      className={`text-muted-foreground transition-transform ${scheduleDropdownOpen ? "rotate-180" : ""}`}
                    />
                  </button>
                  {scheduleDropdownOpen && (
                    <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-xl overflow-hidden">
                      {SCHEDULE_FREQUENCIES.map((freq) => (
                        <div
                          key={freq.value}
                          onClick={() => {
                            setScheduleFrequency(freq.value)
                            setScheduleDropdownOpen(false)
                          }}
                          className="px-4 py-2.5 hover:bg-muted/50 cursor-pointer transition-colors flex items-center justify-between text-sm border-b border-border last:border-b-0"
                        >
                          <span className="text-foreground">{freq.label}</span>
                          {scheduleFrequency === freq.value && <Check size={16} className="text-accent" />}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Rate Limiting Controls */}
            <div className="space-y-4 p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
              <button
                type="button"
                onClick={() => setShowRateLimitSettings(!showRateLimitSettings)}
                className="w-full flex items-center justify-between"
              >
                <label className="block text-sm font-medium text-foreground flex items-center gap-2 cursor-pointer">
                  <Clock size={16} className="text-amber-600" />
                  Rate Limiting (Avoid Bot Detection)
                </label>
                <ChevronDown
                  size={16}
                  className={`text-muted-foreground transition-transform ${showRateLimitSettings ? "rotate-180" : ""}`}
                />
              </button>
              
              {showRateLimitSettings && (
                <div className="space-y-4 pt-2">
                  {/* Delay Between Requests */}
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-2">
                      Delay Between Requests: {scrapeDelay} second{scrapeDelay !== 1 ? "s" : ""}
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={scrapeDelay}
                      onChange={(e) => setScrapeDelay(parseInt(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>1s (Fast)</span>
                      <span>10s (Safe)</span>
                    </div>
                  </div>

                  {/* Requests Per Minute */}
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-2">
                      Max Requests Per Minute: {requestsPerMinute}
                    </label>
                    <input
                      type="range"
                      min="5"
                      max="60"
                      step="5"
                      value={requestsPerMinute}
                      onChange={(e) => setRequestsPerMinute(parseInt(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>5 (Conservative)</span>
                      <span>60 (Aggressive)</span>
                    </div>
                  </div>

                  {/* File Limit Per Session */}
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-2">
                      Max Files Per Session: {maxFilesPerSession.toLocaleString()}
                    </label>
                    <input
                      type="range"
                      min="100"
                      max="50000"
                      step="100"
                      value={maxFilesPerSession}
                      onChange={(e) => setMaxFilesPerSession(parseInt(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>100 (Testing)</span>
                      <span>50,000 (Full Crawl)</span>
                    </div>
                  </div>

                  {/* Rate Limit Summary */}
                  <div className="p-3 rounded-lg bg-muted/50 border border-border">
                    <p className="text-xs text-foreground">
                      <span className="font-medium">Current Settings:</span> Scraping at max{" "}
                      <span className="font-semibold text-amber-600">{requestsPerMinute}</span> requests/min with{" "}
                      <span className="font-semibold text-amber-600">{scrapeDelay}s</span> delay between each request.
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Max files: <span className="font-semibold">{maxFilesPerSession.toLocaleString()}</span> | 
                      Estimated time per 100 pages: ~{Math.ceil((100 * scrapeDelay) / 60)} minutes
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className={`grid grid-cols-2 gap-4 transition-all duration-300 ease-out ${stateDropdownOpen ? "pb-56" : ""}`}>
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Category</label>
                <div ref={categoryDropdownRef} className="relative">
                  <button
                    type="button"
                    onClick={() => setCategoryDropdownOpen(!categoryDropdownOpen)}
                    className="w-full px-4 py-2.5 rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary flex items-center justify-between hover:bg-muted/50 transition-colors"
                  >
                    <span className="text-sm">{newCategory}</span>
                    <ChevronDown
                      size={16}
                      className={`text-muted-foreground transition-transform ${categoryDropdownOpen ? "rotate-180" : ""}`}
                    />
                  </button>
                  {categoryDropdownOpen && (
                    <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-xl overflow-hidden">
                      <div
                        onClick={() => {
                          setNewCategory("Federal")
                          setNewState("")
                          setCategoryDropdownOpen(false)
                        }}
                        className="px-4 py-2.5 hover:bg-muted/50 cursor-pointer transition-colors flex items-center justify-between text-sm"
                      >
                        <span className="text-foreground">Federal</span>
                        {newCategory === "Federal" && <Check size={16} className="text-accent" />}
                      </div>
                      <div
                        onClick={() => {
                          setNewCategory("State")
                          setCategoryDropdownOpen(false)
                        }}
                        className="px-4 py-2.5 hover:bg-muted/50 cursor-pointer transition-colors flex items-center justify-between border-t border-border text-sm"
                      >
                        <span className="text-foreground">State</span>
                        {newCategory === "State" && <Check size={16} className="text-accent" />}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Select State</label>
                <div ref={stateDropdownRef} className="relative">
                  <button
                    type="button"
                    onClick={() => newCategory === "State" && setStateDropdownOpen(!stateDropdownOpen)}
                    disabled={newCategory !== "State"}
                    className={`w-full px-4 py-2.5 rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-accent flex items-center justify-between transition-colors ${
                      newCategory === "State" ? "hover:bg-muted/50 cursor-pointer" : "opacity-50 cursor-not-allowed"
                    }`}
                  >
                    <span className={`text-sm ${newState ? "text-foreground" : "text-muted-foreground"}`}>
                      {newCategory !== "State" ? "Select State first" : newState || "Choose a state"}
                    </span>
                    <ChevronDown
                      size={16}
                      className={`text-muted-foreground transition-transform ${stateDropdownOpen ? "rotate-180" : ""}`}
                    />
                  </button>
                  {stateDropdownOpen && newCategory === "State" && (
                    <div className="absolute z-[100] w-full mt-1 bg-card border border-accent/50 rounded-xl shadow-2xl overflow-hidden animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-200">
                      <div className="p-2.5 border-b border-border/50 bg-muted/30">
                        <div className="relative">
                          <Search
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                            size={14}
                          />
                          <input
                            type="text"
                            value={stateSearchQuery}
                            onChange={(e) => setStateSearchQuery(e.target.value)}
                            placeholder="Search states..."
                            className="w-full pl-8 pr-3 py-2 rounded-lg bg-input border border-border text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/50 transition-all"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                      </div>
                      <div className="max-h-52 overflow-y-auto custom-scrollbar">
                        {filteredStates.length === 0 ? (
                          <div className="px-4 py-4 text-sm text-muted-foreground text-center">No states found</div>
                        ) : (
                          <div className="py-1">
                            {filteredStates.map((state) => (
                              <div
                                key={state}
                                onClick={() => {
                                  setNewState(state)
                                  setStateDropdownOpen(false)
                                  setStateSearchQuery("")
                                }}
                                className="mx-1 px-3 py-2.5 hover:bg-accent/10 cursor-pointer transition-all duration-150 flex items-center justify-between text-sm rounded-lg group"
                              >
                                <span className="text-foreground group-hover:text-accent transition-colors">{state}</span>
                                {newState === state && (
                                  <div className="flex items-center justify-center w-5 h-5 rounded-full bg-accent/20">
                                    <Check size={12} className="text-accent" />
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={handleValidateURL}
                className="px-4 py-2.5 rounded-lg bg-muted text-foreground font-medium hover:bg-muted/80 transition-colors text-sm"
              >
                {dataSource === "file" ? "Validate File" : "Validate URL"}
              </button>
              <button
                onClick={handleAddURL}
                className="px-4 py-2.5 rounded-lg bg-accent text-accent-foreground font-medium hover:bg-accent/90 transition-colors text-sm"
              >
                {dataSource === "file" ? "Upload File" : "Add URL"}
              </button>
              <button
                onClick={() => {
                  setShowForm(false)
                  setNewURL("")
                  setNewCategory("Federal")
                  setNewState("")
                  setDataSource("scrape")
                  setApiKey("")
                  setApiEndpoint("")
                  setUploadedFile(null)
                  if (fileInputRef.current) {
                    fileInputRef.current.value = ""
                  }
                  setScheduleFrequency("on_demand")
                  setScriptNow(false)
                  setValidationStatus("none")
                  setDuplicateWarning(null)
                }}
                className="px-4 py-2.5 rounded-lg bg-muted text-foreground font-medium hover:bg-muted/80 transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search URLs..."
            className="w-80 pl-10 pr-20 py-2.5 rounded-lg bg-card border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
          />
          {searchQuery && (
            <>
              <span className="absolute right-16 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                {filteredURLs.length}
              </span>
              <button
                onClick={() => handleSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground hover:text-foreground transition-colors font-medium"
              >
                Clear
              </button>
            </>
          )}
        </div>
        <button
          onClick={() => setShowDuplicatesOnly(!showDuplicatesOnly)}
          className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
            showDuplicatesOnly
              ? "bg-amber-500/20 text-amber-600 border border-amber-500/30"
              : "bg-muted text-foreground hover:bg-muted/80 border border-border"
          }`}
        >
          <AlertCircle size={16} />
          Show Duplicates
          {duplicateIds.size > 0 && (
            <span className="px-1.5 py-0.5 rounded-full text-xs bg-amber-500/30 text-amber-700">
              {duplicateIds.size}
            </span>
          )}
        </button>
      </div>

      {/* Scraping Progress Indicator */}
      {scrapingUrlId && scrapingProgress && (
        <div className="p-4 rounded-lg bg-accent/10 border border-accent/30 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
            <div>
              <p className="text-sm font-medium text-foreground">
                Scraping: {urls.find(u => u.id === scrapingUrlId)?.url.slice(0, 50)}...
              </p>
              <p className="text-xs text-muted-foreground">{scrapingProgress.status}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-48">
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-accent transition-all duration-300"
                  style={{ width: `${scrapingProgress.current}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground text-right mt-1">
                {Math.round(scrapingProgress.current)}%
              </p>
            </div>
            <button
              onClick={handleCancelScrape}
              className="px-3 py-1.5 rounded-lg bg-destructive/20 text-destructive hover:bg-destructive/30 transition-colors text-sm font-medium flex items-center gap-1.5"
            >
              <X size={14} />
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full">
          <thead className="bg-muted border-b border-border">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-foreground">URL</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-foreground">Data Source</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-foreground">Category</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-foreground">State</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-foreground">Status</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-foreground">Schedule</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-foreground">Last Updated</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {currentURLs.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-8 text-center text-muted-foreground">
                  {searchQuery ? "No URLs found matching your search" : "No URLs added yet"}
                </td>
              </tr>
            ) : (
              currentURLs.map((url) => (
                <tr key={url.id} className="border-b border-border hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4 text-sm text-foreground">
                    <div className="flex items-center gap-2">
                      {url.dataSource === "file" ? (
                        <>
                          <FileText size={16} className="text-accent" />
                          <span>{url.fileName || url.url}</span>
                        </>
                      ) : (
                        <span>{url.url}</span>
                      )}
                      {duplicateIds.has(url.id) && (
                        <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-600 border border-amber-500/30">
                          Duplicate
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className="flex items-center gap-1 text-muted-foreground">
                      {url.dataSource === "api" ? (
                        <Key size={14} />
                      ) : url.dataSource === "file" ? (
                        <Upload size={14} />
                      ) : (
                        <Globe size={14} />
                      )}
                      <span className="capitalize">{url.dataSource === "file" ? "File Upload" : url.dataSource}</span>
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span
                      className={`px-2 py-1.5 rounded-full text-xs font-semibold ${
                        url.category === "State" ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {url.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-foreground">{url.state || "-"}</td>
                  <td className="px-6 py-4">
                    <div 
                      ref={statusDropdownOpen === url.id ? statusDropdownRef : null}
                      className="relative inline-block"
                    >
                      <button
                        onClick={() => setStatusDropdownOpen(statusDropdownOpen === url.id ? null : url.id)}
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-[13px] font-medium transition-all duration-200 cursor-pointer ${
                          url.active
                            ? "bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20"
                            : "bg-zinc-500/10 text-zinc-400 hover:bg-zinc-500/20"
                        }`}
                      >
                        <span 
                          className={`w-2 h-2 rounded-full ${
                            url.active ? "bg-emerald-500" : "bg-zinc-500"
                          }`} 
                        />
                        <span className="tracking-wide">{url.active ? "Active" : "Inactive"}</span>
                        <ChevronDown 
                          size={14} 
                          className={`opacity-60 transition-transform duration-200 ${statusDropdownOpen === url.id ? "rotate-180" : ""}`}
                        />
                      </button>
                      
                      {statusDropdownOpen === url.id && (
                        <div className="absolute z-50 top-full left-0 mt-1.5 min-w-[140px] bg-card border border-border/80 rounded-lg shadow-xl overflow-hidden animate-in fade-in-0 zoom-in-95 slide-in-from-top-2 duration-150">
                          <div className="py-1">
                            <button
                              onClick={() => {
                                updateURLStatus(url.id, true)
                                setStatusDropdownOpen(null)
                              }}
                              className={`w-full flex items-center gap-2.5 px-3 py-2 text-[13px] font-medium transition-colors ${
                                url.active 
                                  ? "bg-emerald-500/10 text-emerald-500" 
                                  : "text-foreground/80 hover:bg-muted/60"
                              }`}
                            >
                              <span className="w-2 h-2 rounded-full bg-emerald-500" />
                              <span>Active</span>
                              {url.active && <Check size={14} className="ml-auto" />}
                            </button>
                            <button
                              onClick={() => {
                                updateURLStatus(url.id, false)
                                setStatusDropdownOpen(null)
                              }}
                              className={`w-full flex items-center gap-2.5 px-3 py-2 text-[13px] font-medium transition-colors ${
                                !url.active 
                                  ? "bg-zinc-500/10 text-zinc-400" 
                                  : "text-foreground/80 hover:bg-muted/60"
                              }`}
                            >
                              <span className="w-2 h-2 rounded-full bg-zinc-500" />
                              <span>Inactive</span>
                              {!url.active && <Check size={14} className="ml-auto" />}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex flex-col gap-1">
                      <span className="text-foreground font-medium capitalize">
                        {url.scheduleFrequency === "on_demand" ? "On Demand" : url.scheduleFrequency}
                      </span>
                      {url.nextScheduledRun && (
                        <span className="text-xs text-muted-foreground">
                          Next: {new Date(url.nextScheduledRun).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">{url.lastUpdated}</td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex gap-2 items-center">
                      {scrapingUrlId === url.id ? (
                        <button
                          onClick={handleCancelScrape}
                          className="px-3 py-1.5 rounded-lg bg-destructive/20 text-destructive hover:bg-destructive/30 transition-colors text-xs font-medium flex items-center gap-1.5"
                          title="Cancel Scrape"
                        >
                          <X size={14} />
                          Cancel
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStartScrape(url.id)}
                          disabled={scrapingUrlId !== null}
                          className="p-2 rounded-lg hover:bg-accent/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Scrape Now"
                        >
                          <Play size={16} className="text-accent" />
                        </button>
                      )}
                      <button
                        onClick={() => setViewingURL(url)}
                        className="p-2 rounded-lg hover:bg-muted/50 transition-colors"
                        title="View Details"
                      >
                        <Eye size={16} className="text-muted-foreground" />
                      </button>
                      <button
                        onClick={() => deleteURL(url.id)}
                        className="p-2 rounded-lg hover:bg-destructive/20 transition-colors"
                        title="Delete URL"
                      >
                        <Trash2 size={16} className="text-destructive" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {filteredURLs.length > 0 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
            className="p-2 rounded-lg bg-card border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft size={20} className="text-foreground" />
          </button>
          <div className="flex items-center gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
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
            onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
            className="p-2 rounded-lg bg-card border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight size={20} className="text-foreground" />
          </button>
        </div>
      )}

      {viewingURL && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-xl max-w-md w-full p-5 shadow-2xl animate-in fade-in-0 zoom-in-95 duration-200">
            <h2 className="text-lg font-semibold text-foreground mb-4">{viewingURL.dataSource === "file" ? "File Upload Details" : "URL Details"}</h2>
            <div className="space-y-3">
              {viewingURL.dataSource === "file" ? (
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">File Name</label>
                  <div className="flex items-center gap-2 mt-1">
                    <FileText size={16} className="text-accent" />
                    <p className="text-foreground text-sm break-all">{viewingURL.fileName || viewingURL.url}</p>
                  </div>
                  {viewingURL.fileSize && (
                    <p className="text-xs text-muted-foreground mt-1">{formatFileSize(viewingURL.fileSize)}</p>
                  )}
                </div>
              ) : (
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">URL</label>
                  <p className="text-foreground text-sm mt-1 break-all">{viewingURL.url}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Category</label>
                  <p className="text-foreground text-sm mt-1">{viewingURL.category}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">State</label>
                  <p className="text-foreground text-sm mt-1">{viewingURL.state || "N/A"}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Data Source</label>
                  <p className="text-foreground text-sm mt-1 capitalize">
                    {viewingURL.dataSource === "file" ? "File Upload" : viewingURL.dataSource}
                  </p>
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Status</label>
                  <div className="mt-1">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium ${
                      viewingURL.active 
                        ? "bg-emerald-500/10 text-emerald-500" 
                        : "bg-zinc-500/10 text-zinc-400"
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${viewingURL.active ? "bg-emerald-500" : "bg-zinc-500"}`} />
                      {viewingURL.active ? "Active" : "Inactive"}
                    </span>
                  </div>
                </div>
              </div>
              {viewingURL.dataSource === "api" && (
                <div className="space-y-3 pt-1">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">API Endpoint</label>
                    <p className="text-foreground text-sm mt-1 break-all">{viewingURL.apiEndpoint}</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">API Key</label>
                    <p className="text-foreground text-sm mt-1 font-mono">{"*".repeat(16)}</p>
                  </div>
                </div>
              )}
              <div className="space-y-3 pt-1">
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Schedule Frequency</label>
                  <p className="text-foreground text-sm mt-1 capitalize">
                    {viewingURL.scheduleFrequency === "on_demand" ? "On Demand" : viewingURL.scheduleFrequency || "Not set"}
                  </p>
                </div>
                {viewingURL.nextScheduledRun && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Next Scheduled Run</label>
                    <p className="text-foreground text-sm mt-1">{new Date(viewingURL.nextScheduledRun).toLocaleString()}</p>
                  </div>
                )}
                {viewingURL.lastSuccessfulRun && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Last Successful Run</label>
                    <p className="text-foreground text-sm mt-1">{new Date(viewingURL.lastSuccessfulRun).toLocaleString()}</p>
                  </div>
                )}
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Last Updated</label>
                <p className="text-foreground text-sm mt-1">{viewingURL.lastUpdated}</p>
              </div>
            </div>
            <button
              onClick={() => setViewingURL(null)}
              className="mt-5 w-full px-4 py-2.5 rounded-lg bg-accent text-accent-foreground text-sm font-medium hover:bg-accent/90 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* File Limit Warning Modal */}
      {showFileLimitWarning && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-card border border-amber-500/50 rounded-xl max-w-md w-full p-6 shadow-2xl animate-in fade-in-0 zoom-in-95 duration-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-amber-500/20 flex items-center justify-center">
                <AlertCircle size={24} className="text-amber-500" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-foreground">File Limit Reached</h2>
                <p className="text-sm text-muted-foreground">Scraping paused for safety</p>
              </div>
            </div>
            
            <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 mb-4">
              <p className="text-sm text-foreground mb-2">
                <span className="font-semibold">{filesScrapedCount.toLocaleString()}</span> files have been processed,
                reaching the limit of <span className="font-semibold">{maxFilesPerSession.toLocaleString()}</span> files per session.
              </p>
              <p className="text-xs text-muted-foreground">
                This limit helps prevent overwhelming the system and avoids potential bot detection.
              </p>
            </div>

            <div className="flex flex-col gap-2">
              <button
                onClick={() => {
                  // Continue scraping with increased limit
                  setMaxFilesPerSession(maxFilesPerSession + 10000)
                  handleStartScrape(urls[0]?.id || "", true)
                }}
                className="w-full px-4 py-2.5 rounded-lg bg-amber-500/20 text-amber-600 text-sm font-medium hover:bg-amber-500/30 transition-colors border border-amber-500/30"
              >
                Continue (+10,000 more files)
              </button>
              <button
                onClick={() => {
                  setShowFileLimitWarning(false)
                  setFilesScrapedCount(0)
                }}
                className="w-full px-4 py-2.5 rounded-lg bg-muted text-foreground text-sm font-medium hover:bg-muted/80 transition-colors"
              >
                Stop Scraping
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
