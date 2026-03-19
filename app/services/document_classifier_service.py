"""Document Classification Service using AI.

This service provides AI-powered document classification and metadata extraction.
It can be used by any module that needs to classify documents:
- File uploads
- Web scraping
- API imports
- Bulk ingestion

The service analyzes document text and extracts:
- Title
- Description
- Document type
- Authority level
- Tags
- Tax year (if applicable)
"""

import logging
import re
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum

from pydantic import BaseModel, Field as PydanticField

from ..config import settings
from ..prompts import get_classifier_system_prompt, get_classifier_user_prompt

logger = logging.getLogger(__name__)


class DocType(str, Enum):
    """Document type classifications."""

    FORM = "form"
    INSTRUCTIONS = "instructions"
    PUBLICATION = "publication"
    SCHEDULE = "schedule"
    REGULATION = "regulation"
    RULING = "ruling"
    NOTICE = "notice"
    FAQ = "faq"
    GUIDE = "guide"
    OTHER = "other"


@dataclass
class ClassificationResult:
    """Result of document classification.

    This is a data class that can be easily converted to dict
    and used by any consumer module.
    """

    title: Optional[str] = None
    description: Optional[str] = None
    doc_type: Optional[str] = None
    authority_level: Optional[int] = None
    authority_level_rationale: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    tax_year: Optional[int] = None
    form_family: Optional[str] = None
    confidence: float = 0.0  # Overall confidence score 0-1

    # Source of classification
    classified_by: str = "ai"  # "ai", "rules", "manual"
    classification_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy integration."""
        return asdict(self)

    def is_valid(self) -> bool:
        """Check if classification has minimum required fields."""
        return self.title is not None or self.doc_type is not None


class DocumentClassifierService:
    """AI-powered document classification service.

    This service is designed to be modular and reusable:
    - Used by upload module for file classification
    - Used by scraping module for web document classification
    - Can be extended with custom classification rules

    Classification sources (in order of priority):
    1. AI (OpenAI GPT-4) - Most accurate
    2. URL pattern matching - For authority level
    3. Filename pattern matching - For doc_type
    4. Text pattern matching - For tax year, tags
    """

    # URL patterns for authority level detection.
    # Based on the official US tax law authority hierarchy:
    #   1 = IRC / Constitution / Tax Treaties  (statutory primary authority)
    #   2 = Treasury Regulations               (administrative primary authority)
    #   3 = IRS Published Guidance in IRB      (Rev. Rulings, Rev. Procs, Notices, Announcements)
    #   4 = IRS Forms, Publications, IRM, Written Determinations (PLR/TAM/CCA)
    #   5 = Federal case law + State primary authorities
    #   6 = Secondary sources (Big-4, journals, treatises, general web)
    AUTHORITY_PATTERNS = {
        1: [  # Level 1 — IRC / U.S. Constitution / Tax Treaties (Statutory Primary)
            r"uscode\.house\.gov/browse/prelim@title26",
            r"govinfo\.gov/app/collection/uscode",
            r"law\.cornell\.edu/uscode/text/26",
            r"constitution\.congress\.gov",
            r"irs\.gov/businesses/international-businesses/united-states-income-tax-treaties",
        ],
        2: [  # Level 2 — Treasury Regulations / CFR Title 26 (Administrative Primary)
            r"ecfr\.gov/current/title-26",
            r"govinfo\.gov/app/collection/cfr",
            r"law\.cornell\.edu/cfr/text/26",
            r"federalregister\.gov",
            r"treasury\.gov/resource-center/tax-policy",
        ],
        3: [  # Level 3 — IRS Published Guidance in IRB (Rev. Rulings, Rev. Procs, Notices)
            r"irs\.gov/irb/",
            r"irs\.gov/internal-revenue-bulletins",
            r"irs\.gov/pub/irs-drop/rr-",        # Revenue Rulings
            r"irs\.gov/pub/irs-drop/rp-",        # Revenue Procedures
            r"irs\.gov/pub/irs-drop/n-",         # Notices
            r"irs\.gov/pub/irs-drop/a-",         # Announcements
        ],
        4: [  # Level 4 — IRS Forms/Publications/IRM + Written Determinations (PLR/TAM/CCA)
            r"irs\.gov/forms-instructions",
            r"irs\.gov/pub/irs-pdf/",
            r"irs\.gov/publications/",
            r"irs\.gov/pub/irs-prior/",
            r"irs\.gov/irm/",
            r"irs\.gov/pub/irs-wd/",             # PLRs, TAMs, CCAs, FSAs
            r"irs\.gov/privacy-disclosure/foia-library",
            r"irs\.gov/actions-on-decisions",
            r"irs\.gov/faqs",
        ],
        5: [  # Level 5 — Federal Case Law + State Primary Tax Authorities
            # Federal courts
            r"ustaxcourt\.gov",
            r"supremecourt\.gov",
            r"uscfc\.uscourts\.gov",
            r"uscourts\.gov",
            r"law\.justia\.com/cases/federal/",
            r"casetext\.com",
            # California
            r"ftb\.ca\.gov",
            r"cdtfa\.ca\.gov",
            r"boe\.ca\.gov",
            # New York
            r"tax\.ny\.gov",
            # Texas
            r"comptroller\.texas\.gov/taxes",
            # Florida
            r"floridarevenue\.com",
            # Illinois
            r"tax\.illinois\.gov",
            # Other major state revenue agencies
            r"revenue\.state\.",
            r"dor\.",
            r"department\.of\.revenue\.",
        ],
        6: [  # Level 6 — Secondary / Professional / General Web (No binding authority)
            # Big-4 and professional firms
            r"kpmg\.com",
            r"deloitte\.com",
            r"pwc\.com",
            r"ey\.com",
            r"answerconnect\.cch\.com",
            r"checkpoint\.thomsonreuters\.com",
            r"bloomberglaw\.com",
            r"taxnotes\.com",
            r"viewpoint\.pwc\.com",
            # News / general commentary
            r"forbes\.com",
            r"wsj\.com",
            r"cnbc\.com",
            r"bloomberg\.com",
            r"wikipedia\.org",
            r"medium\.com",
            r"reddit\.com",
            r"quora\.com",
            r"linkedin\.com/pulse",
            r"[./]blog[./]",
        ],
    }

    # Filename patterns for doc_type detection
    DOC_TYPE_PATTERNS = {
        "form": [r"form[\s_-]?\d", r"f\d{3,4}", r"w-\d", r"1099", r"1040", r"540"],
        "instructions": [r"instructions?", r"inst", r"i\d{3,4}"],
        "schedule": [r"schedule[\s_-]?[a-z]", r"sch[\s_-]?[a-z]"],
        "publication": [r"pub[\s_-]?\d", r"publication"],
        "regulation": [r"reg[\s_-]?", r"cfr", r"treasury"],
        "ruling": [r"rev[\s_-]?rul", r"ruling"],
        "notice": [r"notice[\s_-]?\d", r"ann[\s_-]?\d"],
    }

    # Tax year patterns
    TAX_YEAR_PATTERNS = [
        r"tax\s*year\s*(\d{4})",
        r"(\d{4})\s*tax\s*year",
        r"for\s*(\d{4})",
        r"fy\s*(\d{4})",
        r"(?:19|20)(\d{2})\s*(?:form|return|filing)",
    ]

    def __init__(self, use_ai: bool = True, openai_api_key: str = None):
        """Initialize the classifier.

        Args:
            use_ai: Whether to use AI for classification (requires OpenAI API key)
            openai_api_key: OpenAI API key (uses settings if not provided)
        """
        self.use_ai = use_ai
        self.api_key = openai_api_key or settings.openai_api_key
        self.model = settings.classifier_llm_model
        self.temperature = settings.classifier_llm_temperature
        self.max_tokens = settings.classifier_llm_max_tokens
        self._client = None

    def _get_langchain_client(self):
        """Lazy-load a ChatOpenAI instance for structured output."""
        if self._client is None and self.use_ai and self.api_key:
            try:
                from langchain_openai import ChatOpenAI
                self._client = ChatOpenAI(
                    api_key=self.api_key,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except ImportError:
                raise RuntimeError("langchain-openai package is required for AI classification")
        return self._client

    def classify(
        self,
        text: str,
        source_url: Optional[str] = None,
        filename: Optional[str] = None,
        existing_metadata: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """Classify a document and extract metadata.

        This is the main entry point for classification.
        It combines AI classification with rule-based fallbacks.

        Args:
            text: Document text content
            source_url: Optional source URL (for authority detection)
            filename: Optional filename (for doc_type detection)
            existing_metadata: Optional existing metadata to preserve

        Returns:
            ClassificationResult with extracted metadata
        """
        result = ClassificationResult()
        errors = []

        logger.debug(
            "classify start: filename=%s, text_len=%s",
            filename, len(text) if text else 0,
        )

        # Initialize with existing metadata if provided
        if existing_metadata:
            result = self._apply_existing_metadata(result, existing_metadata)

        # Try AI classification first
        if self.use_ai and self.api_key:
            try:
                ai_result = self._classify_with_ai(text, source_url, filename)
                result = self._merge_results(result, ai_result)
                result.classified_by = "ai"
            except Exception as e:
                errors.append(f"AI classification failed: {str(e)}")
                result.classified_by = "rules"
                logger.warning(
                    "classify ai_fallback: filename=%s, error=%s",
                    filename, str(e),
                )
        else:
            result.classified_by = "rules"

        # Apply rule-based classification for missing fields
        result = self._apply_rule_based_classification(
            result, text, source_url, filename
        )

        # Calculate overall confidence
        result.confidence = self._calculate_confidence(result)
        result.classification_errors = errors

        logger.info(
            "classify done: filename=%s, by=%s, title=%s, doc_type=%s, confidence=%.2f",
            filename, result.classified_by, result.title, result.doc_type, result.confidence,
        )
        return result

    def _classify_with_ai(
        self,
        text: str,
        source_url: Optional[str],
        filename: Optional[str],
    ) -> ClassificationResult:
        """Classify a document using LangChain with_structured_output.

        with_structured_output binds a Pydantic schema to the model using
        OpenAI's native JSON schema enforcement. The model cannot return
        invalid field values — no manual JSON parsing or validation needed.
        """
        llm = self._get_langchain_client()
        if not llm:
            raise RuntimeError("LangChain OpenAI client not available")

        # Pydantic schema for with_structured_output.
        # OpenAI enforces all constraints (Literal, ge/le, Optional) at the
        # API level so the response is always a valid instance.
        class ClassificationSchema(BaseModel):
            """Structured metadata extracted from a US tax document."""

            title: Optional[str] = PydanticField(
                default=None,
                description="Document title extracted from content or derived from filename",
            )
            description: Optional[str] = PydanticField(
                default=None,
                description="Brief 1-2 sentence summary of what the document covers",
            )
            doc_type: Optional[Literal[
                "form", "instructions", "publication", "schedule",
                "regulation", "ruling", "notice", "faq", "guide", "other",
            ]] = PydanticField(
                default=None,
                description="Document type — must be exactly one of the listed values",
            )
            authority_level: Optional[int] = PydanticField(
                default=None,
                ge=1,
                le=6,
                description=(
                    "US tax authority level 1-6: "
                    "1=IRC/Constitution/Tax Treaties, "
                    "2=Treasury Regulations (CFR Title 26), "
                    "3=IRS IRB Guidance (Rev. Ruling / Rev. Proc. / Notice / Announcement), "
                    "4=IRS Forms / Publications / IRM / PLR / TAM, "
                    "5=Federal Case Law or State Primary Authority (FTB/CDTFA/NY DTF/etc.), "
                    "6=Secondary/Professional/General Web"
                ),
            )
            authority_level_rationale: Optional[str] = PydanticField(
                default=None,
                description="Brief explanation of why this authority level was assigned",
            )
            tags: List[str] = PydanticField(
                default_factory=list,
                description="Up to 4 relevant keyword tags",
            )
            tax_year: Optional[int] = PydanticField(
                default=None,
                ge=1990,
                le=2100,
                description="Tax year as integer if mentioned in the document, null otherwise",
            )
            form_family: Optional[str] = PydanticField(
                default=None,
                description="Form family identifier e.g. '1040', 'SchC', 'W-2' if applicable",
            )

        # Build text window: start (12000 chars) + end (4000 chars) = ~16000 chars / ~4000 tokens.
        # Start captures title, header, authority declaration, and opening sections.
        # End captures conclusions, effective dates, and signatures.
        if len(text) > 16000:
            truncated_text = (
                text[:12000]
                + "\n\n...[sections omitted]...\n\n"
                + text[-4000:]
            )
        else:
            truncated_text = text

        system_prompt = get_classifier_system_prompt()
        user_prompt = get_classifier_user_prompt(
            document_text=truncated_text,
            source_url=source_url,
            filename=filename,
        )

        try:
            structured_llm = llm.with_structured_output(ClassificationSchema)
            data: ClassificationSchema = structured_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ])

            return ClassificationResult(
                title=data.title or None,
                description=data.description or None,
                doc_type=data.doc_type,
                authority_level=data.authority_level,
                authority_level_rationale=data.authority_level_rationale or None,
                tags=data.tags,
                tax_year=data.tax_year,
                form_family=data.form_family or None,
            )

        except Exception as e:
            raise RuntimeError(f"LangChain structured output error: {e}")

    def _apply_rule_based_classification(
        self,
        result: ClassificationResult,
        text: str,
        source_url: Optional[str],
        filename: Optional[str],
    ) -> ClassificationResult:
        """Apply rule-based classification for missing fields."""

        # Extract authority level from URL if not set
        if result.authority_level is None and source_url:
            level, rationale = self._detect_authority_from_url(source_url)
            if level:
                result.authority_level = level
                result.authority_level_rationale = rationale

        # Extract doc_type from filename if not set
        if result.doc_type is None and filename:
            result.doc_type = self._detect_doc_type_from_filename(filename)

        # Extract doc_type from text if still not set
        if result.doc_type is None:
            result.doc_type = self._detect_doc_type_from_text(text)

        # Extract tax year if not set
        if result.tax_year is None:
            result.tax_year = self._detect_tax_year(text, filename)

        # Extract title from filename if not set
        if result.title is None and filename:
            result.title = self._derive_title_from_filename(filename)

        # Generate basic tags if empty
        if not result.tags:
            result.tags = self._extract_basic_tags(text, filename)

        return result

    def _detect_authority_from_url(self, url: str) -> tuple:
        """Detect authority level from URL patterns."""
        url_lower = url.lower()

        for level, patterns in self.AUTHORITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    rationale = f"URL matches {pattern} pattern"
                    return level, rationale

        return None, None

    def _detect_doc_type_from_filename(self, filename: str) -> Optional[str]:
        """Detect document type from filename patterns."""
        filename_lower = filename.lower()

        for doc_type, patterns in self.DOC_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower):
                    return doc_type

        return None

    def _detect_doc_type_from_text(self, text: str) -> Optional[str]:
        """Detect document type from text content."""
        text_lower = text[:2000].lower()  # Check first 2000 chars

        if any(word in text_lower for word in ["form", "tax return", "fill in"]):
            return "form"
        if "instructions" in text_lower:
            return "instructions"
        if "publication" in text_lower:
            return "publication"
        if any(word in text_lower for word in ["regulation", "treasury"]):
            return "regulation"
        if any(word in text_lower for word in ["faq", "frequently asked"]):
            return "faq"

        return "other"

    def _detect_tax_year(self, text: str, filename: Optional[str]) -> Optional[int]:
        """Extract tax year from text or filename."""
        # Check filename first
        if filename:
            match = re.search(r"(20\d{2}|19\d{2})", filename)
            if match:
                year = int(match.group(1))
                if 1990 <= year <= 2100:
                    return year

        # Check text
        for pattern in self.TAX_YEAR_PATTERNS:
            match = re.search(pattern, text[:5000], re.IGNORECASE)
            if match:
                year_str = match.group(1)
                if len(year_str) == 2:
                    year = (
                        int(f"20{year_str}")
                        if int(year_str) < 50
                        else int(f"19{year_str}")
                    )
                else:
                    year = int(year_str)
                if 1990 <= year <= 2100:
                    return year

        return None

    def _derive_title_from_filename(self, filename: str) -> str:
        """Create a title from filename."""
        # Remove extension
        name = re.sub(r"\.[a-zA-Z]+$", "", filename)

        # Replace underscores and hyphens with spaces
        name = re.sub(r"[_-]", " ", name)

        # Capitalize words
        name = name.title()

        return name

    def _extract_basic_tags(self, text: str, filename: Optional[str]) -> List[str]:
        """Extract basic tags from content."""
        tags = []
        text_lower = text[:5000].lower()

        # Tax type tags
        if any(word in text_lower for word in ["income tax", "income return"]):
            tags.append("income-tax")
        if any(word in text_lower for word in ["sales tax", "sales and use"]):
            tags.append("sales-tax")
        if any(word in text_lower for word in ["property tax"]):
            tags.append("property-tax")
        if any(
            word in text_lower for word in ["payroll", "employment tax", "w-2", "w-4"]
        ):
            tags.append("payroll-tax")

        # Form number tags
        if filename:
            form_match = re.search(
                r"(form[\s_-]?\d+[a-z]*|[fw]-\d+|\d{4})", filename, re.IGNORECASE
            )
            if form_match:
                tags.append(form_match.group(1).lower().replace(" ", "-"))

        # Jurisdiction tags
        if "federal" in text_lower or "irs" in text_lower:
            tags.append("federal")
        if "california" in text_lower or "ftb" in text_lower:
            tags.append("california")
        if "new york" in text_lower:
            tags.append("new-york")

        return list(set(tags))  # Remove duplicates

    def _apply_existing_metadata(
        self,
        result: ClassificationResult,
        existing: Dict[str, Any],
    ) -> ClassificationResult:
        """Preserve existing metadata that shouldn't be overwritten."""
        if existing.get("title"):
            result.title = existing["title"]
        if existing.get("description"):
            result.description = existing["description"]
        if existing.get("doc_type"):
            result.doc_type = existing["doc_type"]
        if existing.get("authority_level"):
            result.authority_level = existing["authority_level"]
        if existing.get("tags"):
            result.tags = existing["tags"]
        if existing.get("tax_year"):
            result.tax_year = existing["tax_year"]
        if existing.get("form_family"):
            result.form_family = existing["form_family"]
        return result

    def _merge_results(
        self,
        base: ClassificationResult,
        ai: ClassificationResult,
    ) -> ClassificationResult:
        """Merge AI results with base, preferring AI for empty fields."""
        return ClassificationResult(
            title=base.title or ai.title,
            description=base.description or ai.description,
            doc_type=base.doc_type or ai.doc_type,
            authority_level=base.authority_level or ai.authority_level,
            authority_level_rationale=base.authority_level_rationale
            or ai.authority_level_rationale,
            tags=base.tags if base.tags else ai.tags,
            tax_year=base.tax_year or ai.tax_year,
            form_family=base.form_family or ai.form_family,
        )

    def _calculate_confidence(self, result: ClassificationResult) -> float:
        """Calculate overall confidence score based on filled fields."""
        score = 0.0
        max_score = 7.0  # 7 fields to check (jurisdiction excluded - user-provided)

        if result.title:
            score += 1.0
        if result.description:
            score += 1.0
        if result.doc_type:
            score += 1.0
        if result.authority_level:
            score += 1.0
        if result.authority_level_rationale:
            score += 0.5
        if result.tags:
            score += 1.0
        if result.tax_year:
            score += 1.0

        return min(score / max_score, 1.0)


# Singleton instance
_classifier_service: Optional[DocumentClassifierService] = None


def get_document_classifier_service(use_ai: bool = True) -> DocumentClassifierService:
    """Get or create the DocumentClassifierService singleton.

    Args:
        use_ai: Whether to use AI classification

    Returns:
        DocumentClassifierService instance
    """
    global _classifier_service
    if _classifier_service is None or _classifier_service.use_ai != use_ai:
        _classifier_service = DocumentClassifierService(use_ai=use_ai)
    return _classifier_service
