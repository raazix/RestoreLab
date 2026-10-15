"""
RestoreLab Local SQLite Knowledge Provider
Offline-first case-based reasoning implementation using SQLite FTS5.
Zero network dependencies and explains match relevance for each result.
"""

from __future__ import annotations

from typing import List, Optional
from restorelab.incidents.models import IncidentRecord
from restorelab.incidents.repository import IncidentRepository
from restorelab.knowledge.provider import MemoryProvider, SearchResult


class SQLiteKnowledgeProvider(MemoryProvider):
    """Local SQLite memory provider with FTS5 search and deterministic match explanations."""

    def __init__(self, repository: Optional[IncidentRepository] = None) -> None:
        self.repo = repository or IncidentRepository()

    def is_available(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "Local SQLite FTS5 Knowledge Engine (Offline)"

    def index_incident(self, incident: IncidentRecord) -> bool:
        """Persist incident to local database."""
        self.repo.save_incident(incident)
        return True

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[SearchResult]:
        """Search knowledge base and past incidents using query keywords."""
        results: List[SearchResult] = []
        q_clean = query.strip()
        if not q_clean:
            # Return top articles if query is empty
            articles = self.repo.list_knowledge_articles(category=category)[:limit]
            for a in articles:
                results.append(
                    SearchResult(
                        item_id=a.article_id,
                        title=a.title,
                        item_type="article",
                        snippet=a.problem_symptoms[:200],
                        match_reason="Browse default knowledge base catalog",
                        verified_resolution=a.resolution_steps,
                        category=a.category,
                        metadata={"known_limitations": a.known_limitations},
                    )
                )
            return results

        # 1. Search Knowledge Articles via FTS5
        articles = self.repo.search_knowledge_base(q_clean)
        for a in articles:
            if category and a.category != category:
                continue

            # Identify matching tokens for match explanation
            query_tokens = [tok.lower() for tok in q_clean.split() if len(tok) > 2]
            matched_terms = [
                tok for tok in query_tokens
                if tok in a.title.lower() or tok in a.problem_symptoms.lower() or tok in a.verified_cause.lower()
            ]
            match_reason = (
                f"Matched keywords [{', '.join(set(matched_terms))}] in title, symptoms, or root cause."
                if matched_terms
                else "Matched query criteria via full-text ranking."
            )

            results.append(
                SearchResult(
                    item_id=a.article_id,
                    title=a.title,
                    item_type="article",
                    snippet=a.problem_symptoms[:220],
                    match_reason=match_reason,
                    verified_resolution=a.resolution_steps,
                    category=a.category,
                    metadata={
                        "diagnostic_checks": a.diagnostic_checks,
                        "verification_procedure": a.verification_procedure,
                        "verified_cause": a.verified_cause,
                    },
                )
            )
            if len(results) >= limit:
                break

        # 2. Search Past Incidents
        if len(results) < limit:
            all_incidents = self.repo.list_incidents(limit=50)
            for inc in all_incidents:
                if category and inc.category != category:
                    continue

                text_corpus = f"{inc.title} {' '.join(inc.symptoms)} {inc.verified_resolution or ''}".lower()
                query_tokens = [tok.lower() for tok in q_clean.split() if len(tok) > 2]
                matched_tokens = [tok for tok in query_tokens if tok in text_corpus]

                if matched_tokens:
                    results.append(
                        SearchResult(
                            item_id=inc.incident_id,
                            title=inc.title,
                            item_type="incident",
                            snippet="; ".join(inc.symptoms)[:220] or inc.title,
                            match_reason=f"Matched prior incident symptoms on keywords [{', '.join(set(matched_tokens))}]",
                            verified_resolution=inc.verified_resolution,
                            category=inc.category,
                            metadata={"status": inc.status, "severity": inc.severity},
                        )
                    )
                if len(results) >= limit:
                    break

        return results
