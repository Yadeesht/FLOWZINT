'use client'

import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// === Mini Components ===

function StatCard({ icon, label, value, sub, color = '#4F46E5', delta }) {
  return (
    <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: color + '14', border: `1px solid ${color}22`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17,
        }}>{icon}</div>
        {delta != null && (
          <span style={{ fontSize: 12, fontWeight: 700, color: delta >= 0 ? '#10B981' : '#F43F5E', background: delta >= 0 ? '#ECFDF5' : '#FFF1F2', padding: '3px 8px', borderRadius: 999 }}>
            {delta >= 0 ? '↑' : '↓'} {Math.abs(delta)}%
          </span>
        )}
      </div>
      <div>
        <div style={{ fontSize: 28, fontWeight: 800, color: '#0A0A0F', letterSpacing: '-0.03em', lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#4A5568', marginTop: 4 }}>{label}</div>
        {sub && <div style={{ fontSize: 11.5, color: '#94A3B8', marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  )
}

function Avatar({ name, size = 32 }) {
  const colors = ['#EEF2FF', '#ECFDF5', '#FFFBEB', '#FFF1F2', '#F0FDF4']
  const idx = (name?.charCodeAt(0) || 0) % colors.length
  return (
    <div style={{
      width: size, height: size, borderRadius: size * 0.28, flexShrink: 0,
      background: colors[idx], border: '1px solid rgba(0,0,0,0.08)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.4, fontWeight: 800, color: '#4F46E5',
    }}>
      {(name || '?')[0].toUpperCase()}
    </div>
  )
}

function SentimentPill({ sentiment }) {
  const map = {
    positive:   { color: '#059669', bg: '#ECFDF5', label: 'Positive' },
    neutral:    { color: '#4F46E5', bg: '#EEF2FF', label: 'Neutral' },
    confused:   { color: '#B45309', bg: '#FFFBEB', label: 'Confused' },
    frustrated: { color: '#BE123C', bg: '#FFF1F2', label: 'Frustrated' },
  }
  const c = map[sentiment] || map.neutral
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 9px', borderRadius: 999,
      background: c.bg, color: c.color,
      fontSize: 11, fontWeight: 700, letterSpacing: '0.03em',
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: c.color, display: 'inline-block' }} />
      {c.label}
    </span>
  )
}

function SentimentDonut({ data }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  const colors = { positive: '#10B981', neutral: '#6366F1', confused: '#F59E0B', frustrated: '#F43F5E' }
  const r = 38, circ = 2 * Math.PI * r
  let offset = 0
  const slices = Object.entries(data).map(([k, v]) => {
    const pct = v / total * 100
    const s = { key: k, pct, color: colors[k] || '#CBD5E1', offset }
    offset += pct
    return s
  })

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 28, flexWrap: 'wrap' }}>
      <div style={{ position: 'relative', width: 100, height: 100, flexShrink: 0 }}>
        <svg width={100} height={100} viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={50} cy={50} r={r} fill="none" stroke="#F1F5F9" strokeWidth={14}/>
          {slices.map(sl => (
            <circle key={sl.key} cx={50} cy={50} r={r} fill="none" stroke={sl.color} strokeWidth={14}
              strokeDasharray={`${sl.pct / 100 * circ} ${circ}`}
              strokeDashoffset={-(sl.offset / 100 * circ)}
              strokeLinecap="round"
              style={{ transition: 'all 0.5s ease' }}
            />
          ))}
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 16, fontWeight: 800, color: '#0A0A0F' }}>{total}</span>
          <span style={{ fontSize: 9, color: '#94A3B8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>total</span>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {Object.entries(data).map(([k, v]) => (
          <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: colors[k] || '#CBD5E1', flexShrink: 0 }}/>
            <span style={{ fontSize: 13, color: '#4A5568', minWidth: 72, textTransform: 'capitalize' }}>{k}</span>
            <div style={{ height: 5, width: 80, background: '#F1F5F9', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${v / total * 100}%`, background: colors[k] || '#CBD5E1', borderRadius: 99, transition: 'width 0.6s ease' }}/>
            </div>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#0A0A0F', minWidth: 24, textAlign: 'right' }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function WALogEntry({ entry }) {
  const icons = { otp: '🔐', abandoned_nudge: '⚡', enrollment_confirmation: '🎉', reminder: '📅', review_request: '⭐' }
  const statusColor = { delivered: '#059669', simulated: '#B45309', failed: '#BE123C' }
  const ts = entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''
  return (
    <div style={{ padding: '14px 16px', background: '#FAFAFA', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 15 }}>{icons[entry.type] || '📨'}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#4A5568', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {entry.type?.replace(/_/g, ' ')}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#94A3B8' }}>{ts}</span>
        <span style={{
          fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 999,
          color: statusColor[entry.status] || '#64748B',
          background: (statusColor[entry.status] || '#64748B') + '14',
          letterSpacing: '0.04em', textTransform: 'uppercase',
        }}>{entry.status}</span>
      </div>
      <div style={{ fontSize: 12, color: '#64748B' }}>
        → <strong style={{ color: '#1E1E2E' }}>{entry.name}</strong> · {entry.to}
      </div>
      <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 4, lineHeight: 1.5 }}>
        {entry.message?.slice(0, 130)}{entry.message?.length > 130 ? '…' : ''}
      </div>
    </div>
  )
}

function ReviewCard({ review }) {
  return (
    <div className="card" style={{ padding: '18px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
        <Avatar name={review.student_name} size={36} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 13, color: '#1E1E2E' }}>{review.student_name}</div>
          <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 1 }}>{review.course} · {review.date}</div>
        </div>
        <div style={{ display: 'flex', gap: 1, flexShrink: 0 }}>
          {[1,2,3,4,5].map(n => (
            <span key={n} style={{ fontSize: 13, color: n <= review.rating ? '#F59E0B' : '#E2E8F0' }}>★</span>
          ))}
        </div>
      </div>
      <p style={{ fontSize: 13, color: '#4A5568', lineHeight: 1.65 }}>"{review.comment}"</p>
    </div>
  )
}

function PipelineTable({ rows, showNudge, onNudge, nudgeStatus }) {
  if (!rows || rows.length === 0) return <p style={{ color: '#94A3B8', fontSize: 13 }}>No entries yet.</p>
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {['Student', 'Course Interest', 'Last Active', 'Sentiment', ...(showNudge ? ['Action'] : [])].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#94A3B8', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid rgba(0,0,0,0.06)', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(s => {
            const lastSent = s.sentiment_history?.slice(-1)[0]
            const lastActive = s.last_active ? new Date(s.last_active).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'
            const nudging = nudgeStatus?.[s.phone]
            return (
              <tr key={s.phone} style={{ borderBottom: '1px solid rgba(0,0,0,0.04)', transition: 'background 0.1s ease' }}
                onMouseEnter={e => e.currentTarget.style.background = '#FAFAFA'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <td style={{ padding: '12px 12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Avatar name={s.name} size={28} />
                    <div>
                      <div style={{ fontWeight: 600, color: '#1E1E2E' }}>{s.name}</div>
                      <div style={{ fontSize: 11, color: '#94A3B8' }}>+91 {s.phone}</div>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '12px 12px' }}>
                  <span style={{ color: '#4A5568' }}>{s.course_interest || s.enrolled_course?.replace(/-/g,' ') || '—'}</span>
                </td>
                <td style={{ padding: '12px 12px' }}>
                  <span style={{ color: '#94A3B8', fontSize: 12 }}>{lastActive}</span>
                </td>
                <td style={{ padding: '12px 12px' }}>
                  {lastSent ? <SentimentPill sentiment={lastSent} /> : <span style={{ color: '#94A3B8', fontSize: 12 }}>—</span>}
                </td>
                {showNudge && (
                  <td style={{ padding: '12px 12px' }}>
                    <button
                      onClick={() => onNudge(s)}
                      disabled={nudging === 'loading'}
                      style={{
                        padding: '6px 12px', borderRadius: 12, border: '1px solid #FDE68A',
                        background: nudging === 'sent' ? '#ECFDF5' : '#FFFBEB',
                        color: nudging === 'sent' ? '#059669' : '#B45309',
                        fontSize: 12, fontWeight: 600, cursor: 'pointer',
                        fontFamily: 'inherit', transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                      }}
                    >
                      {nudging === 'loading' ? '⏳ Sending…' : nudging === 'sent' ? '✓ Sent!' : '📲 Nudge'}
                    </button>
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// === Main Dashboard ===

const NAV = [
  { id: 'overview', label: 'Overview', icon: '◈' },
  { id: 'pipeline', label: 'Pipeline', icon: '⤳' },
  { id: 'wa_log', label: 'WA Log', icon: '◉' },
  { id: 'reviews', label: 'Reviews', icon: '★' },
]

export default function AdminDashboard() {
  const [tab, setTab] = useState('overview')
  const [analytics, setAnalytics] = useState(null)
  const [students, setStudents] = useState({ enrolled: [], investigated: [], hot_leads: [] })
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [nudgeStatus, setNudgeStatus] = useState({})
  const [pipelineTab, setPipelineTab] = useState('hot')
  const [copilotInput, setCopilotInput] = useState('')
  const [copilotMessages, setCopilotMessages] = useState([
    { role: 'assistant', content: '👋 Hello Administrator! I am your **Admin AI Copilot**.\n\nI have fully indexed our student pipeline, conversion metrics, and reviews. Ask me anything, or try these quick options below!' }
  ])
  const [copilotTyping, setCopilotTyping] = useState(false)

  async function load() {
    try {
      const [ar, sr, rr] = await Promise.all([
        fetch(`${API_BASE}/api/analytics`).then(r => r.json()),
        fetch(`${API_BASE}/api/students`).then(r => r.json()),
        fetch(`${API_BASE}/api/reviews`).then(r => r.json()),
      ])
      setAnalytics(ar); setStudents(sr); setReviews(rr.reviews || [])
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t) }, [])

  async function nudge(student) {
    const k = student.phone
    setNudgeStatus(p => ({ ...p, [k]: 'loading' }))
    try {
      await fetch(`${API_BASE}/api/inactive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: student.phone, name: student.name, course_interest: student.course_interest || 'AI/ML Bootcamp', discount: 20 }),
      })
      setNudgeStatus(p => ({ ...p, [k]: 'sent' }))
      setTimeout(() => setNudgeStatus(p => ({ ...p, [k]: null })), 4000)
      load()
    } catch { setNudgeStatus(p => ({ ...p, [k]: null })) }
  }

  async function sendCopilotQuery(overrideText) {
    const text = (overrideText || copilotInput).trim()
    if (!text || copilotTyping) return
    setCopilotInput('')
    const newMsgs = [...copilotMessages, { role: 'user', content: text }]
    setCopilotMessages(newMsgs)
    setCopilotTyping(true)

    try {
      const res = await fetch(`${API_BASE}/api/admin/copilot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          history: newMsgs.slice(-10).map(m => ({ role: m.role, content: m.content }))
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to get copilot response')
      setCopilotMessages(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch (err) {
      setCopilotMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Error: ${err.message}` }])
    } finally {
      setCopilotTyping(false)
    }
  }

  const avgRating = reviews.length > 0 ? (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1) : '—'

  if (loading) return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#F8F9FB', flexDirection: 'column', gap: 16 }}>
      <div className="anim-spin" style={{ width: 36, height: 36, border: '3px solid #E0E7FF', borderTopColor: '#4F46E5', borderRadius: '50%' }}/>
      <span style={{ color: '#94A3B8', fontSize: 14, fontWeight: 600 }}>Loading dashboard…</span>
    </div>
  )

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#F8F9FB', overflow: 'hidden' }}>
      {/* === Sidebar === */}
      <aside style={s.sidebar}>
        {/* Logo */}
        <div style={s.sidebarTop}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={s.sidebarLogo}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5"/>
              </svg>
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 14, color: '#0A0A0F', lineHeight: 1 }}>EduFlow AI</div>
              <div style={{ fontSize: 11, color: '#94A3B8' }}>Admin Console</div>
            </div>
          </div>
        </div>

        {/* Live indicator */}
        <div style={s.livePill}>
          <span className="status-dot" style={{ width: 6, height: 6 }}/>
          <span>Live · auto-refresh 15s</span>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '8px 8px' }}>
          {NAV.map(n => (
            <button key={n.id} onClick={() => setTab(n.id)} style={{
              ...s.navItem,
              background: tab === n.id ? '#EEF2FF' : 'transparent',
              color: tab === n.id ? '#4F46E5' : '#64748B',
              fontWeight: tab === n.id ? 700 : 500,
            }}>
              <span style={{ fontSize: 15 }}>{n.icon}</span>
              <span>{n.label}</span>
              {n.id === 'wa_log' && analytics?.wa_outbound_log?.length > 0 && (
                <span style={{ marginLeft: 'auto', background: '#EEF2FF', color: '#4F46E5', fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 999 }}>
                  {analytics.wa_outbound_log.length}
                </span>
              )}
            </button>
          ))}
        </nav>

        {/* Bottom */}
        <div style={s.sidebarBottom}>
          <button onClick={load} style={s.refreshBtn}>
            <span>↻</span> Refresh
          </button>
          <a href="/" style={s.chatLink}>
            <span>←</span> Back to Chat
          </a>
        </div>
      </aside>

      {/* === Main Content === */}
      <main style={s.main}>
        {/* Page header */}
        <div style={s.pageHeader}>
          <div>
            <h1 style={s.pageTitle}>{NAV.find(n => n.id === tab)?.label}</h1>
            <p style={s.pageSub}>
              {tab === 'overview' && `${analytics?.total_sessions ?? 0} sessions · ${analytics?.total_enquirers ?? 0} enquirers · ${analytics?.total_enrolled ?? 0} enrolled`}
              {tab === 'pipeline' && `${students.enrolled.length} enrolled · ${students.hot_leads.length} hot leads · ${students.investigated.length} enquirers`}
              {tab === 'wa_log' && `${analytics?.wa_outbound_log?.length ?? 0} messages sent`}
              {tab === 'reviews' && `${reviews.length} reviews · avg ${avgRating} / 5`}
              {tab === 'copilot' && "Query analytics, pipeline leads, and reviews interactively using AI."}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {tab === 'pipeline' && (
              <div style={{ display: 'flex', background: '#F1F3F7', borderRadius: 10, padding: 3, gap: 2 }}>
                {[['hot', '🔥 Hot Leads'], ['enrolled', '✅ Enrolled'], ['all', '🔍 All']].map(([id, label]) => (
                  <button key={id} onClick={() => setPipelineTab(id)} style={{
                    padding: '6px 14px', borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: pipelineTab === id ? '#FFFFFF' : 'transparent',
                    color: pipelineTab === id ? '#1E1E2E' : '#64748B',
                    fontWeight: pipelineTab === id ? 700 : 500,
                    fontSize: 12, fontFamily: 'inherit',
                    boxShadow: pipelineTab === id ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
                    transition: 'all 0.15s ease',
                  }}>{label}</button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* === Overview === */}
        {tab === 'overview' && (
          <div style={{ ...s.content, display: 'flex', flexDirection: 'row', gap: 24, alignItems: 'stretch', width: '100%' }}>
            {/* Left Column - Stats & Metrics (covers 50%) */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24, minWidth: 0, width: '50%' }}>
              {/* Stat cards inside left column */}
              <div style={s.statsGrid}>
                <StatCard icon="👥" label="Total Sessions" value={analytics?.total_sessions ?? 0} delta={12} color="#6366F1" />
                <StatCard icon="🔍" label="Enquirers" value={analytics?.total_enquirers ?? 0} sub="OTP verified" color="#8B5CF6" />
                <StatCard icon="✅" label="Enrolled" value={analytics?.total_enrolled ?? 0} delta={analytics?.total_enrolled > 0 ? Math.round(analytics.total_enrolled / Math.max(analytics.total_enquirers, 1) * 100) : 0} color="#10B981" />
                <StatCard icon="📈" label="Conversion" value={`${analytics?.conversion_rate ?? 0}%`} sub="Enquiry → Enrollment" color="#F59E0B" />
              </div>

              {/* Sentiment chart */}
              <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', borderRadius: 24, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 8px 30px rgba(0,0,0,0.04)' }}>
                <div style={s.sectionLabel}>Sentiment Breakdown</div>
                {analytics?.sentiment_breakdown && (
                  <SentimentDonut data={analytics.sentiment_breakdown} />
                )}
              </div>

              {/* Secondary stats cards side-by-side */}
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div className="card" style={{ flex: 1, padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 16, borderRadius: 24, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 8px 30px rgba(0,0,0,0.04)', minWidth: 160, transition: 'transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
                  onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                  onMouseLeave={e => e.currentTarget.style.transform = 'none'}
                >
                  <div style={{ width: 40, height: 40, borderRadius: 12, background: '#06B6D414', border: '1px solid #06B6D422', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>📲</div>
                  <div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: '#0A0A0F', letterSpacing: '-0.03em', lineHeight: 1 }}>{analytics?.wa_outbound_log?.length ?? 0}</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#4A5568', marginTop: 4 }}>WA Sent</div>
                  </div>
                </div>
                <div className="card" style={{ flex: 1, padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 16, borderRadius: 24, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 8px 30px rgba(0,0,0,0.04)', minWidth: 160, transition: 'transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
                  onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                  onMouseLeave={e => e.currentTarget.style.transform = 'none'}
                >
                  <div style={{ width: 40, height: 40, borderRadius: 12, background: '#F59E0B14', border: '1px solid #F59E0B22', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>⭐</div>
                  <div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: '#0A0A0F', letterSpacing: '-0.03em', lineHeight: 1 }}>{avgRating}</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#4A5568', marginTop: 4 }}>Avg Rating</div>
                  </div>
                </div>
              </div>

              {/* Hot leads preview */}
              <div className="card" style={{ padding: '24px', borderRadius: 24, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 8px 30px rgba(0,0,0,0.04)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div>
                    <div style={s.sectionLabel}>Hot Leads</div>
                    <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>Unenrolled leads</div>
                  </div>
                  <button className="btn btn-ghost" style={{ fontSize: 12, padding: '5px 10px' }} onClick={() => { setTab('pipeline'); setPipelineTab('hot') }}>
                    View all →
                  </button>
                </div>
                <PipelineTable rows={students.hot_leads.slice(0, 3)} showNudge onNudge={nudge} nudgeStatus={nudgeStatus} />
              </div>
            </div>

            {/* Right Column - Admin AI Copilot (covers 50%) */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, width: '50%', maxHeight: 720 }}>
                <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', background: '#FFFFFF', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 24, boxShadow: '0 8px 30px rgba(0,0,0,0.04)', height: '100%' }}>
                  {/* Copilot Header */}
                  <div style={{ padding: '18px 24px', borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'linear-gradient(135deg, #F8F9FB 0%, #FFFFFF 100%)', display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                      width: 32, height: 32, borderRadius: 10,
                      background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
                      border: '1px solid #C7D2FE',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14
                    }}>
                      🤖
                    </div>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: 14, color: '#0A0A0F' }}>Admin AI Copilot</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 2 }}>
                        <span className="status-dot" style={{ width: 6, height: 6 }} />
                        <span style={{ fontSize: 11, color: '#10B981', fontWeight: 600 }}>Active · Business Intelligence</span>
                      </div>
                    </div>
                  </div>

                  {/* Chat messages */}
                  <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }} className="scroll-area">
                    {copilotMessages.map((m, i) => (
                      <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                        {m.role === 'assistant' && (
                          <div style={{
                            width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                            background: '#EEF2FF', border: '1px solid #C7D2FE',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12
                          }}>
                            🤖
                          </div>
                        )}
                        <div style={{
                          maxWidth: '82%',
                          background: m.role === 'user' ? 'linear-gradient(135deg, #4F46E5, #6366F1)' : '#F8F9FB',
                          color: m.role === 'user' ? '#FFFFFF' : '#1E1E2E',
                          borderRadius: m.role === 'user' ? '16px 16px 0 16px' : '0 16px 16px 16px',
                          padding: '11px 16px',
                          border: m.role === 'user' ? 'none' : '1px solid rgba(0,0,0,0.04)',
                          boxShadow: '0 2px 6px rgba(0,0,0,0.02)',
                          fontSize: 13,
                          lineHeight: 1.6
                        }}>
                          <div style={{ whiteSpace: 'pre-line' }}>
                            {m.content}
                          </div>
                        </div>
                        {m.role === 'user' && (
                          <div style={{
                            width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                            background: '#EEF2FF', border: '1px solid #C7D2FE',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 800, color: '#4F46E5'
                          }}>
                            AD
                          </div>
                        )}
                      </div>
                    ))}
                    {copilotTyping && (
                      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                        <div style={{
                          width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                          background: '#EEF2FF', border: '1px solid #C7D2FE',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12
                        }}>
                          🤖
                        </div>
                        <div style={{ background: '#F8F9FB', border: '1px solid rgba(0,0,0,0.04)', borderRadius: '0 12px 12px 12px', padding: '11px 16px', maxWidth: 64 }}>
                          <div style={{ display: 'flex', gap: 3, alignItems: 'center', height: 8 }}>
                            <span className="dot-typing" style={{ width: 4, height: 4 }} />
                            <span className="dot-typing" style={{ width: 4, height: 4 }} />
                            <span className="dot-typing" style={{ width: 4, height: 4 }} />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Suggestions bar */}
                  <div style={{ padding: '12px 20px', borderTop: '1px solid rgba(0,0,0,0.06)', display: 'flex', gap: 6, flexWrap: 'wrap', background: '#FAFAFA' }}>
                    {[
                      { emoji: '🔥', label: 'Hottest Leads', text: 'Who is our hottest lead right now?' },
                      { emoji: '📈', label: 'Conversion', text: 'Show me our active conversion rate' },
                      { emoji: '⭐', label: 'Reviews', text: 'Summary of course ratings & reviews' },
                      { emoji: '📅', label: 'Batches', text: 'Status of upcoming batches' }
                    ].map(chip => (
                      <button
                        key={chip.text}
                        className="chip"
                        onClick={() => sendCopilotQuery(chip.text)}
                        disabled={copilotTyping}
                        style={{ background: '#FFFFFF', border: '1px solid rgba(0,0,0,0.08)', cursor: 'pointer', padding: '5px 10px', fontSize: 11.5 }}
                      >
                        <span>{chip.emoji}</span> {chip.label}
                      </button>
                    ))}
                  </div>

                  {/* Input bar */}
                  <div style={{ padding: '14px 20px 18px', borderTop: '1px solid rgba(0,0,0,0.06)', display: 'flex', gap: 8 }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      background: '#F8F9FB',
                      border: '1px solid rgba(0,0,0,0.08)',
                      borderRadius: 14,
                      padding: '4px 6px 4px 12px',
                      flex: 1,
                      transition: 'all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                      boxShadow: '0 2px 12px rgba(0,0,0,0.03)',
                    }}>
                      <input
                        className="input"
                        style={{ border: 'none', outline: 'none', flex: 1, padding: '8px 12px', background: 'transparent', fontSize: 13.5 }}
                        placeholder="Ask Admin Copilot..."
                        value={copilotInput}
                        onChange={e => setCopilotInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendCopilotQuery()}
                        disabled={copilotTyping}
                      />
                      <button
                        onClick={() => sendCopilotQuery()}
                        disabled={!copilotInput.trim() || copilotTyping}
                        style={{
                          width: 34, height: 34, borderRadius: 10, border: 'none',
                          background: copilotInput.trim() && !copilotTyping ? '#4F46E5' : '#E2E8F0',
                          color: copilotInput.trim() && !copilotTyping ? '#fff' : '#94A3B8',
                          cursor: copilotInput.trim() && !copilotTyping ? 'pointer' : 'default',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15, flexShrink: 0,
                          transition: 'all 0.2s ease',
                          boxShadow: copilotInput.trim() && !copilotTyping ? '0 4px 10px rgba(79,70,229,0.25)' : 'none'
                        }}
                      >
                        {copilotTyping ? '⏳' : '↑'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        {/* === Pipeline === */}
        {tab === 'pipeline' && (
          <div style={s.content}>
            <div className="card" style={{ padding: '24px' }}>
              {pipelineTab === 'hot' && (
                <>
                  <div style={s.tableHeader}>
                    <div>
                      <div style={s.sectionLabel}>🔥 Hot Leads <span style={s.countBadge}>{students.hot_leads.length}</span></div>
                      <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>Unenrolled · High engagement · Ready to convert</div>
                    </div>
                  </div>
                  <PipelineTable rows={students.hot_leads} showNudge onNudge={nudge} nudgeStatus={nudgeStatus} />
                </>
              )}
              {pipelineTab === 'enrolled' && (
                <>
                  <div style={s.tableHeader}>
                    <div style={s.sectionLabel}>✅ Enrolled Students <span style={s.countBadge}>{students.enrolled.length}</span></div>
                  </div>
                  <PipelineTable rows={students.enrolled} />
                </>
              )}
              {pipelineTab === 'all' && (
                <>
                  <div style={s.tableHeader}>
                    <div style={s.sectionLabel}>🔍 All Enquirers <span style={s.countBadge}>{students.investigated.length}</span></div>
                  </div>
                  <PipelineTable rows={students.investigated} />
                </>
              )}
            </div>
          </div>
        )}

        {/* === WA Log === */}
        {tab === 'wa_log' && (
          <div style={s.content}>
            <div className="card" style={{ padding: '24px' }}>
              <div style={s.tableHeader}>
                <div>
                  <div style={s.sectionLabel}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <span className="status-dot" style={{ width: 7, height: 7 }}/>
                      WhatsApp Outbound Log
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>Real-time stream of all WhatsApp messages sent by EduFlow AI</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {(analytics?.wa_outbound_log || []).map(e => <WALogEntry key={e.id} entry={e} />)}
                {(!analytics?.wa_outbound_log || analytics.wa_outbound_log.length === 0) && (
                  <div style={{ textAlign: 'center', padding: '40px 0', color: '#94A3B8' }}>
                    <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>No messages sent yet</div>
                    <div style={{ fontSize: 12, marginTop: 4 }}>Start a chat to see WA messages appear here in real time.</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* === Reviews === */}
        {tab === 'reviews' && (
          <div style={s.content}>
            {/* Summary bar */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
              <div className="card" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ fontSize: 40, fontWeight: 800, color: '#0A0A0F', lineHeight: 1 }}>{avgRating}</div>
                <div>
                  <div style={{ display: 'flex', gap: 2 }}>
                    {[1,2,3,4,5].map(n => (
                      <span key={n} style={{ fontSize: 18, color: n <= Math.round(parseFloat(avgRating) || 0) ? '#F59E0B' : '#E2E8F0' }}>★</span>
                    ))}
                  </div>
                  <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 4 }}>{reviews.length} reviews total</div>
                </div>
              </div>
              <div className="card" style={{ padding: '20px 24px', flex: 1, minWidth: 200 }}>
                {[5,4,3,2,1].map(n => {
                  const count = reviews.filter(r => r.rating === n).length
                  return (
                    <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: '#64748B', width: 16, textAlign: 'right' }}>{n}</span>
                      <span style={{ color: '#F59E0B', fontSize: 11 }}>★</span>
                      <div className="progress-bar" style={{ flex: 1 }}>
                        <div className="progress-fill" style={{ width: `${reviews.length ? count / reviews.length * 100 : 0}%` }}/>
                      </div>
                      <span style={{ fontSize: 11, color: '#94A3B8', width: 20, textAlign: 'right' }}>{count}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            <div style={s.reviewGrid}>
              {reviews.map(r => <ReviewCard key={r.id} review={r} />)}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

const s = {
  sidebar: {
    width: 228, flexShrink: 0, background: '#FFFFFF',
    borderRight: '1px solid rgba(0,0,0,0.06)',
    display: 'flex', flexDirection: 'column',
  },
  sidebarTop: {
    padding: '20px 16px', borderBottom: '1px solid rgba(0,0,0,0.06)',
  },
  sidebarLogo: {
    width: 32, height: 32, borderRadius: 12, flexShrink: 0,
    background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
    border: '1px solid #C7D2FE',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(79,70,229,0.15)',
  },
  livePill: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '7px 16px', background: '#ECFDF5',
    borderBottom: '1px solid rgba(0,0,0,0.06)',
    fontSize: 11, fontWeight: 700, color: '#059669', letterSpacing: '0.02em',
  },
  navItem: {
    display: 'flex', alignItems: 'center', gap: 9, width: '100%',
    padding: '9px 12px', border: 'none', cursor: 'pointer',
    borderRadius: 12, fontFamily: 'inherit', fontSize: 13,
    transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)', textAlign: 'left', marginBottom: 2,
  },
  sidebarBottom: {
    padding: '12px 8px', borderTop: '1px solid rgba(0,0,0,0.06)',
    display: 'flex', flexDirection: 'column', gap: 4,
  },
  refreshBtn: {
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '9px 12px', borderRadius: 12, border: 'none',
    background: 'transparent', cursor: 'pointer', color: '#64748B',
    fontSize: 13, fontWeight: 500, fontFamily: 'inherit',
    transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)', width: '100%', textAlign: 'left',
  },
  chatLink: {
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '9px 12px', borderRadius: 12, textDecoration: 'none',
    color: '#64748B', fontSize: 13, fontWeight: 500,
    transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
  },
  main: {
    flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column',
  },
  pageHeader: {
    display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
    padding: '24px 28px 16px', background: '#FFFFFF',
    borderBottom: '1px solid rgba(0,0,0,0.06)', flexShrink: 0,
  },
  pageTitle: {
    fontSize: 20, fontWeight: 800, color: '#0A0A0F', letterSpacing: '-0.02em',
  },
  pageSub: { fontSize: 13, color: '#94A3B8', marginTop: 4 },
  content: {
    padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20, flex: 1,
  },
  statsGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 14,
  },
  twoCol: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
  },
  sectionLabel: {
    fontSize: 14, fontWeight: 700, color: '#0A0A0F', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8,
  },
  tableHeader: { marginBottom: 16 },
  countBadge: {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    background: '#EEF2FF', color: '#4F46E5', fontSize: 11, fontWeight: 700,
    padding: '1px 8px', borderRadius: 999, marginLeft: 6,
  },
  reviewGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 14,
  },
}
