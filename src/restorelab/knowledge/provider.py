"""
RestoreLab Knowledge Base & Incident Retrieval Provider Interface
Defines the memory provider contract for offline-first case-based reasoning
and optional remote extensions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from restorelab.incidents.models import IncidentRecord, KnowledgeArticle


class SearchResult(BaseModel):
    """Normalized search match explaining relevance and resolution evidence."""

    item_id: str
    title: str
    item_type: str = Field(description="'article' or 'incident'")
    snippet: str
    match_reason: str = Field(description="Deterministic explanation of why this record matched")
    score: float = 1.0
    verified_resolution: Optional[str] = None
    category: str = "general"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryProvider(ABC):
    """Contract for incident knowledge retrieval providers."""

    @abstractmethod
    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[SearchResult]:
        """Search historical troubleshooting cases and knowledge articles."""
        pass

    @abstractmethod
    def index_incident(self, incident: IncidentRecord) -> bool:
        """Add a resolved incident to the searchable knowledge repository."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the provider is active and operational."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return human-readable identifier."""
        pass
