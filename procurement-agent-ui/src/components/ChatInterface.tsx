import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Zap, Maximize2, Minimize2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BarChart, Bar, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts'
import { sendChatMessage } from '../services/api'
import { fetchMaterialForecast, type ForecastPoint } from '../services/forecastApi'

/** Try to extract forecast P10/P50/P90 data from agent response text */
function extractForecastData(text: string): { material: string; p10: number; p50: number; p90: number } | null {
  // Match P10/P50/P90 followed by any non-digit chars then a number
  const p10Match = text.match(/P10\D+?(\d[\d,]*)/i);
  const p50Match = text.match(/P50\D+?(\d[\d,]*)/i);
  const p90Match = text.match(/P90\D+?(\d[\d,]*)/i);
  if (!p10Match || !p50Match || !p90Match) return null;

  const parse = (s: string) => parseInt(s.replace(/,/g, ''), 10);
  const p10 = parse(p10Match[1]);
  const p50 = parse(p50Match[1]);
  const p90 = parse(p90Match[1]);
  if (isNaN(p10) || isNaN(p50) || isNaN(p90) || p50 === 0) return null;

  const matMatch = text.match(/MAT-[A-Z]{3}-\d{3}/);
  return { material: matMatch?.[0] || 'Material', p10, p50, p90 };
}

function InlineTimeSeriesChart({ materialId }: { materialId: string }) {
  const [points, setPoints] = useState<ForecastPoint[] | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMaterialForecast(materialId, 60).then(result => {
      setPoints(result.forecast || null)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [materialId])

  if (loading) return <div style={{ fontSize: 11, color: '#94a3b8', padding: 8 }}>Loading time series chart...</div>
  if (!points || points.length === 0) return null

  const chartData = points.map(p => ({
    date: p.date.slice(5), // MM-DD
    p10: Math.max(0, Math.round(p.p10)),
    p50: Math.max(0, Math.round(p.p50)),
    p90: Math.max(0, Math.round(p.p90)),
  }))

  return (
    <div style={{ margin: '12px 0 4px', padding: '12px', background: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0' }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {materialId} — 60-Day Forecast (Chronos-2)
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.5} />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#94a3b8' }} interval={9} />
          <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} />
          <Tooltip contentStyle={{ fontSize: 11 }} />
          <Area dataKey="p90" stroke="#ef4444" fill="#ef444420" strokeWidth={1} name="P90 (Conservative)" />
          <Area dataKey="p50" stroke="#3b82f6" fill="none" strokeWidth={2} name="P50 (Median)" />
          <Area dataKey="p10" stroke="#22c55e" fill="#22c55e20" strokeWidth={1} name="P10 (Optimistic)" />
        </AreaChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 4, fontSize: 10, color: '#94a3b8' }}>
        <span><span style={{ color: '#22c55e' }}>●</span> P10 Optimistic</span>
        <span><span style={{ color: '#3b82f6' }}>●</span> P50 Median</span>
        <span><span style={{ color: '#ef4444' }}>●</span> P90 Conservative</span>
      </div>
    </div>
  )
}

function InlineForecastChart({ data }: { data: { material: string; p10: number; p50: number; p90: number } }) {
  const chartData = [
    { name: 'P10 (Optimistic)', value: data.p10, color: '#22c55e' },
    { name: 'P50 (Median)', value: data.p50, color: '#3b82f6' },
    { name: 'P90 (Conservative)', value: data.p90, color: '#ef4444' },
  ];

  const handlePopOut = () => {
    const popup = window.open('', '_blank', 'width=600,height=400');
    if (popup) {
      // nosemgrep: html-in-template-string -- interpolates app-controlled material name and numeric forecast values, no end-user free-text
      popup.document.write(`<html>
        <head><title>${data.material} Forecast</title>
        <style>
          body { font-family: system-ui; background: #0f172a; color: #e2e8f0; padding: 24px; margin: 0; }
          h2 { font-size: 16px; margin-bottom: 16px; }
          .bar-row { display: flex; align-items: center; margin-bottom: 12px; }
          .label { width: 140px; font-size: 13px; }
          .bar { height: 28px; border-radius: 4px; display: flex; align-items: center; padding-left: 8px; font-size: 12px; font-weight: 600; }
        </style></head>
        <body>
          <h2>${data.material} — Demand Forecast</h2>
          <div class="bar-row">
            <div class="label">P10 (Optimistic)</div>
            <div class="bar" style="width: ${(data.p10 / data.p90) * 100}%; background: #22c55e;">${data.p10} units</div>
          </div>
          <div class="bar-row">
            <div class="label">P50 (Median)</div>
            <div class="bar" style="width: ${(data.p50 / data.p90) * 100}%; background: #3b82f6;">${data.p50} units</div>
          </div>
          <div class="bar-row">
            <div class="label">P90 (Conservative)</div>
            <div class="bar" style="width: 100%; background: #ef4444;">${data.p90} units</div>
          </div>
        </body></html>`);
    }
  };

  return (
    <div style={{ margin: '12px 0 4px', padding: '12px', background: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0', position: 'relative' }}>
      <button
        onClick={handlePopOut}
        style={{
          position: 'absolute', top: 8, right: 8,
          padding: '3px 8px', borderRadius: 6, border: '1px solid #cbd5e1',
          background: '#fff', cursor: 'pointer', fontSize: 11, color: '#64748b',
          display: 'flex', alignItems: 'center', gap: 3,
        }}
      >
        ↗ Pop Out
      </button>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {data.material} — Demand Forecast (units)
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 0, bottom: 0 }}>
          <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} width={110} />
          <Tooltip formatter={(v: number) => [`${v.toLocaleString()} units`]} contentStyle={{ fontSize: 12 }} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

interface ChatInterfaceProps {
  messages: Message[]
  /** External activity messages pushed by the parent (e.g. optimization events) */
  activityMessages?: Message[]
  onOptimizationTriggered?: () => void
  /** When set, auto-sends this message and clears it via the callback */
  pendingMessage?: string | null
  onPendingMessageConsumed?: () => void
}

export default function ChatInterface({ messages: initialMessages, activityMessages = [], onOptimizationTriggered, pendingMessage, onPendingMessageConsumed }: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevActivityLen = useRef(0)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Merge in new activity messages from parent
  useEffect(() => {
    if (activityMessages.length > prevActivityLen.current) {
      const newMsgs = activityMessages.slice(prevActivityLen.current)
      setMessages(prev => [...prev, ...newMsgs])
      prevActivityLen.current = activityMessages.length
    }
  }, [activityMessages])

  // Auto-send pending message from parent (e.g. analysis prompt)
  useEffect(() => {
    if (pendingMessage && !isProcessing) {
      const msg = pendingMessage
      onPendingMessageConsumed?.()
      addMessage('user', msg)
      setIsProcessing(true)
      sendChatMessage(msg).then(result => {
        addMessage('assistant', result.response)
        // Don't trigger optimization refetch for programmatic analysis prompts
      }).catch(() => {
        addMessage('assistant', 'Agent request failed. Retrying may help.')
      }).finally(() => {
        setIsProcessing(false)
      })
    }
  }, [pendingMessage])

  const cleanResponse = (text: string): string => {
    // Strip XML tool_call/function_calls tags that leak from Strands agent responses
    let cleaned = text
      .replace(/<function_calls>[\s\S]*?<\/function_calls>/gi, '')
      .replace(/<function_calls\s*\/?>/gi, '')
      .replace(/<\/function_calls>/gi, '')
      .replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, '')
      .replace(/<tool_calls>[\s\S]*?<\/tool_calls>/gi, '')
      .replace(/<\/tool_calls>/gi, '')
      .replace(/<tool_calls>/gi, '')
      .replace(/<invoke[\s\S]*?<\/invoke>/gi, '')
      .replace(/<parameter[\s\S]*?<\/parameter>/gi, '')
      .replace(/<tool_use>[\s\S]*?<\/tool_use>/gi, '')
      .replace(/<tool_result>[\s\S]*?<\/tool_result>/gi, '')
      .replace(/<\/?function_calls>/gi, '')
      .trim()
    // Remove leading/trailing blank lines
    cleaned = cleaned.replace(/^\n+/, '').replace(/\n{3,}/g, '\n\n')
    return cleaned || text
  }

  const addMessage = (role: 'user' | 'assistant', content: string) => {
    const cleaned = role === 'assistant' ? cleanResponse(content) : content
    setMessages(prev => [...prev, { role, content: cleaned, timestamp: new Date() }])
  }

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!input.trim() || isProcessing) return

    const userMessage = input.trim()
    addMessage('user', userMessage)
    setInput('')
    setIsProcessing(true)

    try {
      const result = await sendChatMessage(userMessage)
      addMessage('assistant', result.response)
      if (result.response.match(/solution|pareto|budget|balanced|premium|optimiz/i)) {
        onOptimizationTriggered?.()
      }
    } catch {
      addMessage('assistant', 'Agent request failed. Retrying may help.')
    }

    setIsProcessing(false)
  }

  const handleQuickAction = async (action: string) => {
    if (isProcessing) return
    addMessage('user', action)
    setIsProcessing(true)
    try {
      const result = await sendChatMessage(action)
      addMessage('assistant', result.response)
      if (result.response.match(/solution|pareto|budget|balanced|premium|optimiz/i)) {
        onOptimizationTriggered?.()
      }
    } catch {
      addMessage('assistant', 'Agent request failed.')
    }
    setIsProcessing(false)
  }

  const fullscreenStyle: React.CSSProperties = isFullscreen
    ? { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000, background: '#fff' }
    : {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#fff', position: 'relative', ...fullscreenStyle }}>
      {/* Fullscreen toggle */}
      <button
        onClick={() => setIsFullscreen(f => !f)}
        title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        style={{
          position: 'absolute', top: 10, right: 10, zIndex: 10,
          padding: '5px', borderRadius: 6, border: '1px solid #e2e8f0',
          background: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#64748b',
        }}
      >
        {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
      </button>
      {/* Messages area */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#94a3b8' }}>
            <Zap size={28} style={{ marginBottom: 8, opacity: 0.4 }} />
            <div style={{ fontSize: 13, fontWeight: 500 }}>Procurement Agent ready</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>Ask a question or trigger an optimization from the Demand page</div>
          </div>
        )}
        {messages.map((msg, idx) => {
          // System messages (activity feed)
          if (msg.role === 'system') {
            return (
              <div key={idx} style={{ marginBottom: 12, display: 'flex', justifyContent: 'center' }}>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '6px 14px', borderRadius: 20, fontSize: 12,
                  background: '#f0f9ff', border: '1px solid #bae6fd', color: '#0369a1',
                }}>
                  <Zap size={12} />
                  <span>{msg.content}</span>
                  <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 4 }}>{msg.timestamp.toLocaleTimeString()}</span>
                </div>
              </div>
            )
          }

          return (
            <div key={idx} style={{
              display: 'flex', gap: '10px', marginBottom: '16px',
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
            }}>
              <div style={{
                maxWidth: msg.role === 'user' ? '75%' : '100%',
                padding: msg.role === 'user' ? '10px 14px' : '14px 18px',
                borderRadius: '12px', fontSize: '14px', lineHeight: '1.5',
                background: msg.role === 'user' ? '#3b82f6' : '#f8fafc',
                color: msg.role === 'user' ? '#fff' : '#1e293b',
                border: msg.role === 'assistant' ? '1px solid #e2e8f0' : 'none',
                overflow: 'hidden',
                ...(msg.role === 'user' ? { whiteSpace: 'pre-line' as const } : {}),
              }}>
                {msg.role === 'user' ? msg.content : (
                  <div className="markdown-body" style={{ lineHeight: '1.6', overflowX: 'auto', maxWidth: '100%' }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    {(() => {
                      const forecast = extractForecastData(msg.content);
                      if (!forecast) return null;
                      return (
                        <>
                          <InlineTimeSeriesChart materialId={forecast.material} />
                          <InlineForecastChart data={forecast} />
                        </>
                      );
                    })()}
                  </div>
                )}
                <div style={{ fontSize: '10px', marginTop: '4px', opacity: 0.6, textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          )
        })}
        {isProcessing && (
          <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
            <div style={{ padding: '10px 14px', borderRadius: '12px', background: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '14px' }}>
              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
              Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick actions */}
      <div style={{ padding: '8px 20px', display: 'flex', gap: '6px', flexWrap: 'wrap', flexShrink: 0 }}>
        {[
          ['Optimize suppliers for 500 urban e-bikes for Q2 production', 'Optimize Q2'],
          ['Simulate Strait of Hormuz blockade impact on our supply chain', 'Hormuz Risk'],
          ['Simulate US-China tariff escalation impact', 'Tariff Impact'],
          ['Forecast demand for MAT-BAT-001 battery packs over 60 days', 'Forecast Batteries'],
          ['What materials are single-sourced?', 'Sourcing Risk'],
          ['Show top-performing suppliers by on-time delivery', 'Top Suppliers'],
          ['What risk scenarios can you simulate?', 'List Risks'],
          ['Explain the Balanced strategy in detail', 'Explain Strategy'],
        ].map(([action, label]) => (
          <button key={label} onClick={() => handleQuickAction(action)}
            disabled={isProcessing}
            style={{
              padding: '5px 12px', borderRadius: '16px', border: '1px solid #e2e8f0',
              background: '#fff', cursor: 'pointer', fontSize: '12px', color: '#475569',
              opacity: isProcessing ? 0.5 : 1,
            }}>
            {label}
          </button>
        ))}
      </div>

      {/* Input */}
      <form onSubmit={handleSend} style={{ padding: '12px 20px', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '8px', flexShrink: 0 }}>
        <input
          type="text"
          placeholder="Ask about procurement, suppliers, optimization..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isProcessing}
          style={{
            flex: 1, padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0',
            fontSize: '14px', outline: 'none', background: '#f8fafc',
          }}
        />
        <button type="submit" disabled={isProcessing}
          style={{
            padding: '10px 16px', borderRadius: '10px', border: 'none',
            background: isProcessing ? '#94a3b8' : '#3b82f6', color: '#fff', cursor: 'pointer',
            display: 'flex', alignItems: 'center',
          }}>
          <Send size={18} />
        </button>
      </form>
    </div>
  )
}
