'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import MessageBubble, { TypingIndicator } from './MessageBubble'
import { useInactivityTimer } from '../hooks/useInactivityTimer'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const CHIPS = [
  { emoji: '📚', label: 'Our courses', query: 'Tell me about your courses' },
  { emoji: '📅', label: 'Batch timings', query: 'Show me batch timings and schedules' },
  { emoji: '📲', label: 'WhatsApp Me details', query: 'Please send my batch and course details to my WhatsApp' },
  { emoji: '💰', label: 'Fees & EMI', query: 'What are the fees and EMI options?' },
  { emoji: '🏆', label: 'Placements', query: 'Do you offer placement assistance?' },
  { emoji: '✅', label: 'Enroll now', query: 'I want to enroll' },
]

const SENTIMENT_BORDER = {
  positive: '2px solid #A7F3D0',
  neutral:  '2px solid #C7D2FE',
  confused: '2px solid #FDE68A',
  frustrated: '2px solid #FECDD3',
}

export default function ChatWindow({ sessionToken, student: initialStudent, welcomeMsg }) {
  const [student, setStudent] = useState(initialStudent)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const [sentiment, setSentiment] = useState('neutral')
  const [demoMode, setDemoMode] = useState(false)
  const [nudgeSent, setNudgeSent] = useState(false)
  const [nudgeModalOpen, setNudgeModalOpen] = useState(false)
  const [enrollOpen, setEnrollOpen] = useState(false)
  const [batches, setBatches] = useState([])
  const [enrollStatus, setEnrollStatus] = useState(null)
  const [enrollData, setEnrollData] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [inputFocused, setInputFocused] = useState(false)
  const inputRef = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    setMessages([{
      id: 'w0', role: 'bot',
      content: welcomeMsg || `Hey ${student.name}! 👋 I'm EduFlow AI. How can I help you today?`,
      sentiment: 'positive', timestamp: new Date(),
    }])
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typing])

  const { onStudentMessage } = useInactivityTimer({
    studentData: {
      phone: student.phone, name: student.name,
      courseInterest: student.courseInterest || student.course_interest,
      sessionToken,
    },
    active: true, // Always keep inactivity timer enabled for demo testing
    demoMode,
    onNudgeSent: () => {
      setNudgeSent(true);
      setNudgeModalOpen(true);
      setTimeout(() => setNudgeSent(false), 7000);
    },
  })

  const sendMessage = useCallback(async (text) => {
    const msg = (text || input).trim()
    if (!msg || typing) return
    setInput('')
    const uId = Date.now() + '-u'
    setMessages(p => [...p, { id: uId, role: 'user', content: msg, timestamp: new Date() }])
    setTyping(true)
    onStudentMessage()

    const isEnroll = /\benroll\b|\bjoin\b|\bregister\b/i.test(msg)
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_token: sessionToken, message: msg }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      setSentiment(data.sentiment || 'neutral')
      setMessages(p => [...p, { id: Date.now() + '-b', role: 'bot', content: data.response, sentiment: data.sentiment, timestamp: new Date() }])
      if (isEnroll && !student.enrolled) setTimeout(openEnrollModal, 800)
    } catch (err) {
      setMessages(p => [...p, { id: Date.now() + '-e', role: 'bot', content: `Something went wrong: ${err.message}`, sentiment: 'confused', timestamp: new Date() }])
    } finally {
      setTyping(false)
      inputRef.current?.focus()
    }
  }, [input, typing, sessionToken, student, onStudentMessage])

  async function openEnrollModal() {
    setEnrollOpen(true)
    if (batches.length === 0) {
      const r = await fetch(`${API_BASE}/api/batches`)
      setBatches(await r.json() || [])
    }
  }

  async function doEnroll(batchId) {
    setEnrollStatus('loading')
    try {
      const r = await fetch(`${API_BASE}/api/enroll`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_token: sessionToken, batch_id: batchId }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail)
      setEnrollData(d)
      setEnrollStatus('done')
      setStudent(prev => ({
        ...prev,
        enrolled: true,
        enrolled_course: d.course.id,
        enrolled_batch: d.batch.id,
      }))
      setMessages(p => [...p, {
        id: Date.now() + '-enroll', role: 'bot',
        content: `🎉 Congratulations ${student.name}! You're enrolled in **${d.course.name}**!\n\n📅 **Starts:** ${d.batch.start_date} · ${d.batch.time}\n👨‍🏫 **Instructor:** ${d.batch.instructor}\n\nA WhatsApp confirmation is on its way! 🚀`,
        sentiment: 'positive', timestamp: new Date(),
      }])
    } catch (err) {
      setEnrollStatus(null)
      setEnrollOpen(false)
      setMessages(p => [...p, { id: Date.now() + '-ee', role: 'bot', content: `Enrollment error: ${err.message}`, sentiment: 'frustrated', timestamp: new Date() }])
    }
  }

  const userMsgCount = messages.filter(m => m.role === 'user').length

  return (
    <div style={{ display: 'flex', height: '100%', maxHeight: '100%', overflow: 'hidden', background: '#F8F9FB', position: 'relative' }}>
      {/* === Sidebar Info Panel === */}
      {sidebarOpen && (
        <aside style={s.sidebar} className="anim-fade-in">
          <div style={s.sidebarHeader}>
            <div style={{ fontWeight: 700, fontSize: 14, color: '#1E1E2E' }}>Session Info</div>
            <button className="btn btn-ghost btn-icon" onClick={() => setSidebarOpen(false)} style={{ width: 28, height: 28, fontSize: 16, borderRadius: 8 }}>×</button>
          </div>
          <div style={{ padding: '20px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            <InfoRow label="Name" value={student.name} />
            <InfoRow label="Phone" value={`+91 ${student.phone}`} />
            <InfoRow label="Enrolled" value={student.enrolled ? '✅ Yes' : '—'} />
          </div>
          <div style={{ margin: '0 12px', padding: '12px 16px', borderRadius: 12, background: '#F8F9FB', border: '1px solid rgba(0,0,0,0.06)' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#64748B', marginBottom: 8 }}>INACTIVITY TIMER</div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#1E1E2E' }}>{demoMode ? '30 seconds' : '3 minutes'}</div>
                <div style={{ fontSize: 11, color: '#94A3B8' }}>{demoMode ? 'Demo speed ⚡' : 'Normal mode'}</div>
              </div>
              <button
                className={`toggle-track${demoMode ? ' on' : ''}`}
                onClick={() => setDemoMode(d => !d)}
                title="Demo speed mode (30s inactivity)"
                aria-label="Toggle demo mode"
              >
                <span className="toggle-thumb" />
              </button>
            </div>
          </div>
          <div style={{ padding: '12px 16px', marginTop: 'auto' }}>
            <a href="/admin" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: '#EEF2FF', border: '1px solid #C7D2FE', borderRadius: 10, textDecoration: 'none', color: '#4F46E5', fontSize: 13, fontWeight: 600 }}>
              <span>📊</span> Admin Dashboard
            </a>
          </div>
        </aside>
      )}

      {/* === Main Chat === */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, height: '100%', maxHeight: '100%', overflow: 'hidden' }}>
        {/* Header */}
        <header style={s.header}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn btn-icon" onClick={() => setSidebarOpen(o => !o)} style={{ borderRadius: 10 }} title="Session info">
              <span style={{ fontSize: 15 }}>☰</span>
            </button>
            <div style={s.avatarHeader}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5"/>
              </svg>
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#0A0A0F', lineHeight: 1 }}>EduFlow AI</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 3 }}>
                <span className="status-dot" />
                <span style={{ fontSize: 12, color: '#10B981', fontWeight: 600 }}>Active · Intelligent Support</span>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {!student.enrolled && (
              <button
                id="enroll-btn"
                className="btn btn-primary"
                onClick={openEnrollModal}
                style={{ padding: '8px 18px', fontSize: 13 }}
              >
                Enroll now
              </button>
            )}
          </div>
        </header>

        {/* Sentiment indicator strip */}
        <div style={{
          height: 3, background: 'transparent',
          borderBottom: SENTIMENT_BORDER[sentiment] || '2px solid #C7D2FE',
          transition: 'border-color 0.4s ease',
          flexShrink: 0,
        }} />

        {/* Messages */}
        <div style={s.messagesWrap} className="scroll-area">
          <div style={{ padding: '12px 24px', maxWidth: '100%', margin: '0 auto', width: '100%' }}>
            {messages.map((m, i) => (
              <MessageBubble
                key={m.id}
                message={m}
                studentName={student.name}
                isLatest={i === messages.length - 1}
              />
            ))}
            {typing && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Quick chips — shown before first user message */}
        {userMsgCount === 0 && (
          <div style={s.chipsBar}>
            <div style={{ maxWidth: '100%', margin: '0 auto', width: '100%', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {CHIPS.map(c => (
                <button key={c.label} className="chip" onClick={() => sendMessage(c.query)}>
                  <span>{c.emoji}</span>{c.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Dynamic Suggested Prompts when Focusing Input */}
        {inputFocused && (
          <div style={{
            background: 'rgba(255, 255, 255, 0.85)',
            backdropFilter: 'blur(10px)',
            borderTop: '1px solid rgba(0,0,0,0.04)',
            padding: '8px 16px',
            flexShrink: 0,
            transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
          }} className="anim-fade-up">
            <div style={{ maxWidth: '100%', margin: '0 auto', width: '100%' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#6366F1', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="anim-float" style={{ fontSize: 12 }}>💡</span> Suggested Queries
              </div>
              <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 2 }} className="scroll-area">
                {[
                  { emoji: '🧠', label: 'AI/ML Bootcamp Syllabus', text: 'Tell me about the AI/ML Bootcamp course details and fees' },
                  { emoji: '📲', label: 'WhatsApp details to me', text: 'Send my batch details to my WhatsApp' },
                  { emoji: '💼', label: 'FlowZint Internship Tracks', text: 'Tell me about the FlowZint Corporate Internship domains' },
                  { emoji: '💳', label: 'EMI & Payment Options', text: 'What EMI plans and installment options do you have?' }
                ].map(sug => (
                  <button
                    key={sug.label}
                    onMouseDown={() => sendMessage(sug.text)}
                    style={{
                      padding: '7px 14px',
                      borderRadius: 9999,
                      border: '1px solid rgba(79, 70, 229, 0.15)',
                      background: '#EEF2FF',
                      color: '#4F46E5',
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      whiteSpace: 'nowrap',
                      fontFamily: 'inherit',
                      transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 4px 12px rgba(79, 70, 229, 0.15)';
                      e.currentTarget.style.background = '#4F46E5';
                      e.currentTarget.style.color = '#FFFFFF';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.transform = 'none';
                      e.currentTarget.style.boxShadow = 'none';
                      e.currentTarget.style.background = '#EEF2FF';
                      e.currentTarget.style.color = '#4F46E5';
                    }}
                  >
                    <span>{sug.emoji}</span> {sug.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Input bar */}
        <div style={s.inputBar}>
          <div style={{ maxWidth: '100%', margin: '0 auto', width: '100%', display: 'flex', gap: 10 }}>
            <div style={{
              ...s.inputWrap,
              borderColor: inputFocused ? '#4F46E5' : 'rgba(0,0,0,0.10)',
              boxShadow: inputFocused ? '0 4px 20px rgba(79,70,229,0.08), 0 0 0 3px rgba(79,70,229,0.12)' : '0 2px 12px rgba(0,0,0,0.03)'
            }}>
              <input
                ref={inputRef}
                id="chat-input"
                className="input"
                style={{ border: 'none', outline: 'none', flex: 1, padding: '12px 16px', background: 'transparent', fontSize: 14 }}
                placeholder="Ask anything about EduFlow courses…"
                value={input}
                onChange={e => setInput(e.target.value)}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setTimeout(() => setInputFocused(false), 200)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                autoFocus
              />
              <button
                id="send-btn"
                onClick={() => sendMessage()}
                disabled={!input.trim() || typing}
                style={{
                  width: 40, height: 40, borderRadius: 9999, border: 'none',
                  background: input.trim() && !typing ? 'linear-gradient(135deg, #4F46E5, #6366F1)' : '#E2E8F0',
                  color: input.trim() && !typing ? '#fff' : '#94A3B8',
                  cursor: input.trim() && !typing ? 'pointer' : 'default',
                  transition: 'all 0.25s ease',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 18, flexShrink: 0,
                  boxShadow: input.trim() && !typing ? '0 4px 12px rgba(79,70,229,0.3)' : 'none',
                }}
              >
                {typing ? (
                  <span className="anim-spin" style={{ width: 14, height: 14, border: '2px solid rgba(79,70,229,0.2)', borderTopColor: '#4F46E5', borderRadius: '50%', display: 'inline-block' }} />
                ) : '↑'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* === Enrollment Modal === */}
      {enrollOpen && (
        <div style={s.modalBackdrop} onClick={() => enrollStatus !== 'loading' && setEnrollOpen(false)}>
          <div style={s.modal} className="anim-slide-up" onClick={e => e.stopPropagation()}>
            {enrollStatus === 'done' ? (
              <div style={{ textAlign: 'center', padding: '8px 0' }}>
                <div style={{ fontSize: 52, marginBottom: 16 }}>🎉</div>
                <h3 style={{ fontSize: 22, fontWeight: 800, color: '#0A0A0F', marginBottom: 8 }}>You're in, {student.name}!</h3>
                <p style={{ fontSize: 14, color: '#64748B', marginBottom: 24, lineHeight: 1.6 }}>
                  Enrolled in <strong>{enrollData?.course?.name}</strong>.<br/>
                  Check your WhatsApp for the full confirmation.
                </p>
                <button className="btn btn-primary" style={{ padding: '12px 28px' }} onClick={() => { setEnrollOpen(false); setEnrollStatus(null) }}>
                  Back to chat →
                </button>
              </div>
            ) : (
              <>
                <div style={{ marginBottom: 20 }}>
                  <h3 style={{ fontSize: 18, fontWeight: 800, color: '#0A0A0F' }}>Choose a batch</h3>
                  <p style={{ fontSize: 13, color: '#64748B', marginTop: 4 }}>Pick the timing that works best for you.</p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' }}>
                  {batches.slice(0, 8).map(b => (
                    <button
                      key={b.id}
                      onClick={() => doEnroll(b.id)}
                      disabled={enrollStatus === 'loading' || b.seats_left === 0}
                      style={s.batchItem}
                    >
                      <div style={{ textAlign: 'left', flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: 14, color: '#1E1E2E', marginBottom: 3 }}>
                          {b.id.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </div>
                        <div style={{ fontSize: 12, color: '#64748B' }}>{b.start_date} · {b.time}</div>
                        <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>{b.instructor} · {b.days}</div>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 16 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: b.seats_left <= 5 ? '#F43F5E' : '#10B981' }}>
                          {b.seats_left} left
                        </div>
                        <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 2 }}>{b.mode}</div>
                      </div>
                    </button>
                  ))}
                </div>
                {enrollStatus === 'loading' && (
                  <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}>
                    <span className="anim-spin" style={{ width: 24, height: 24, border: '2px solid #E0E7FF', borderTopColor: '#4F46E5', borderRadius: '50%', display: 'inline-block' }} />
                  </div>
                )}
                <button className="btn btn-secondary" style={{ width: '100%', marginTop: 14 }} onClick={() => setEnrollOpen(false)}>
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* === Inactivity Nudge Explanatory Popup === */}
      {nudgeModalOpen && (
        <div style={s.modalBackdrop} onClick={() => setNudgeModalOpen(false)}>
          <div style={{ ...s.modal, maxWidth: 460 }} className="anim-slide-up" onClick={e => e.stopPropagation()}>
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <div style={{ fontSize: 44, marginBottom: 12 }}>📲</div>
              <h3 style={{ fontSize: 18, fontWeight: 800, color: '#0A0A0F', margin: 0 }}>Proactive Cart Nudge Triggered!</h3>
              <p style={{ fontSize: 12.5, color: '#94A3B8', marginTop: 4 }}>Simulated real-world student recovery scenario</p>
            </div>
            
            <div style={{ background: '#F8F9FB', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 16, padding: '16px', marginBottom: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
                WhatsApp Message Received
              </div>
              <div style={{ background: '#FFFFFF', border: '1px solid rgba(0,0,0,0.06)', borderRadius: '0px 12px 12px 12px', padding: 12, boxShadow: '0 2px 6px rgba(0,0,0,0.03)' }}>
                <div style={{ fontWeight: 700, fontSize: 12.5, color: '#4F46E5', marginBottom: 4 }}>EduFlow AI Support</div>
                <div style={{ fontSize: 13, color: '#1E1E2E', lineHeight: 1.5 }}>
                  Hey **{student.name}**! 👋 We noticed you went quiet while checking our coaching programs. Here's a special **15% discount code** valid for the next 30 minutes to help you get started! 🚀<br/><br/>
                  🎟️ Code: **DISCOUNT15**
                </div>
              </div>
            </div>

            <p style={{ fontSize: 13, color: '#4A5568', lineHeight: 1.6, textAlign: 'center', margin: '0 0 24px 0' }}>
              In production, the student instantly receives this customized offer directly on their WhatsApp phone to recover the abandoned lead. You can inspect this live event log in the **Admin Dashboard Outbox Log**!
            </p>

            <button className="btn btn-primary" style={{ width: '100%', padding: '12px 20px', fontSize: 13.5 }} onClick={() => setNudgeModalOpen(false)}>
              Got it, check Admin Console! →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 12, color: '#94A3B8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: '#1E1E2E' }}>{value}</span>
    </div>
  )
}

const s = {
  sidebar: {
    width: 260, flexShrink: 0, background: '#FFFFFF',
    borderRight: '1px solid rgba(0,0,0,0.06)',
    display: 'flex', flexDirection: 'column',
    boxShadow: '2px 0 12px rgba(0,0,0,0.04)',
  },
  sidebarHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '16px', borderBottom: '1px solid rgba(0,0,0,0.06)',
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '8px 16px', background: '#FFFFFF',
    borderBottom: '1px solid rgba(0,0,0,0.06)',
    flexShrink: 0,
  },
  avatarHeader: {
    width: 36, height: 36, borderRadius: 12, flexShrink: 0,
    background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
    border: '1px solid #C7D2FE',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(79,70,229,0.15)',
  },
  messagesWrap: {
    flex: 1, overflow: 'auto', minHeight: 0, background: '#F8F9FB',
  },
  chipsBar: {
    padding: '6px 16px', background: '#FFFFFF',
    borderTop: '1px solid rgba(0,0,0,0.06)', flexShrink: 0,
  },
  inputBar: {
    padding: '8px 16px 12px', background: '#FFFFFF',
    borderTop: '1px solid rgba(0,0,0,0.06)', flexShrink: 0,
  },
  inputWrap: {
    flex: 1, display: 'flex', alignItems: 'center', gap: 8,
    background: '#F8F9FB', border: '1px solid rgba(0,0,0,0.08)',
    borderRadius: 9999, padding: '4px 6px 4px 16px',
    transition: 'all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    boxShadow: '0 2px 12px rgba(0,0,0,0.03)',
  },
  modalBackdrop: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
    backdropFilter: 'blur(8px)', display: 'flex',
    alignItems: 'center', justifyContent: 'center', padding: 20, zIndex: 100,
  },
  modal: {
    background: '#FFFFFF', borderRadius: 28, padding: '28px 28px',
    width: '100%', maxWidth: 500, maxHeight: '88vh', overflowY: 'auto',
    boxShadow: '0 24px 80px rgba(0,0,0,0.12)',
    border: '1px solid rgba(0,0,0,0.05)',
  },
  batchItem: {
    width: '100%', display: 'flex', alignItems: 'center',
    padding: '14px 16px', background: '#F8F9FB',
    border: '1px solid rgba(0,0,0,0.06)', borderRadius: 16,
    cursor: 'pointer', fontFamily: 'inherit',
    transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)', textAlign: 'left',
  },
}
