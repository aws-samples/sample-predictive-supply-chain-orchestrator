import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Database, MessageSquare, Brain, User, Clock, Search, Sparkles, Heart, FileText, ChevronDown, ChevronRight } from 'lucide-react'
import {
  fetchSessions, fetchMemoryRecords, fetchMemoryInfo, searchMemory,
  type SessionTurn, type MemoryRecord,
} from '../services/adminApi'

type Tab = 'sessions' | 'memory'

interface MemoryInfo {
  memory_id: string;
  name: string;
  status: string;
  event_expiry_days: number;
  strategies: Array<{ strategy_id: string; name: string; type: string; status: string; namespaces: string[] }>;
}

const STRATEGY_META: Record<string, { icon: typeof Brain; color: string; bg: string; description: string }> = {
  SEMANTIC: {
    icon: Sparkles,
    color: '#3b82f6',
    bg: '#eff6ff',
    description: 'Extracts supplier facts from your conversations and consolidates them over time — so the agent remembers what it learned about suppliers across sessions.',
  },
  USER_PREFERENCE: {
    icon: Heart,
    color: '#7c3aed',
    bg: '#faf5ff',
    description: 'Tracks your optimization preferences (budget limits, preferred strategies, risk tolerance) so the agent adapts to how you work.',
  },
  SUMMARIZATION: {
    icon: FileText,
    color: '#d97706',
    bg: '#fffbeb',
    description: 'Summarizes each conversation so the agent can pick up context in future sessions without replaying the full history.',
  },
}

export default function MemoryExplorer() {
  const [tab, setTab] = useState<Tab>('memory')
  const [sessions, setSessions] = useState<SessionTurn[]>([])
  const [records, setRecords] = useState<MemoryRecord[]>([])
  const [memoryInfo, setMemoryInfo] = useState<MemoryInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<MemoryRecord[] | null>(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchSessions(), fetchMemoryRecords(), fetchMemoryInfo()]).then(([s, r, info]) => {
      setSessions(s)
      setRecords(r)
      if (info) setMemoryInfo(info as MemoryInfo)
      setLoading(false)
    })
  }, [])

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null)
      return
    }
    setSearching(true)
    const results = await searchMemory(searchQuery.trim())
    setSearchResults(results)
    setSearching(false)
  }

  // Group sessions by session_id, sorted by most recent first
  const sessionGroups = sessions.reduce<Record<string, SessionTurn[]>>((acc, turn) => {
    (acc[turn.session_id] ||= []).push(turn)
    return acc
  }, {})
  const sortedSessionIds = Object.keys(sessionGroups).sort((a, b) => {
    const latestA = Math.max(...sessionGroups[a].map(t => t.created_at))
    const latestB = Math.max(...sessionGroups[b].map(t => t.created_at))
    return latestB - latestA
  })

  // Sort records by most recent first, then group by strategy
  const sortedRecords = [...records].sort((a, b) => {
    const ta = new Date(a.updated_at || a.created_at || 0).getTime()
    const tb = new Date(b.updated_at || b.created_at || 0).getTime()
    return tb - ta
  })
  const recordsByStrategy = sortedRecords.reduce<Record<string, MemoryRecord[]>>((acc, rec) => {
    (acc[rec.strategy] ||= []).push(rec)
    return acc
  }, {})

  const formatTime = (ts: number | string) => {
    if (!ts) return ''
    const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
    if (isNaN(d.getTime())) return String(ts)
    const now = new Date()
    const diffH = Math.round((now.getTime() - d.getTime()) / 3600000)
    if (diffH < 1) return 'just now'
    if (diffH < 24) return `${diffH}h ago`
    return `${Math.round(diffH / 24)}d ago`
  }

  const displayRecords = searchResults !== null
    ? [...searchResults].sort((a, b) => {
        const ta = a.updated_at ? new Date(a.updated_at).getTime() : 0
        const tb = b.updated_at ? new Date(b.updated_at).getTime() : 0
        return tb - ta
      })
    : sortedRecords

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: '#1e293b' }}>Agent Memory</h2>
        <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#64748b' }}>
          Long-term memory powered by AgentCore — the agent remembers supplier insights, your preferences, and conversation context across sessions.
        </p>
      </div>

      {/* Live memory info bar */}
      {memoryInfo && (
        <div style={{
          display: 'flex', gap: '10px', marginBottom: '16px', padding: '10px 14px',
          background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe', fontSize: '12px', flexWrap: 'wrap', alignItems: 'center',
        }}>
          <span style={{ color: '#2563eb', fontWeight: 600 }}>Memory ID:</span>
          <span style={{ fontFamily: 'monospace', color: '#1d4ed8', fontSize: '11px' }}>{memoryInfo.memory_id || 'ProcurementAgentMemory'}</span>
          <span style={{ color: '#bfdbfe' }}>|</span>
          <span style={{ color: '#2563eb' }}>{memoryInfo.strategies.length} strategies</span>
          <span style={{ color: '#bfdbfe' }}>|</span>
          <span style={{ color: '#64748b' }}>Events expire after {memoryInfo.event_expiry_days || 90} days</span>
          <span style={{ color: '#bfdbfe' }}>|</span>
          <span style={{
            padding: '1px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: 700,
            background: '#dcfce7', color: '#166534',
          }}>ACTIVE</span>
        </div>
      )}

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: '2px', marginBottom: '20px', background: '#f1f5f9', borderRadius: '8px', padding: '3px' }}>
        {([['sessions', 'Sessions', MessageSquare], ['memory', 'Long-term Memory', Brain]] as const).map(([key, label, Icon]) => (
          <button key={key} onClick={() => { setTab(key); setSearchResults(null); setSearchQuery(''); }} style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
            padding: '8px', borderRadius: '6px', border: 'none', cursor: 'pointer',
            fontSize: '13px', fontWeight: 600,
            background: tab === key ? '#fff' : 'transparent',
            color: tab === key ? '#1e293b' : '#94a3b8',
            boxShadow: tab === key ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
          }}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>Loading...</div>
      ) : tab === 'sessions' ? (
        /* ── Sessions view ── */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {Object.keys(sessionGroups).length === 0 && (
            <div style={{ padding: '30px', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '10px' }}>
              <MessageSquare size={32} style={{ margin: '0 auto 8px', display: 'block', opacity: 0.4 }} />
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>No sessions yet</div>
              <div style={{ fontSize: '12px' }}>Conversation sessions will appear here after chatting with the agent.</div>
            </div>
          )}
          {sortedSessionIds.map(sessionId => {
            // Sort turns within session chronologically (oldest first) for readability
            const turns = [...sessionGroups[sessionId]].sort((a, b) => a.created_at - b.created_at)
            const latestTurn = turns[turns.length - 1]
            return { sessionId, turns, latestTurn }
          }).map(({ sessionId, turns, latestTurn }) => (
            <div key={sessionId} style={{ background: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Database size={14} style={{ color: '#3b82f6' }} />
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>{sessionId}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', color: '#94a3b8' }}>
                  <span><User size={11} /> {turns[0]?.user_id}</span>
                  <span><Clock size={11} /> {formatTime(latestTurn?.created_at || turns[0]?.created_at)}</span>
                  <span>{turns.length} turns</span>
                </div>
              </div>
              <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {turns.map((turn) => (
                  <TurnRow key={`${turn.session_id}-${turn.turn_id}`} turn={turn} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* ── Long-term memory view ── */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {/* Strategy cards with descriptions */}
          {memoryInfo && memoryInfo.strategies.length > 0 && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginBottom: '8px' }}>
                How Memory Works
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
                {memoryInfo.strategies.map(s => {
                  const meta = STRATEGY_META[s.type] || STRATEGY_META.SEMANTIC
                  const Icon = meta.icon
                  return (
                    <div key={s.strategy_id} style={{
                      background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '14px',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Icon size={14} style={{ color: meta.color }} />
                          <span style={{ fontSize: '13px', fontWeight: 700, color: '#1e293b' }}>{s.name}</span>
                        </div>
                        <span style={{
                          padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: 600,
                          background: s.status === 'ACTIVE' ? '#dcfce7' : '#fef3c7',
                          color: s.status === 'ACTIVE' ? '#166534' : '#92400e',
                        }}>{s.status}</span>
                      </div>
                      <div style={{
                        padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                        background: meta.bg, color: meta.color,
                        display: 'inline-block', marginBottom: '8px',
                      }}>{s.type}</div>
                      <p style={{ margin: 0, fontSize: '12px', color: '#64748b', lineHeight: '1.5' }}>
                        {meta.description}
                      </p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Search bar */}
          <div style={{
            display: 'flex', gap: '8px', padding: '12px 16px',
            background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0',
          }}>
            <Search size={16} style={{ color: '#94a3b8', flexShrink: 0, marginTop: '2px' }} />
            <input
              type="text"
              placeholder="Search memories... e.g. &quot;battery supplier preferences&quot;"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              style={{
                flex: 1, border: 'none', outline: 'none', fontSize: '13px', color: '#1e293b',
                background: 'transparent', fontFamily: 'inherit',
              }}
            />
            <button
              onClick={handleSearch}
              disabled={searching}
              style={{
                padding: '4px 14px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                fontSize: '12px', fontWeight: 600,
                background: '#3b82f6', color: '#fff',
                opacity: searching ? 0.6 : 1,
              }}
            >
              {searching ? 'Searching...' : 'Search'}
            </button>
            {searchResults !== null && (
              <button
                onClick={() => { setSearchResults(null); setSearchQuery(''); }}
                style={{
                  padding: '4px 10px', borderRadius: '6px', border: '1px solid #e2e8f0',
                  cursor: 'pointer', fontSize: '12px', color: '#64748b', background: '#f8fafc',
                }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Search results header */}
          {searchResults !== null && (
            <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic' }}>
              {searchResults.length > 0
                ? `Found ${searchResults.length} memory record${searchResults.length !== 1 ? 's' : ''} matching "${searchQuery}"`
                : `No results for "${searchQuery}" — try a broader query or the agent may not have stored memories yet.`}
            </div>
          )}

          {/* Memory records */}
          {searchResults === null && displayRecords.length === 0 && (
            <div style={{ padding: '30px', textAlign: 'center', color: '#94a3b8', background: '#f8fafc', borderRadius: '10px' }}>
              <Brain size={32} style={{ margin: '0 auto 8px', display: 'block', opacity: 0.4 }} />
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#64748b', marginBottom: '4px' }}>No memory records yet</div>
              <div style={{ fontSize: '12px' }}>
                Chat with the agent to build up memories. The strategies above will automatically extract insights, preferences, and summaries from your conversations.
              </div>
            </div>
          )}

          {/* Render records grouped by strategy (browsing mode) or flat (search mode) */}
          {searchResults !== null ? (
            /* Flat search results */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {searchResults.map((rec) => {
                const meta = STRATEGY_META[rec.strategy_type] || STRATEGY_META.SEMANTIC
                const Icon = meta.icon
                return (
                  <div key={rec.record_id} style={{
                    background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '12px 16px',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Icon size={13} style={{ color: meta.color }} />
                        <span style={{
                          padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                          background: meta.bg, color: meta.color,
                        }}>{rec.strategy}</span>
                        {rec.score != null && (
                          <span style={{ fontSize: '10px', color: '#94a3b8' }}>
                            relevance: {(rec.score * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      {(rec.updated_at || rec.created_at) && (
                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                          <Clock size={11} /> {formatTime(rec.updated_at || rec.created_at)}
                        </span>
                      )}
                    </div>
                    <p style={{
                      margin: 0, fontSize: '13px', color: '#334155', lineHeight: '1.5',
                    }}>{rec.content}</p>
                  </div>
                )
              })}
            </div>
          ) : (
            /* Grouped by strategy */
            Object.entries(recordsByStrategy).length > 0 && Object.entries(recordsByStrategy).map(([strategy, stratRecords]) => {
              const firstRec = stratRecords[0]
              const meta = STRATEGY_META[firstRec?.strategy_type] || STRATEGY_META.SEMANTIC
              const Icon = meta.icon
              return (
                <div key={strategy}>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    marginBottom: '8px', fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase',
                  }}>
                    <Icon size={13} style={{ color: meta.color }} />
                    {strategy.replace(/([A-Z])/g, ' $1').trim()} ({stratRecords.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {stratRecords.map((rec) => (
                      <div key={rec.record_id} style={{
                        background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '12px 16px',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                          <span style={{
                            padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
                            background: meta.bg, color: meta.color,
                          }}>{rec.strategy_type}</span>
                          <div style={{ display: 'flex', gap: '8px', fontSize: '11px', color: '#94a3b8' }}>
                            {(rec.updated_at || rec.created_at) && <span><Clock size={11} /> {formatTime(rec.updated_at || rec.created_at)}</span>}
                          </div>
                        </div>
                        <p style={{
                          margin: 0, fontSize: '13px', color: '#334155', lineHeight: '1.5',
                        }}>{rec.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

function TurnRow({ turn }: { turn: SessionTurn }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = turn.content.length > 200

  return (
    <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
      <span style={{
        padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 600,
        background: turn.role === 'user' ? '#eff6ff' : '#f0fdf4',
        color: turn.role === 'user' ? '#3b82f6' : '#16a34a',
        flexShrink: 0, marginTop: '2px',
      }}>
        {turn.role}
      </span>
      <div style={{ fontSize: '13px', color: '#334155', lineHeight: '1.5', flex: 1, minWidth: 0 }}>
        {turn.role === 'assistant' && (expanded || !isLong) ? (
          <div className="memory-markdown" style={{ fontSize: '12px' }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.content}</ReactMarkdown>
          </div>
        ) : (
          <span>{isLong && !expanded ? turn.content.slice(0, 200) + '...' : turn.content}</span>
        )}
        {isLong && (
          <button onClick={() => setExpanded(!expanded)} style={{
            display: 'inline-flex', alignItems: 'center', gap: '3px', padding: '2px 8px',
            borderRadius: '4px', border: '1px solid #e2e8f0', background: '#f8fafc',
            cursor: 'pointer', fontSize: '10px', fontWeight: 600, color: '#64748b', marginTop: '4px',
          }}>
            {expanded ? <><ChevronDown size={10} /> Collapse</> : <><ChevronRight size={10} /> Show full</>}
          </button>
        )}
        {turn.tools_used.length > 0 && (
          <div style={{ marginTop: '4px' }}>
            {turn.tools_used.map(t => (
              <span key={t} style={{
                padding: '1px 5px', borderRadius: '3px', fontSize: '10px',
                background: '#fef3c7', color: '#92400e', marginRight: '4px',
              }}>
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
