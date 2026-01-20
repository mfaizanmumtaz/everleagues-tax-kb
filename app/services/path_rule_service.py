"""Path Rule service for managing URL path blocking/allowing rules."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from ..db_models.path_rule import PathRule, RuleType, RuleSource


class PathRuleService:
    """Service for managing path rules."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create_rule(
        self,
        scrape_url_id: UUID,
        pattern: str,
        rule_type: RuleType = RuleType.BLOCK,
        reason: Optional[str] = None,
        is_regex: bool = False,
        is_glob: bool = True,
        case_sensitive: bool = False,
        priority: int = 0,
        source: RuleSource = RuleSource.MANUAL,
    ) -> PathRule:
        """
        Create a new path rule.
        
        Args:
            scrape_url_id: Parent URL ID
            pattern: Path pattern (glob or regex)
            rule_type: BLOCK or ALLOW
            reason: Reason for the rule
            is_regex: If pattern is regex
            is_glob: If pattern is glob (default)
            case_sensitive: Case-sensitive matching
            priority: Rule priority (higher evaluated first)
            source: Source of the rule
            
        Returns:
            Created PathRule
        """
        rule = PathRule(
            scrape_url_id=scrape_url_id,
            pattern=pattern,
            rule_type=rule_type,
            reason=reason,
            is_regex=is_regex,
            is_glob=is_glob,
            case_sensitive=case_sensitive,
            priority=priority,
            source=source,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def get_rule(self, rule_id: UUID) -> Optional[PathRule]:
        """Get a single rule by ID."""
        result = await self.db.execute(
            select(PathRule).where(PathRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def list_rules(
        self,
        scrape_url_id: UUID,
        rule_type: Optional[RuleType] = None,
        source: Optional[RuleSource] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[PathRule], int]:
        """
        List path rules with filters.
        
        Args:
            scrape_url_id: Parent URL ID
            rule_type: Filter by rule type
            source: Filter by source
            page: Page number
            limit: Items per page
            
        Returns:
            Tuple of (rules list, total count)
        """
        query = select(PathRule).where(PathRule.scrape_url_id == scrape_url_id)
        count_query = select(func.count(PathRule.id)).where(
            PathRule.scrape_url_id == scrape_url_id
        )

        if rule_type is not None:
            query = query.where(PathRule.rule_type == rule_type)
            count_query = count_query.where(PathRule.rule_type == rule_type)
            
        if source is not None:
            query = query.where(PathRule.source == source)
            count_query = count_query.where(PathRule.source == source)

        # Get total
        total = await self.db.execute(count_query)
        total_count = total.scalar() or 0

        # Pagination
        offset = (page - 1) * limit
        query = query.order_by(PathRule.priority.desc(), PathRule.created_at)
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        rules = result.scalars().all()

        return list(rules), total_count

    async def get_all_rules(self, scrape_url_id: UUID) -> List[PathRule]:
        """Get all rules for a URL (for use in crawling)."""
        result = await self.db.execute(
            select(PathRule)
            .where(PathRule.scrape_url_id == scrape_url_id)
            .order_by(PathRule.priority.desc())
        )
        return list(result.scalars().all())

    async def update_rule(
        self,
        rule_id: UUID,
        pattern: Optional[str] = None,
        rule_type: Optional[RuleType] = None,
        reason: Optional[str] = None,
        is_regex: Optional[bool] = None,
        is_glob: Optional[bool] = None,
        case_sensitive: Optional[bool] = None,
        priority: Optional[int] = None,
    ) -> Optional[PathRule]:
        """Update an existing rule."""
        rule = await self.get_rule(rule_id)
        if not rule:
            return None

        if pattern is not None:
            rule.pattern = pattern
        if rule_type is not None:
            rule.rule_type = rule_type
        if reason is not None:
            rule.reason = reason
        if is_regex is not None:
            rule.is_regex = is_regex
        if is_glob is not None:
            rule.is_glob = is_glob
        if case_sensitive is not None:
            rule.case_sensitive = case_sensitive
        if priority is not None:
            rule.priority = priority

        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a rule by ID."""
        result = await self.db.execute(
            delete(PathRule).where(PathRule.id == rule_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def delete_rules_by_source(
        self,
        scrape_url_id: UUID,
        source: RuleSource,
    ) -> int:
        """Delete all rules from a specific source."""
        result = await self.db.execute(
            delete(PathRule)
            .where(PathRule.scrape_url_id == scrape_url_id)
            .where(PathRule.source == source)
        )
        await self.db.commit()
        return result.rowcount

    async def import_from_robots_txt(
        self,
        scrape_url_id: UUID,
        disallowed_paths: List[str],
    ) -> List[PathRule]:
        """
        Import disallowed paths from robots.txt as block rules.
        
        Args:
            scrape_url_id: Parent URL ID
            disallowed_paths: List of disallowed paths from robots.txt
            
        Returns:
            List of created rules
        """
        # First, delete existing robots.txt rules
        await self.delete_rules_by_source(scrape_url_id, RuleSource.ROBOTS_TXT)
        
        created_rules = []
        for path in disallowed_paths:
            rule = await self.create_rule(
                scrape_url_id=scrape_url_id,
                pattern=path if path.endswith("*") else f"{path}*",
                rule_type=RuleType.BLOCK,
                reason="Imported from robots.txt",
                is_glob=True,
                source=RuleSource.ROBOTS_TXT,
            )
            created_rules.append(rule)
        
        return created_rules

    async def add_common_blocks(self, scrape_url_id: UUID) -> List[PathRule]:
        """
        Add common paths that should typically be blocked.
        
        Args:
            scrape_url_id: Parent URL ID
            
        Returns:
            List of created rules
        """
        common_blocks = [
            ("/login*", "Login pages"),
            ("/logout*", "Logout pages"),
            ("/cart*", "Shopping cart"),
            ("/checkout*", "Checkout pages"),
            ("/account*", "User account pages"),
            ("/admin*", "Admin pages"),
            ("/wp-admin*", "WordPress admin"),
            ("/wp-login*", "WordPress login"),
            ("*.css", "Stylesheets"),
            ("*.js", "JavaScript files"),
            ("*.png", "PNG images"),
            ("*.jpg", "JPEG images"),
            ("*.gif", "GIF images"),
            ("*.svg", "SVG images"),
            ("*.ico", "Icon files"),
        ]
        
        created_rules = []
        for pattern, reason in common_blocks:
            rule = await self.create_rule(
                scrape_url_id=scrape_url_id,
                pattern=pattern,
                rule_type=RuleType.BLOCK,
                reason=reason,
                is_glob=True,
                source=RuleSource.AUTO,
                priority=-10,  # Lower priority so manual rules override
            )
            created_rules.append(rule)
        
        return created_rules

    def to_dict(self, rule: PathRule) -> dict:
        """Convert PathRule to dictionary for API response."""
        return {
            "id": str(rule.id),
            "scrape_url_id": str(rule.scrape_url_id),
            "pattern": rule.pattern,
            "rule_type": rule.rule_type.value,
            "reason": rule.reason,
            "is_regex": rule.is_regex,
            "is_glob": rule.is_glob,
            "case_sensitive": rule.case_sensitive,
            "priority": rule.priority,
            "source": rule.source.value,
            "match_count": rule.match_count,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        }
