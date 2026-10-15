import React, { useEffect, useState } from 'react'
import {
  BookOpen,
  Search,
  Sparkles,
  Database,
  Tag,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { api, KnowledgeArticle, SearchResult, SystemStatus } from '@/lib/api'

interface KnowledgeBaseViewProps {
  systemStatus: SystemStatus | null
}

export const KnowledgeBaseView: React.FC<KnowledgeBaseViewProps> = ({ systemStatus }) => {
  const [query, setQuery] = useState('')
  const [useSupermemory, setUseSupermemory] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [curatedArticles, setCuratedArticles] = useState<KnowledgeArticle[]>([])
  const [searching, setSearching] = useState(false)
  const [loadingArticles, setLoadingArticles] = useState(false)

  const fetchArticles = async () => {
    setLoadingArticles(true)
    try {
      const data = await api.getKnowledgeArticles()
      setCuratedArticles(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoadingArticles(false)
    }
  }

  useEffect(() => {
    fetchArticles()
  }, [])

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!query.trim()) {
      setSearchResults([])
      return
    }

    setSearching(true)
    try {
      const results = await api.searchKnowledge(query, useSupermemory)
      setSearchResults(results)
    } catch (err: any) {
      alert(`Search failed: ${err.message}`)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* View Header */}
      <div>
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          Reliability Knowledge Base & Case-Based Retrieval
        </h2>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
          Case-based reasoning system matching symptoms against verified post-mortems.
          Query local SQLite FTS5 index or leverage Supermemory v5 hybrid semantic search.
        </p>
      </div>

      {/* Search Input & Engine Toggle */}
      <Card>
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search error messages, symptoms, rules, or verified resolutions (e.g. silent corruption, password, access denied)..."
                className="w-full pl-10 pr-4 py-2 bg-surface-2 border border-border-muted rounded-lg text-xs text-zinc-100 placeholder-zinc-500 font-sans focus:outline-none focus:border-border-active"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={searching}
              leftIcon={<Search className="w-3.5 h-3.5" />}
            >
              Search
            </Button>
          </div>

          <div className="flex items-center justify-between text-xs text-zinc-400 pt-2 border-t border-border-subtle">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={useSupermemory}
                  onChange={(e) => setUseSupermemory(e.target.checked)}
                  disabled={!systemStatus?.supermemory_enabled}
                  className="rounded bg-surface-3 border-border-muted text-indigo-500 focus:ring-0 disabled:opacity-50"
                />
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  Supermemory v5 Hybrid Search
                  {!systemStatus?.supermemory_enabled && (
                    <span className="text-[10px] text-zinc-500">(Disabled in settings)</span>
                  )}
                </span>
              </label>

              <span className="flex items-center gap-1.5 text-zinc-500">
                <Database className="w-3.5 h-3.5 text-cyan-400" />
                SQLite FTS5 Local Search
              </span>
            </div>

            {query && (
              <span className="font-mono text-[11px] text-zinc-500">
                {searchResults.length} results
              </span>
            )}
          </div>
        </form>
      </Card>

      {/* Search Results (If query active) */}
      {query.trim() && (
        <div className="space-y-4">
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Matching Articles & Historical Incidents
          </h3>

          {searchResults.length === 0 && !searching ? (
            <Card className="py-12 text-center text-xs text-zinc-500">
              No matching knowledge base articles or historical post-mortems found.
            </Card>
          ) : (
            searchResults.map((res, idx) => (
              <Card key={idx} className="space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 text-xs">
                      <Badge variant="cyan" className="font-mono text-[10px]">
                        {res.reference_id}
                      </Badge>
                      <Badge variant={res.source_type === 'knowledge_base' ? 'zinc' : 'amber'}>
                        {res.source_type.replace('_', ' ').toUpperCase()}
                      </Badge>
                      <span className="font-mono text-[10px] text-zinc-500">
                        Score: {res.score.toFixed(2)}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-zinc-100 mt-1.5">
                      {res.title}
                    </h4>
                  </div>
                </div>

                {/* Match Reason */}
                {res.match_reason && (
                  <div className="p-2.5 rounded bg-surface-2 border border-border-subtle text-xs text-zinc-300">
                    <strong className="text-cyan-400 font-mono text-[11px]">Match Reason:</strong>{' '}
                    {res.match_reason}
                  </div>
                )}

                {/* Snippet / Resolution */}
                <p className="text-xs text-zinc-400 leading-relaxed">
                  {res.snippet}
                </p>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Curated Articles (When no search active) */}
      {!query.trim() && (
        <div className="space-y-4">
          <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Curated Reliability Engineering Articles ({curatedArticles.length})
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {curatedArticles.map((art) => (
              <Card key={art.article_id} className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <Badge variant="cyan" className="font-mono text-[10px]">
                    {art.article_id}
                  </Badge>
                  <span className="font-mono text-[10px] text-zinc-500 uppercase">
                    {art.category}
                  </span>
                </div>

                <h4 className="text-xs font-bold text-zinc-100">{art.title}</h4>

                <div className="space-y-1.5 text-[11px] text-zinc-400">
                  <div>
                    <strong className="text-zinc-300">Verified Cause:</strong> {art.verified_cause}
                  </div>
                  <div>
                    <strong className="text-emerald-400">Resolution Steps:</strong> {art.resolution_steps}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
