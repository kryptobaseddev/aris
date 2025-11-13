"""URL complexity analysis for intelligent extraction routing.

Determines whether a URL should be extracted using:
- Tavily Extract API (simple static content)
- Playwright MCP (complex JavaScript-heavy content)

Analyzes URL patterns, domain characteristics, and content indicators.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class ExtractionMethod(str, Enum):
    """Recommended extraction method."""

    TAVILY_EXTRACT = "tavily_extract"  # Simple static content
    PLAYWRIGHT = "playwright"  # Complex dynamic content
    TAVILY_SEARCH = "tavily_search"  # Use search snippet instead


@dataclass
class ComplexityIndicators:
    """Individual complexity indicators."""

    has_javascript: bool = False  # Likely JavaScript-rendered content
    requires_auth: bool = False  # Authentication required
    is_social_media: bool = False  # Social media platform
    is_dynamic: bool = False  # Dynamic/infinite scroll content
    is_paywall: bool = False  # Content behind paywall
    is_pdf: bool = False  # PDF document
    has_fragment: bool = False  # URL has fragment identifier (#)


@dataclass
class ComplexityAnalysis:
    """Complete URL complexity analysis."""

    url: str
    score: int  # 0-7, higher = more complex
    indicators: ComplexityIndicators
    recommended_method: ExtractionMethod
    confidence: float  # 0.0-1.0
    reasoning: str


class ComplexityAnalyzer:
    """Analyzes URL complexity to route extraction appropriately.

    Example:
        analyzer = ComplexityAnalyzer()
        analysis = analyzer.analyze_url("https://example.com/article")
        if analysis.recommended_method == ExtractionMethod.PLAYWRIGHT:
            content = await playwright_extract(url)
        else:
            content = await tavily_extract(url)
    """

    # JavaScript-heavy frameworks/platforms
    JS_PATTERNS = [
        "app",
        "spa",
        "react",
        "vue",
        "angular",
        "next",
        "nuxt",
        "svelte",
    ]

    # Authentication indicators
    AUTH_PATTERNS = [
        "login",
        "signin",
        "auth",
        "account",
        "dashboard",
        "settings",
        "admin",
    ]

    # Social media domains
    SOCIAL_DOMAINS = [
        "twitter.com",
        "x.com",
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "reddit.com",
        "tiktok.com",
        "youtube.com",
    ]

    # Dynamic content indicators
    DYNAMIC_PATTERNS = [
        "infinite",
        "scroll",
        "lazy",
        "dynamic",
        "stream",
        "feed",
        "timeline",
    ]

    # Paywall indicators
    PAYWALL_DOMAINS = [
        "nytimes.com",
        "wsj.com",
        "ft.com",
        "bloomberg.com",
        "economist.com",
    ]

    # Simple static content domains (high confidence for Tavily Extract)
    STATIC_DOMAINS = [
        "wikipedia.org",
        "github.com",
        "stackoverflow.com",
        "medium.com",
        "docs.python.org",
        "developer.mozilla.org",
    ]

    def analyze_url(self, url: str) -> ComplexityAnalysis:
        """Analyze URL complexity and recommend extraction method.

        Args:
            url: URL to analyze

        Returns:
            ComplexityAnalysis with recommendations
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        query = parsed.query.lower()
        fragment = parsed.fragment

        indicators = ComplexityIndicators()

        # Check JavaScript indicators
        indicators.has_javascript = any(
            pattern in path or pattern in domain for pattern in self.JS_PATTERNS
        )

        # Check authentication indicators
        indicators.requires_auth = any(
            pattern in path for pattern in self.AUTH_PATTERNS
        )

        # Check social media
        indicators.is_social_media = any(
            social_domain in domain for social_domain in self.SOCIAL_DOMAINS
        )

        # Check dynamic content
        indicators.is_dynamic = (
            any(pattern in path or pattern in query for pattern in self.DYNAMIC_PATTERNS)
            or "page=" in query
        )

        # Check paywall
        indicators.is_paywall = any(
            paywall_domain in domain for paywall_domain in self.PAYWALL_DOMAINS
        )

        # Check PDF
        indicators.is_pdf = path.endswith(".pdf")

        # Check fragment
        indicators.has_fragment = bool(fragment)

        # Calculate complexity score (0-7)
        score = sum(
            [
                indicators.has_javascript,
                indicators.requires_auth,
                indicators.is_social_media,
                indicators.is_dynamic,
                indicators.is_paywall,
                indicators.is_pdf,
                indicators.has_fragment,
            ]
        )

        # Determine recommended method
        method, confidence, reasoning = self._recommend_method(
            score, indicators, domain, path
        )

        return ComplexityAnalysis(
            url=url,
            score=score,
            indicators=indicators,
            recommended_method=method,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _recommend_method(
        self,
        score: int,
        indicators: ComplexityIndicators,
        domain: str,
        path: str,
    ) -> tuple[ExtractionMethod, float, str]:
        """Determine recommended extraction method.

        Args:
            score: Complexity score (0-7)
            indicators: Complexity indicators
            domain: URL domain
            path: URL path

        Returns:
            Tuple of (method, confidence, reasoning)
        """
        # High confidence for static domains
        if any(static_domain in domain for static_domain in self.STATIC_DOMAINS):
            return (
                ExtractionMethod.TAVILY_EXTRACT,
                0.95,
                f"Domain {domain} known for static content",
            )

        # PDFs should use Tavily Extract (returns metadata + text)
        if indicators.is_pdf:
            return (
                ExtractionMethod.TAVILY_EXTRACT,
                0.90,
                "PDF documents handled well by Tavily Extract",
            )

        # Authentication required → cannot extract
        if indicators.requires_auth:
            return (
                ExtractionMethod.TAVILY_SEARCH,
                0.85,
                "Authentication required, use search snippet instead",
            )

        # Paywall → likely blocked
        if indicators.is_paywall:
            return (
                ExtractionMethod.TAVILY_SEARCH,
                0.80,
                "Paywall detected, use search snippet instead",
            )

        # Social media → complex and often blocked
        if indicators.is_social_media:
            return (
                ExtractionMethod.PLAYWRIGHT,
                0.85,
                "Social media requires JavaScript rendering",
            )

        # High complexity (3+ indicators) → Playwright
        if score >= 3:
            return (
                ExtractionMethod.PLAYWRIGHT,
                0.75,
                f"High complexity score ({score}/7) indicates JavaScript-heavy content",
            )

        # Medium complexity (1-2 indicators) → Tavily Extract with caution
        if score >= 1:
            return (
                ExtractionMethod.TAVILY_EXTRACT,
                0.60,
                f"Medium complexity ({score}/7), Tavily Extract should work",
            )

        # Low complexity → Tavily Extract
        return (
            ExtractionMethod.TAVILY_EXTRACT,
            0.90,
            "Simple static content, ideal for Tavily Extract",
        )

    def batch_analyze(self, urls: list[str]) -> dict[str, ComplexityAnalysis]:
        """Analyze multiple URLs.

        Args:
            urls: List of URLs to analyze

        Returns:
            Dictionary mapping URL to ComplexityAnalysis
        """
        return {url: self.analyze_url(url) for url in urls}

    def get_method_distribution(
        self, analyses: dict[str, ComplexityAnalysis]
    ) -> dict[str, int]:
        """Get distribution of recommended methods.

        Args:
            analyses: Dictionary of ComplexityAnalysis results

        Returns:
            Count of each extraction method
        """
        distribution = {method.value: 0 for method in ExtractionMethod}
        for analysis in analyses.values():
            distribution[analysis.recommended_method.value] += 1
        return distribution
