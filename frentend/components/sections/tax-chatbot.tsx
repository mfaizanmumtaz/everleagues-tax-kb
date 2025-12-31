"use client"

import { useState } from "react"
import { Send, Settings, FileText, Database, ChevronDown, ChevronUp, ExternalLink, BookOpen, BarChart3, Globe, Calendar, Layers, Hash, ArrowRight, SlidersHorizontal } from "lucide-react"

interface RetrievedChunk {
  id: string
  chunkId: string
  documentName: string
  content: string
  relevanceScore: number
  authorityLevel?: 1 | 2 | 3 | 4 | 5 | 6
  taxYear?: number
  sourceUrl?: string
  paragraphNumber?: number
  fileVersion?: string
  sourceDomain?: string
  effectiveFrom?: string
  jurisdiction?: string
  state?: string
  conflictResolutionReason?: "higher_authority" | "more_recent_date" | "jurisdiction_match" | null
  priorityRank?: number
  isPreferred?: boolean
}

interface SourceDocument {
  id: string
  title: string
  category: string
  jurisdiction: string
  url?: string
  excerpt?: string
  authorityLevel?: 1 | 2 | 3 | 4 | 5 | 6
  taxYear?: number
  effectiveFrom?: string
  state?: string
  conflictResolutionReason?: "higher_authority" | "more_recent_date" | "jurisdiction_match" | null
  priorityRank?: number
  isPreferred?: boolean
  chunks?: RetrievedChunk[]
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  sources?: SourceDocument[]
  retrievedChunks?: RetrievedChunk[]
}

const STATES = ["NY", "CA", "NJ", "CT", "MA", "PA"]
const CITIES = ["NYC", "Philadelphia", "Los Angeles", "Chicago", "Houston", "Phoenix", "San Antonio", "San Diego", "Dallas", "San Jose"]
const CATEGORIES = ["forms", "instructions", "faq", "code", "regulations", "bulletins", "sales-tax"]

const RANDOM_SOURCE_NAMES = [
  "Tax Form 1040 Guide",
  "Federal Income Tax Rules",
  "State Sales Tax Code",
  "Business Deduction Manual",
  "Corporate Tax Regulations",
  "Individual Return Instructions",
  "Tax Credit Eligibility",
  "Estimated Tax Payments",
  "Tax Filing Requirements",
  "Deduction Limitations",
]

const MOCK_SOURCE_DOCUMENTS: Record<string, SourceDocument[]> = {
  federal_forms: [
    {
      id: "1",
      title: "Form 1040 - U.S. Individual Income Tax Return",
      category: "forms",
      jurisdiction: "federal",
      excerpt: "The primary form used for reporting individual income tax returns to the IRS.",
    },
    {
      id: "2",
      title: "Form 1099-NEC - Nonemployee Compensation",
      category: "forms",
      jurisdiction: "federal",
      excerpt: "Used to report payments to independent contractors and self-employed individuals.",
    },
  ],
  federal_instructions: [
    {
      id: "3",
      title: "Instructions for Form 1040",
      category: "instructions",
      jurisdiction: "federal",
      excerpt: "Detailed instructions on how to complete your federal income tax return.",
    },
  ],
  federal_regulations: [
    {
      id: "4",
      title: "IRC Section 162 - Trade or Business Expenses",
      category: "regulations",
      jurisdiction: "federal",
      excerpt: "Regulations governing what business expenses are deductible for tax purposes.",
    },
  ],
  NY_forms: [
    {
      id: "5",
      title: "Form IT-201 - New York State Resident Income Tax Return",
      category: "forms",
      jurisdiction: "state",
      excerpt: "New York State's primary form for resident income tax returns.",
    },
  ],
  NY_sales_tax: [
    {
      id: "6",
      title: "New York Sales Tax Guide",
      category: "sales-tax",
      jurisdiction: "state",
      excerpt: "Comprehensive guide to New York sales tax rates and exemptions.",
    },
  ],
  CA_forms: [
    {
      id: "7",
      title: "Form 540 - California Resident Income Tax Return",
      category: "forms",
      jurisdiction: "state",
      excerpt: "California's primary form for resident income tax returns.",
    },
  ],
  CA_sales_tax: [
    {
      id: "8",
      title: "California Sales and Use Tax Guide",
      category: "sales-tax",
      jurisdiction: "state",
      excerpt: "Overview of California sales tax regulations and special tax rates.",
    },
  ],
}

export default function TaxChatbot() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hello! I'm your Tax Document Assistant. How can I help you find tax information today?",
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<"federal" | "state" | "local" | null>(null)
  const [selectedState, setSelectedState] = useState<string | null>(null)
  const [selectedCity, setSelectedCity] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null)
  const [showRetrievalResults, setShowRetrievalResults] = useState<Record<string, boolean>>({})
  const [retrievalResults, setRetrievalResults] = useState<Record<string, RetrievedChunk[]>>({})
  const [showLineage, setShowLineage] = useState<Record<string, boolean>>({})
  
  // Search Quality Controls State
  const [retrievalMode, setRetrievalMode] = useState<"balanced" | "high_recall" | "high_precision">("balanced")
  const [authorityWeightControl, setAuthorityWeightControl] = useState<"strict" | "balanced" | "broad">("balanced")
  const [semanticLexicalBalance, setSemanticLexicalBalance] = useState<number>(0.5)
  const [showSearchControls, setShowSearchControls] = useState<boolean>(false)

  // Helper function to extract domain from URL
  const getDomainFromUrl = (url: string): string => {
    try {
      const urlObj = new URL(url)
      let domain = urlObj.hostname.replace("www.", "")
      // Format common domains
      if (domain === "irs.gov") return "IRS.gov"
      if (domain.includes("cornell.edu")) return "law.cornell.edu"
      if (domain === "govinfo.gov") return "govinfo.gov"
      return domain
    } catch {
      return url
    }
  }

  // Helper function to get conflict resolution reason label
  const getConflictResolutionLabel = (reason: "higher_authority" | "more_recent_date" | "jurisdiction_match" | null | undefined): string => {
    switch (reason) {
      case "higher_authority":
        return "Higher Authority"
      case "more_recent_date":
        return "More Recent Date"
      case "jurisdiction_match":
        return "Jurisdiction Match"
      default:
        return ""
    }
  }

  // Helper function to format effective date
  const formatEffectiveDate = (dateString?: string): string => {
    if (!dateString) return ""
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
    } catch {
      return dateString
    }
  }

  const generateRandomSources = (): SourceDocument[] => {
    const randomCount = Math.floor(Math.random() * 2) + 3 // Random between 3-4
    const sources: SourceDocument[] = []

    for (let i = 0; i < randomCount; i++) {
      const randomName = RANDOM_SOURCE_NAMES[Math.floor(Math.random() * RANDOM_SOURCE_NAMES.length)]
      sources.push({
        id: `random-${Date.now()}-${i}`,
        title: randomName,
        category: selectedCategory || "general",
        jurisdiction: selectedJurisdiction === "federal" ? "federal" : selectedJurisdiction === "state" ? "state" : "local",
      })
    }

    return sources
  }

  const handleJurisdictionSelect = (jurisdiction: "federal" | "state" | "local") => {
    setSelectedJurisdiction(jurisdiction)
    setSelectedState(null)
    setSelectedCity(null)
    setSelectedCategory(null)

    const assistantMessage: Message = {
      id: Date.now().toString(),
      role: "assistant",
      content:
        jurisdiction === "federal"
          ? "You've selected Federal jurisdiction. What category would you like to search? (forms, instructions, faq, code, regulations, bulletins)"
          : jurisdiction === "state"
          ? "You've selected State jurisdiction. Which state would you like to search? (NY, CA, NJ, CT, MA, PA)"
          : "You've selected Local jurisdiction. Which city would you like to search? (NYC, Philadelphia, Los Angeles, Chicago, etc.)",
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, assistantMessage])
  }

  const handleStateSelect = (state: string) => {
    setSelectedState(state)
    setSelectedCategory(null)

    const assistantMessage: Message = {
      id: Date.now().toString(),
      role: "assistant",
      content: `You've selected ${state}. What category would you like to search? (forms, instructions, faq, code, regulations, bulletins, sales-tax)`,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, assistantMessage])
  }

  const handleCitySelect = (city: string) => {
    setSelectedCity(city)
    setSelectedCategory(null)

    const assistantMessage: Message = {
      id: Date.now().toString(),
      role: "assistant",
      content: `You've selected ${city}. What category would you like to search? (forms, instructions, faq, code, regulations, bulletins, sales-tax)`,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, assistantMessage])
  }

  const handleCategorySelect = (category: string) => {
    setSelectedCategory(category)

    const assistantMessage: Message = {
      id: Date.now().toString(),
      role: "assistant",
      content: `Searching for ${category} in ${
        selectedJurisdiction === "federal" 
          ? "Federal" 
          : selectedJurisdiction === "state"
          ? `${selectedState} State`
          : `${selectedCity} Local`
      } documents. What would you like to know?`,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, assistantMessage])
  }

  const generateRetrievedChunks = (): RetrievedChunk[] => {
    // Mock retrieved chunks that would come from RAG retrieval
    // These chunks are shown BEFORE the answer is generated
    // Conflict resolution: Priority 1 = highest authority, Priority 2 = more recent, Priority 3 = jurisdiction match
    const chunks: RetrievedChunk[] = [
      {
        id: "chunk-1",
        chunkId: "chunk_45",
        documentName: "Form_1040_2024.pdf",
        content: "The standard deduction for tax year 2024 is $14,600 for single filers and $29,200 for married couples filing jointly. This amount is adjusted annually for inflation.",
        relevanceScore: 0.95,
        authorityLevel: 2,
        taxYear: 2024,
        sourceUrl: "https://www.irs.gov/forms-pubs/about-form-1040",
        paragraphNumber: 17,
        fileVersion: "2024.1",
        effectiveFrom: "2024-01-01",
        jurisdiction: "federal",
        conflictResolutionReason: "more_recent_date",
        priorityRank: 1,
        isPreferred: true,
      },
      {
        id: "chunk-2",
        chunkId: "chunk_128",
        documentName: "Pub 535 Business Expenses",
        content: "Business expenses are the costs of carrying on a trade or business. These expenses are usually deductible if the business operates to make a profit. Common business expenses include rent, utilities, salaries, and office supplies.",
        relevanceScore: 0.88,
        authorityLevel: 4,
        taxYear: 2024,
        sourceUrl: "https://www.irs.gov/publications/p535",
        paragraphNumber: 23,
        fileVersion: "2024.2",
        effectiveFrom: "2024-01-01",
        jurisdiction: "federal",
        conflictResolutionReason: null,
        priorityRank: 3,
        isPreferred: false,
      },
      {
        id: "chunk-3",
        chunkId: "chunk_67",
        documentName: "Rev Proc 2024-15",
        content: "Revenue Procedure 2024-15 provides guidance on the treatment of certain business expenses and clarifies the deductibility of expenses related to remote work arrangements.",
        relevanceScore: 0.82,
        authorityLevel: 3,
        taxYear: 2024,
        sourceUrl: "https://www.irs.gov/pub/irs-drop/rp-24-15.pdf",
        paragraphNumber: 12,
        fileVersion: "2024.15",
        effectiveFrom: "2024-06-01",
        jurisdiction: "federal",
        conflictResolutionReason: "more_recent_date",
        priorityRank: 2,
        isPreferred: false,
      },
    ]

    // Sort by priority rank (1 = highest priority/preferred)
    const sortedChunks = chunks.sort((a, b) => (a.priorityRank || 999) - (b.priorityRank || 999))

    // Add sourceDomain to each chunk
    return sortedChunks.map((chunk) => ({
      ...chunk,
      sourceDomain: chunk.sourceUrl ? getDomainFromUrl(chunk.sourceUrl) : undefined,
    }))
  }

  const generateDocumentsUsed = (chunks: RetrievedChunk[]): SourceDocument[] => {
    // Extract unique documents from chunks
    // This creates the "Documents Used" list that appears AFTER the answer
    const documentMap = new Map<string, SourceDocument>()
    
    chunks.forEach((chunk) => {
      if (!documentMap.has(chunk.documentName)) {
        // Keep original document name format (Form_1040_2024.pdf, Pub 535 Business Expenses, Rev Proc 2024-15)
        const displayTitle = chunk.documentName.includes("Pub") || chunk.documentName.includes("Rev Proc")
          ? chunk.documentName
          : chunk.documentName.replace(".pdf", "").replace(/_/g, " ")
        
        documentMap.set(chunk.documentName, {
          id: `doc-${chunk.documentName}`,
          title: displayTitle,
          category: selectedCategory || "general",
          jurisdiction: chunk.jurisdiction || (selectedJurisdiction === "federal" ? "federal" : selectedJurisdiction === "state" ? "state" : "local"),
          url: chunk.sourceUrl,
          authorityLevel: chunk.authorityLevel,
          taxYear: chunk.taxYear,
          effectiveFrom: chunk.effectiveFrom,
          state: chunk.state,
          conflictResolutionReason: chunk.conflictResolutionReason,
          priorityRank: chunk.priorityRank,
          isPreferred: chunk.isPreferred,
        })
      }
    })
    
    // Sort by priority rank (preferred documents first)
    return Array.from(documentMap.values()).sort((a, b) => (a.priorityRank || 999) - (b.priorityRank || 999))
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    setIsLoading(true)

    // Prepare search quality controls for API call
    const searchQualityControls = {
      retrieval_mode: retrievalMode,
      authority_weight_control: authorityWeightControl,
      semantic_lexical_balance: semanticLexicalBalance,
    }

    const filters = {
      jurisdiction: selectedJurisdiction || undefined,
      state: selectedState || undefined,
      city: selectedCity || undefined,
      category: selectedCategory ? [selectedCategory] : undefined,
    }

    // TODO: Make actual API call with search quality controls
    // await fetch('/api/search/rag', {
    //   method: 'POST',
    //   body: JSON.stringify({
    //     query: inputValue,
    //     filters,
    //     search_quality_controls: searchQualityControls
    //   })
    // })

    // Simulate RAG retrieval - show chunks BEFORE generating answer
    setTimeout(() => {
      const retrievedChunks = generateRetrievedChunks()
      const messageId = (Date.now() + 1).toString()
      
      // Store retrieval results for this message
      setRetrievalResults((prev) => ({
        ...prev,
        [messageId]: retrievedChunks,
      }))
      setShowRetrievalResults((prev) => ({
        ...prev,
        [messageId]: true, // Show by default
      }))

      // Generate documents used list from chunks
      const documentsUsed = generateDocumentsUsed(retrievedChunks)

      // Generate response with inline citations
      const responseWithCitations = `Based on the retrieved documents, I found relevant information about "${userMessage.content}". Here's what I found:

The standard deduction for tax year 2024 is $14,600 for single filers and $29,200 for married couples filing jointly [1]. Business expenses are deductible if the business operates to make a profit, including rent, utilities, salaries, and office supplies [2]. Revenue Procedure 2024-15 provides additional guidance on the treatment of certain business expenses [3].

These documents provide the most current guidance for tax year 2024.`

      const assistantResponse: Message = {
        id: messageId,
        role: "assistant",
        content: responseWithCitations,
        timestamp: new Date(),
        sources: documentsUsed,
        retrievedChunks: retrievedChunks,
      }
      setMessages((prev) => [...prev, assistantResponse])
      setIsLoading(false)
    }, 800)
  }

  const isInputDisabled = !selectedCategory

  // Render message content with inline citation badges
  const renderContentWithCitations = (content: string, sources?: SourceDocument[]) => {
    if (!sources || sources.length === 0) {
      return <span>{content}</span>
    }
    
    // Split content by citation patterns like [1], [2], etc.
    const parts = content.split(/(\[\d+\])/g)
    
    return (
      <>
        {parts.map((part, index) => {
          const citationMatch = part.match(/\[(\d+)\]/)
          if (citationMatch) {
            const citationNum = parseInt(citationMatch[1])
            const source = sources[citationNum - 1]
            if (source) {
              return (
                <span
                  key={index}
                  className="inline-flex items-center gap-0.5 px-1.5 py-0.5 mx-0.5 rounded bg-accent/20 text-accent text-xs font-medium cursor-pointer hover:bg-accent/30 transition-colors"
                  title={`${source.title} (${source.taxYear || "N/A"}) - Authority Level ${source.authorityLevel || "N/A"}`}
                >
                  {part}
                </span>
              )
            }
          }
          return <span key={index}>{part}</span>
        })}
      </>
    )
  }

  // Mock Knowledge Base Statistics Data
  const kbStatistics = {
    totalDocumentsIndexed: 1247,
    totalChunks: 384256,
    authorityLevelBreakdown: {
      level1: 142,
      level2: 523,
      level3: 198,
      level4: 287,
      level5: 67,
      level6: 30,
    },
    sourcesDistribution: {
      irsGov: 856,
      stateSites: 234,
      lawCornell: 89,
      govInfo: 68,
    },
    freshnessStats: {
      last24h: 12,
      last7Days: 87,
      last30Days: 234,
      staleOver30Days: 27,
    },
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground mb-2">Knowledge Base</h1>
        <p className="text-muted-foreground">
          Query tax documents with intelligent filtering by jurisdiction and category
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chat Area */}
        <div className="lg:col-span-2 flex flex-col">
          {/* Chat Messages */}
          <div className="flex-1 bg-card border border-border rounded-lg p-6 mb-4 overflow-y-auto max-h-[600px] space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className="w-full max-w-2xl">
                  <div
                    className={`px-4 py-2 rounded-lg ${
                      message.role === "user" ? "bg-accent text-accent-foreground" : "bg-muted text-foreground"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">
                      {message.role === "assistant" && message.sources 
                        ? renderContentWithCitations(message.content, message.sources)
                        : message.content
                      }
                    </p>
                    <p className="text-xs opacity-70 mt-1">
                      {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>

                  {/* Citation Sources - Quick Reference */}
                  {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                    <div className="mt-3 p-3 rounded-lg bg-accent/5 border border-accent/20">
                      <p className="text-xs font-semibold text-accent uppercase mb-2 flex items-center gap-1.5">
                        <FileText size={12} />
                        Sources Cited in Response
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {message.sources.map((source, index) => (
                          <div
                            key={source.id}
                            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-card border border-border/50 hover:border-accent/50 transition-colors group"
                          >
                            <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-accent text-accent-foreground">
                              [{index + 1}]
                            </span>
                            <div className="flex flex-col">
                              <span className="text-xs font-medium text-foreground group-hover:text-accent transition-colors">
                                {source.title.length > 40 ? source.title.slice(0, 40) + "..." : source.title}
                              </span>
                              <div className="flex items-center gap-2 mt-0.5">
                                {source.authorityLevel && (
                                  <span className="text-[10px] px-1 py-0.5 rounded bg-blue-500/20 text-blue-600">
                                    Level {source.authorityLevel}
                                  </span>
                                )}
                                {source.taxYear && (
                                  <span className="text-[10px] text-muted-foreground">
                                    {source.taxYear}
                                  </span>
                                )}
                                {source.url && (
                                  <a
                                    href={source.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[10px] text-accent hover:underline flex items-center gap-0.5"
                                  >
                                    <ExternalLink size={8} />
                                    Source
                                  </a>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* RAG Retrieval Results Panel - Shows BEFORE answer */}
                  {message.role === "assistant" && message.retrievedChunks && message.retrievedChunks.length > 0 && (
                    <div className="mt-3 p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
                      <button
                        onClick={() =>
                          setShowRetrievalResults((prev) => ({
                            ...prev,
                            [message.id]: !prev[message.id],
                          }))
                        }
                        className="flex items-center justify-between w-full mb-2"
                      >
                        <div className="flex items-center gap-2">
                          <Database size={16} className="text-blue-600" />
                          <p className="text-sm font-semibold text-foreground">
                            RAG Retrieval Results ({message.retrievedChunks.length} chunks retrieved)
                          </p>
                        </div>
                        {showRetrievalResults[message.id] ? (
                          <ChevronUp size={16} className="text-muted-foreground" />
                        ) : (
                          <ChevronDown size={16} className="text-muted-foreground" />
                        )}
                      </button>
                      {showRetrievalResults[message.id] && (
                        <div className="space-y-3 mt-3">
                          {message.retrievedChunks.map((chunk) => (
                            <div
                              key={chunk.id}
                              className={`p-3 rounded-lg bg-card border ${
                                chunk.isPreferred
                                  ? "border-green-500/50 bg-green-500/5"
                                  : "border-border"
                              }`}
                            >
                              <div className="flex items-start justify-between mb-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <FileText size={14} className="text-accent" />
                                  {chunk.priorityRank && (
                                    <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-accent text-accent-foreground">
                                      #{chunk.priorityRank}
                                    </span>
                                  )}
                                  <span className="text-xs font-semibold text-foreground">
                                    {chunk.documentName}
                                  </span>
                                  {chunk.chunkId && (
                                    <span className="text-xs text-muted-foreground">
                                      (Chunk {chunk.chunkId})
                                    </span>
                                  )}
                                  {chunk.isPreferred && (
                                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-600 border border-green-500/30">
                                      Preferred
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  {chunk.authorityLevel && (
                                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-600">
                                      Level {chunk.authorityLevel}
                                    </span>
                                  )}
                                  <span className="text-xs text-muted-foreground">
                                    {(chunk.relevanceScore * 100).toFixed(0)}% match
                                  </span>
                                </div>
                              </div>
                              {chunk.conflictResolutionReason && (
                                <div className="mb-2">
                                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-600 border border-purple-500/30">
                                    Conflict Resolution: {getConflictResolutionLabel(chunk.conflictResolutionReason)}
                                  </span>
                                </div>
                              )}
                              <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                                {chunk.content}
                              </p>
                              <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                                {chunk.taxYear && (
                                  <span>Tax Year: {chunk.taxYear}</span>
                                )}
                                {chunk.effectiveFrom && (
                                  <span className="flex items-center gap-1">
                                    <Calendar size={12} />
                                    Effective: {formatEffectiveDate(chunk.effectiveFrom)}
                                  </span>
                                )}
                                {chunk.jurisdiction && (
                                  <span className="flex items-center gap-1">
                                    <Globe size={12} />
                                    {chunk.jurisdiction.charAt(0).toUpperCase() + chunk.jurisdiction.slice(1)}
                                    {chunk.state && ` - ${chunk.state}`}
                                  </span>
                                )}
                                {chunk.sourceUrl && (
                                  <a
                                    href={chunk.sourceUrl}
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
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Documents Used Section - Shows AFTER answer */}
                  {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                    <div className="mt-3 p-4 rounded-lg bg-green-500/10 border border-green-500/30">
                      <div className="flex items-center gap-2 mb-3">
                        <BookOpen size={16} className="text-green-600" />
                        <p className="text-sm font-semibold text-foreground">Documents Used</p>
                        <span className="text-xs text-muted-foreground">
                          (Sorted by conflict resolution priority)
                        </span>
                      </div>
                      <div className="space-y-2">
                        {message.sources.map((source) => (
                          <div
                            key={source.id}
                            className={`flex items-center justify-between p-2 rounded-lg border ${
                              source.isPreferred
                                ? "bg-green-500/10 border-green-500/50"
                                : "bg-card border-border/50"
                            }`}
                          >
                            <div className="flex items-center gap-2 flex-1">
                              <FileText size={14} className="text-accent" />
                              <div className="flex-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                  {source.priorityRank && (
                                    <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-accent text-accent-foreground">
                                      #{source.priorityRank}
                                    </span>
                                  )}
                                  <p className="text-sm font-medium text-foreground">{source.title}</p>
                                  {source.isPreferred && (
                                    <span className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-600 border border-green-500/30">
                                      Preferred
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 mt-1 flex-wrap">
                                  {source.taxYear && (
                                    <span className="text-xs text-muted-foreground">
                                      Tax Year: {source.taxYear}
                                    </span>
                                  )}
                                  {source.effectiveFrom && (
                                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                                      <Calendar size={12} />
                                      Effective: {formatEffectiveDate(source.effectiveFrom)}
                                    </span>
                                  )}
                                  {source.authorityLevel && (
                                    <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-600">
                                      Authority Level {source.authorityLevel}
                                    </span>
                                  )}
                                  {source.jurisdiction && (
                                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                                      <Globe size={12} />
                                      {source.jurisdiction.charAt(0).toUpperCase() + source.jurisdiction.slice(1)}
                                      {source.state && ` - ${source.state}`}
                                    </span>
                                  )}
                                  {source.conflictResolutionReason && (
                                    <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-600 border border-purple-500/30">
                                      {getConflictResolutionLabel(source.conflictResolutionReason)}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            {source.url && (
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="ml-2 p-1.5 rounded hover:bg-muted/50 transition-colors"
                                title="View document"
                              >
                                <ExternalLink size={14} className="text-accent" />
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Document Lineage Section - Shows full trace for compliance */}
                  {message.role === "assistant" && message.retrievedChunks && message.retrievedChunks.length > 0 && (
                    <div className="mt-3 p-4 rounded-lg bg-purple-500/10 border border-purple-500/30">
                      <button
                        onClick={() =>
                          setShowLineage((prev) => ({
                            ...prev,
                            [message.id]: !prev[message.id],
                          }))
                        }
                        className="flex items-center justify-between w-full mb-2"
                      >
                        <div className="flex items-center gap-2">
                          <Hash size={16} className="text-purple-600" />
                          <p className="text-sm font-semibold text-foreground">
                            Document Lineage (Compliance Trace)
                          </p>
                        </div>
                        {showLineage[message.id] ? (
                          <ChevronUp size={16} className="text-muted-foreground" />
                        ) : (
                          <ChevronDown size={16} className="text-muted-foreground" />
                        )}
                      </button>
                      {showLineage[message.id] && (
                        <div className="space-y-3 mt-3">
                          <p className="text-xs text-muted-foreground mb-2">
                            Full trace showing where each answer component originated from. Required for PCAOB, IRS Circular 230, HIPAA audits, and legal defensibility. Includes conflict resolution audit trail.
                          </p>
                          {message.retrievedChunks.map((chunk) => (
                            <div
                              key={chunk.id}
                              className={`p-3 rounded-lg bg-card border ${
                                chunk.isPreferred
                                  ? "border-green-500/50 bg-green-500/5"
                                  : "border-border"
                              }`}
                            >
                              <div className="flex items-start gap-2 flex-wrap">
                                {/* Priority Rank */}
                                {chunk.priorityRank && (
                                  <>
                                    <div className="flex items-center gap-1.5">
                                      <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-accent text-accent-foreground">
                                        Priority #{chunk.priorityRank}
                                      </span>
                                      {chunk.isPreferred && (
                                        <span className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-600 border border-green-500/30">
                                          Preferred
                                        </span>
                                      )}
                                    </div>
                                    <ArrowRight size={12} className="text-muted-foreground mt-0.5" />
                                  </>
                                )}
                                
                                {/* Source Domain */}
                                {chunk.sourceDomain && (
                                  <>
                                    <div className="flex items-center gap-1.5">
                                      <Globe size={14} className="text-purple-600" />
                                      <a
                                        href={chunk.sourceUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs font-semibold text-purple-600 hover:underline"
                                      >
                                        {chunk.sourceDomain}
                                      </a>
                                    </div>
                                    <ArrowRight size={12} className="text-muted-foreground mt-0.5" />
                                  </>
                                )}
                                
                                {/* File Name */}
                                <div className="flex items-center gap-1.5">
                                  <FileText size={14} className="text-accent" />
                                  <span className="text-xs font-semibold text-foreground">
                                    {chunk.documentName}
                                  </span>
                                  {chunk.fileVersion && (
                                    <span className="text-xs text-muted-foreground">
                                      (v{chunk.fileVersion})
                                    </span>
                                  )}
                                </div>
                                <ArrowRight size={12} className="text-muted-foreground mt-0.5" />
                                
                                {/* Chunk ID */}
                                <div className="flex items-center gap-1.5">
                                  <Database size={14} className="text-blue-600" />
                                  <span className="text-xs font-semibold text-foreground">
                                    {chunk.chunkId.replace("chunk_", "Chunk ")}
                                  </span>
                                </div>
                                
                                {/* Paragraph Number */}
                                {chunk.paragraphNumber && (
                                  <>
                                    <ArrowRight size={12} className="text-muted-foreground mt-0.5" />
                                    <div className="flex items-center gap-1.5">
                                      <Hash size={14} className="text-green-600" />
                                      <span className="text-xs font-semibold text-foreground">
                                        Paragraph {chunk.paragraphNumber}
                                      </span>
                                    </div>
                                  </>
                                )}
                              </div>
                              
                              {/* Additional Metadata */}
                              <div className="flex items-center gap-3 mt-2 pt-2 border-t border-border/50 flex-wrap">
                                {chunk.taxYear && (
                                  <span className="text-xs text-muted-foreground">
                                    Tax Year: <span className="font-semibold text-foreground">{chunk.taxYear}</span>
                                  </span>
                                )}
                                {chunk.effectiveFrom && (
                                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Calendar size={12} />
                                    Effective: <span className="font-semibold text-foreground">{formatEffectiveDate(chunk.effectiveFrom)}</span>
                                  </span>
                                )}
                                {chunk.jurisdiction && (
                                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Globe size={12} />
                                    {chunk.jurisdiction.charAt(0).toUpperCase() + chunk.jurisdiction.slice(1)}
                                    {chunk.state && ` - ${chunk.state}`}
                                  </span>
                                )}
                                {chunk.authorityLevel && (
                                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-600">
                                    Authority Level {chunk.authorityLevel}
                                  </span>
                                )}
                                {chunk.conflictResolutionReason && (
                                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-600 border border-purple-500/30">
                                    Conflict Resolution: {getConflictResolutionLabel(chunk.conflictResolutionReason)}
                                  </span>
                                )}
                                {chunk.sourceUrl && (
                                  <a
                                    href={chunk.sourceUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-xs text-accent hover:underline"
                                  >
                                    <ExternalLink size={12} />
                                    View Source
                                  </a>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-muted text-foreground px-4 py-2 rounded-lg">
                  <div className="flex gap-2">
                    <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse"></div>
                    <div
                      className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse"
                      style={{ animationDelay: "0.4s" }}
                    ></div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
              disabled={isInputDisabled}
              placeholder={isInputDisabled ? "Select a category first..." : "Ask about tax documents..."}
              className="flex-1 px-4 py-2 rounded-lg bg-background border border-border text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading || isInputDisabled}
              className="px-4 py-2 bg-accent text-accent-foreground rounded-lg hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <Send size={18} />
            </button>
          </div>
        </div>

        {/* Filter Panel */}
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-4 text-foreground font-semibold">
              <Settings size={18} />
              <span>Search Filters</span>
            </div>

            {/* Jurisdiction Selection */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-muted-foreground uppercase">Jurisdiction</p>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => handleJurisdictionSelect("federal")}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedJurisdiction === "federal"
                      ? "bg-accent text-accent-foreground"
                      : "bg-muted text-foreground hover:bg-muted/80"
                  }`}
                >
                  Federal
                </button>
                <button
                  onClick={() => handleJurisdictionSelect("state")}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedJurisdiction === "state"
                      ? "bg-accent text-accent-foreground"
                      : "bg-muted text-foreground hover:bg-muted/80"
                  }`}
                >
                  State
                </button>
                <button
                  onClick={() => handleJurisdictionSelect("local")}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedJurisdiction === "local"
                      ? "bg-accent text-accent-foreground"
                      : "bg-muted text-foreground hover:bg-muted/80"
                  }`}
                >
                  Local
                </button>
              </div>
            </div>

            {/* State Selection (if State is selected) */}
            {selectedJurisdiction === "state" && (
              <div className="space-y-2 mt-4">
                <p className="text-xs font-semibold text-muted-foreground uppercase">Select State</p>
                <div className="grid grid-cols-2 gap-2">
                  {STATES.map((state) => (
                    <button
                      key={state}
                      onClick={() => handleStateSelect(state)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        selectedState === state
                          ? "bg-accent text-accent-foreground"
                          : "bg-muted text-foreground hover:bg-muted/80"
                      }`}
                    >
                      {state}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* City Selection (if Local is selected) */}
            {selectedJurisdiction === "local" && (
              <div className="space-y-2 mt-4">
                <p className="text-xs font-semibold text-muted-foreground uppercase">Select City</p>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {CITIES.map((city) => (
                    <button
                      key={city}
                      onClick={() => handleCitySelect(city)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        selectedCity === city
                          ? "bg-accent text-accent-foreground"
                          : "bg-muted text-foreground hover:bg-muted/80"
                      }`}
                    >
                      {city}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Category Selection (if jurisdiction is selected) */}
            {selectedJurisdiction && (
              <div className="space-y-2 mt-4">
                <p className="text-xs font-semibold text-muted-foreground uppercase">Category</p>
                <div className="space-y-2">
                  {CATEGORIES.map((category) => (
                    <button
                      key={category}
                      onClick={() => handleCategorySelect(category)}
                      className={`w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left capitalize ${
                        selectedCategory === category
                          ? "bg-accent text-accent-foreground"
                          : "bg-muted text-foreground hover:bg-muted/80"
                      }`}
                    >
                      {category}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Selected Filters Display */}
            {selectedJurisdiction && (
              <div className="mt-4 p-3 bg-muted/50 rounded-lg">
                <p className="text-xs text-muted-foreground mb-2">Active Filters:</p>
                <div className="space-y-1 text-sm text-foreground">
                  <p>
                    Jurisdiction: <span className="font-semibold capitalize">{selectedJurisdiction}</span>
                  </p>
                  {selectedState && (
                    <p>
                      State: <span className="font-semibold">{selectedState}</span>
                    </p>
                  )}
                  {selectedCity && (
                    <p>
                      City: <span className="font-semibold">{selectedCity}</span>
                    </p>
                  )}
                  {selectedCategory && (
                    <p>
                      Category: <span className="font-semibold capitalize">{selectedCategory}</span>
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Search Quality Controls Panel */}
          <div className="bg-card border border-border rounded-lg p-4 mt-4">
            <button
              onClick={() => setShowSearchControls(!showSearchControls)}
              className="flex items-center justify-between w-full mb-2"
            >
              <div className="flex items-center gap-2 text-foreground font-semibold">
                <SlidersHorizontal size={18} />
                <span>Search Quality Controls</span>
              </div>
              {showSearchControls ? (
                <ChevronUp size={16} className="text-muted-foreground" />
              ) : (
                <ChevronDown size={16} className="text-muted-foreground" />
              )}
            </button>

            {showSearchControls && (
              <div className="space-y-4 mt-4">
                {/* Retrieval Mode */}
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-muted-foreground uppercase">Retrieval Mode</p>
                  <div className="space-y-2">
                    {[
                      { value: "balanced", label: "Balanced", desc: "Balanced approach between precision and recall" },
                      { value: "high_recall", label: "High Recall", desc: "Prioritize finding all relevant documents" },
                      { value: "high_precision", label: "High Precision", desc: "Prioritize exact matches" },
                    ].map((mode) => (
                      <button
                        key={mode.value}
                        onClick={() => setRetrievalMode(mode.value as any)}
                        className={`w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left ${
                          retrievalMode === mode.value
                            ? "bg-accent text-accent-foreground"
                            : "bg-muted text-foreground hover:bg-muted/80"
                        }`}
                      >
                        <div className="font-semibold">{mode.label}</div>
                        <div className="text-xs opacity-70 mt-0.5">{mode.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Authority Weight Control */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-muted-foreground uppercase">Authority Weight Control</p>
                    <span className="text-xs text-foreground font-medium capitalize">{authorityWeightControl}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-12">Strict</span>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="1"
                      value={authorityWeightControl === "strict" ? 0 : authorityWeightControl === "balanced" ? 1 : 2}
                      onChange={(e) => {
                        const val = parseInt(e.target.value)
                        setAuthorityWeightControl(val === 0 ? "strict" : val === 1 ? "balanced" : "broad")
                      }}
                      className="flex-1"
                    />
                    <span className="text-xs text-muted-foreground w-12 text-right">Broad</span>
                  </div>
                  <div className="text-xs text-muted-foreground px-1">
                    {authorityWeightControl === "strict" && "Heavily favor high-authority sources (Level 1-2)"}
                    {authorityWeightControl === "balanced" && "Moderate authority bias (default)"}
                    {authorityWeightControl === "broad" && "Minimal authority bias, include lower-authority sources"}
                  </div>
                </div>

                {/* Semantic + Lexical Balance Slider */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-muted-foreground uppercase">Semantic / Lexical Balance</p>
                    <span className="text-xs text-foreground font-medium">
                      {semanticLexicalBalance < 0.3 ? "Lexical" : semanticLexicalBalance > 0.7 ? "Semantic" : "Balanced"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-16">Lexical (0.0)</span>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={semanticLexicalBalance}
                      onChange={(e) => setSemanticLexicalBalance(parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-xs text-muted-foreground w-16 text-right">Semantic (1.0)</span>
                  </div>
                  <div className="text-xs text-muted-foreground px-1">
                    {semanticLexicalBalance.toFixed(1)} - {semanticLexicalBalance < 0.3 
                      ? "More keyword/exact matching" 
                      : semanticLexicalBalance > 0.7 
                      ? "More semantic/meaning-based matching"
                      : "Balanced between keyword and semantic matching"}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Knowledge Base Statistics Panel */}
          <div className="bg-card border border-border rounded-lg p-4 mt-4">
            <div className="flex items-center gap-2 mb-4 text-foreground font-semibold">
              <BarChart3 size={18} />
              <span>Knowledge Base Statistics</span>
            </div>

            {/* Total Documents Indexed */}
            <div className="mb-4 pb-4 border-b border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">Total Documents Indexed</span>
                <span className="text-lg font-bold text-foreground">
                  {kbStatistics.totalDocumentsIndexed.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Chunks</span>
                <span className="text-lg font-bold text-foreground">
                  {kbStatistics.totalChunks.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Authority Level Breakdown */}
            <div className="mb-4 pb-4 border-b border-border">
              <p className="text-xs font-semibold text-muted-foreground uppercase mb-3">
                Authority Level Breakdown
              </p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                    <span className="text-xs text-foreground">Level 1 - Statute/Reg</span>
                  </div>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.authorityLevelBreakdown.level1}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    <span className="text-xs text-foreground">Level 2 - Forms/Instructions</span>
                  </div>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.authorityLevelBreakdown.level2}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                    <span className="text-xs text-foreground">Level 3 - Rulings/Procedures</span>
                  </div>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.authorityLevelBreakdown.level3}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                    <span className="text-xs text-foreground">Level 4 - FAQs/Publications</span>
                  </div>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.authorityLevelBreakdown.level4}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                    <span className="text-xs text-foreground">Level 5 - Expert Sources</span>
                  </div>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.authorityLevelBreakdown.level5}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-gray-500"></div>
                    <span className="text-xs text-foreground">Level 6 - Other/Low Authority</span>
                  </div>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.authorityLevelBreakdown.level6}
                  </span>
                </div>
              </div>
            </div>

            {/* Sources Distribution */}
            <div className="mb-4 pb-4 border-b border-border">
              <p className="text-xs font-semibold text-muted-foreground uppercase mb-3 flex items-center gap-1">
                <Globe size={12} />
                Sources Distribution
              </p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground">irs.gov</span>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.sourcesDistribution.irsGov}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground">State Sites</span>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.sourcesDistribution.stateSites}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground">law.cornell.edu</span>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.sourcesDistribution.lawCornell}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground">govinfo.gov</span>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.sourcesDistribution.govInfo}
                  </span>
                </div>
              </div>
            </div>

            {/* Freshness Stats */}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase mb-3 flex items-center gap-1">
                <Calendar size={12} />
                Freshness Stats
              </p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground">Last 24h</span>
                  <span className="text-sm font-semibold text-green-600">
                    {kbStatistics.freshnessStats.last24h}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground">Last 7 Days</span>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.freshnessStats.last7Days}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground">Last 30 Days</span>
                  <span className="text-sm font-semibold text-foreground">
                    {kbStatistics.freshnessStats.last30Days}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-foreground">Stale &gt; 30 Days</span>
                  <span className="text-sm font-semibold text-yellow-600">
                    {kbStatistics.freshnessStats.staleOver30Days}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
