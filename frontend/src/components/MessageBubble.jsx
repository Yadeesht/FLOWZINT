'use client'

import { useEffect, useRef } from 'react'

// Inline markdown renderer
function renderMd(text) {
  if (!text) return null
  return text.split('\n').map((line, i) => {
    if (!line.trim()) return <div key={i} style={{ height: 5 }} />

    const isBullet = line.startsWith('• ') || line.startsWith('- ')
    const content = isBullet ? line.slice(2) : line

    const rendered = content.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, j) => {
      if (part.startsWith('**') && part.endsWith('**'))
        return <strong key={j}>{part.slice(2, -2)}</strong>
      if (part.startsWith('*') && part.endsWith('*'))
        return <em key={j} style={{ color: '#4F46E5', fontStyle: 'normal', fontWeight: 600 }}>{part.slice(1, -1)}</em>
      return part
    })

    if (isBullet) {
      return (
        <div key={i} className="md list-item">
          <span className="md list-bullet">·</span>
          <span>{rendered}</span>
        </div>
      )
    }
    return <div key={i} className="md">{rendered}</div>
  })
}

const SENTIMENT_META = {
  positive:   { color: '#10B981', bg: '#ECFDF5', border: '#A7F3D0', label: 'Positive' },
  neutral:    { color: '#6366F1', bg: '#EEF2FF', border: '#C7D2FE', label: 'Neutral' },
  confused:   { color: '#F59E0B', bg: '#FFFBEB', border: '#FDE68A', label: 'Needs clarity' },
  frustrated: { color: '#F43F5E', bg: '#FFF1F2', border: '#FECDD3', label: 'Frustrated' },
}

export default function MessageBubble({ message, studentName, isLatest }) {
  const ref = useRef(null)
  const isBot = message.role === 'bot'
  const sm = SENTIMENT_META[message.sentiment] || SENTIMENT_META.neutral

  useEffect(() => {
    if (isLatest) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [isLatest])

  const ts = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    : null

  if (isBot) {
    return (
      <div ref={ref} className={isLatest ? 'anim-fade-up' : ''} style={s.botRow}>
        <div style={s.botAvatar}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5"/>
          </svg>
        </div>
        <div style={{ maxWidth: 'min(520px, calc(100% - 44px))', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={s.botLabel}>EduFlow AI</div>
          <div style={s.botBubble}>
            <div style={{ fontSize: 14, lineHeight: 1.7, color: '#1E1E2E' }}>
              {renderMd(message.content)}
            </div>
          </div>
          {ts && <span style={s.timestamp}>{ts}</span>}
        </div>
      </div>
    )
  }

  return (
    <div ref={ref} className={isLatest ? 'anim-fade-up' : ''} style={s.userRow}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end', maxWidth: 'min(460px, calc(100% - 44px))' }}>
        <div style={s.userBubble}>
          <span style={{ fontSize: 14, lineHeight: 1.65, color: '#fff' }}>{message.content}</span>
        </div>
        {ts && <span style={{ ...s.timestamp, textAlign: 'right' }}>{ts}</span>}
      </div>
      <div style={s.userAvatar}>
        <span style={{ fontSize: 11, fontWeight: 800, color: '#4F46E5' }}>
          {(studentName || 'U')[0].toUpperCase()}
        </span>
      </div>
    </div>
  )
}

export function TypingIndicator() {
  return (
    <div style={s.botRow} className="anim-fade-in">
      <div style={s.botAvatar}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5"/>
        </svg>
      </div>
      <div style={{ ...s.botBubble, padding: '14px 18px', maxWidth: 80 }}>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center', height: 16 }}>
          <span className="dot-typing" />
          <span className="dot-typing" />
          <span className="dot-typing" />
        </div>
      </div>
    </div>
  )
}

const s = {
  botRow: {
    display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 18,
  },
  botAvatar: {
    width: 32, height: 32, borderRadius: 9, flexShrink: 0,
    background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
    border: '1px solid #C7D2FE',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(79,70,229,0.12)',
  },
  botLabel: {
    fontSize: 11, fontWeight: 700, color: '#6366F1',
    letterSpacing: '0.05em', textTransform: 'uppercase', paddingLeft: 2, marginBottom: 2,
  },
  botBubble: {
    background: '#FFFFFF',
    border: '1px solid rgba(0,0,0,0.08)',
    borderRadius: '4px 16px 16px 16px',
    padding: '14px 18px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
  },
  userRow: {
    display: 'flex', gap: 10, alignItems: 'flex-start',
    justifyContent: 'flex-end', marginBottom: 18,
  },
  userBubble: {
    background: 'linear-gradient(135deg, #4F46E5, #6366F1)',
    borderRadius: '16px 4px 16px 16px',
    padding: '12px 18px',
    boxShadow: '0 4px 16px rgba(79,70,229,0.25)',
  },
  userAvatar: {
    width: 32, height: 32, borderRadius: 9, flexShrink: 0,
    background: '#EEF2FF', border: '1px solid #C7D2FE',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  timestamp: {
    fontSize: 11, color: '#94A3B8', paddingLeft: 2,
  },
}
