"""Data models for the search API."""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Product:
    """Represents a single product result."""
    title: str
    price: str
    link: str
    image: str = ""
    rating: str = ""
    source: str = ""  # "Amazon" or "Flipkart"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchResponse:
    """Response model for search results."""
    query: str
    amazon_results: list[Product] = field(default_factory=list)
    flipkart_results: list[Product] = field(default_factory=list)
    amazon_error: str = ""
    flipkart_error: str = ""

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "amazon_results": [p.to_dict() for p in self.amazon_results],
            "flipkart_results": [p.to_dict() for p in self.flipkart_results],
            "amazon_error": self.amazon_error,
            "flipkart_error": self.flipkart_error,
            "total_results": len(self.amazon_results) + len(self.flipkart_results),
        }
