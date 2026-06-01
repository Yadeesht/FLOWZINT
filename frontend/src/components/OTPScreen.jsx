'use client'

import { useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function OTPScreen({ onVerified }) {
  const [step, setStep] = useState('input')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [demoOtp, setDemoOtp] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSend(e) {
    e.preventDefault()
    if (!name.trim()) return setError('Please enter your name.')
    if (phone.length !== 10) return setError('Enter a valid 10-digit number.')
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API_BASE}/api/otp/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, name: name.trim() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      if (data.demo_otp) setDemoOtp(data.demo_otp)
      setStep('verify')
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  async function handleVerify(e) {
    e.preventDefault()
    if (otp.length !== 6) return setError('Enter the 6-digit OTP.')
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API_BASE}/api/otp/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, otp }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      onVerified({ sessionToken: data.session_token, student: data.student, welcomeMsg: data.message })
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <div style={s.root}>
      {/* Left panel — brand side */}
      <div style={s.brand} className="hide-mobile">
        <div style={s.brandInner}>
          {/* Logo */}
          <div style={s.logo}>
            <div style={s.logoIcon}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5" strokeWidth="0"/>
              </svg>
            </div>
            <span style={s.logoText}>EduFlow AI</span>
          </div>

          {/* Tagline */}
          <div style={{ marginTop: 60 }}>
            <h1 style={s.brandHeading}>Your intelligent<br />course advisor.</h1>
            <p style={s.brandSub}>
              Ask anything. Get answers instantly.<br />
              From fees to schedules to enrollment — all in one chat.
            </p>
          </div>

          {/* Feature pills */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 48 }}>
            {[
              ['⚡', 'Instant answers', 'Course info, fees, schedules'],
              ['🎯', 'Smart enrollment', 'Enroll in under 2 minutes'],
              ['📲', 'WhatsApp alerts', 'OTP, confirmations, reminders'],
              ['🧠', 'AI-powered', 'Contextual, multi-turn conversations'],
            ].map(([icon, title, sub]) => (
              <div key={title} style={s.featurePill}>
                <span style={{ fontSize: 18 }}>{icon}</span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, color: '#1E1E2E' }}>{title}</div>
                  <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 1 }}>{sub}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Bottom stats */}
          <div style={s.statsRow}>
            {[['2,000+', 'Students enrolled'], ['4.9★', 'Avg rating'], ['< 10s', 'Response time']].map(([n, l]) => (
              <div key={l} style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 800, fontSize: 18, color: '#1E1E2E' }}>{n}</div>
                <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 2 }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — form side */}
      <div style={s.formSide}>
        <div style={s.formCard} className="anim-scale-in">
          {/* Mobile logo */}
          <div style={{ ...s.logo, marginBottom: 32, display: 'flex' }} className="hide-desktop">
            <div style={s.logoIcon}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5"/>
              </svg>
            </div>
            <span style={s.logoText}>EduFlow AI</span>
          </div>

          {step === 'input' && (
            <>
              <div style={s.formHeader}>
                <h2 style={s.formTitle}>Get started</h2>
                <p style={s.formSub}>We'll send a one-time code to your WhatsApp to verify your identity.</p>
              </div>

              <form onSubmit={handleSend} style={s.form}>
                <div style={s.fieldWrap}>
                  <label style={s.label} htmlFor="f-name">Your name</label>
                  <input
                    id="f-name"
                    className="input"
                    placeholder="e.g. Yadeesh"
                    value={name}
                    onChange={e => { setName(e.target.value); setError('') }}
                    autoFocus
                    autoComplete="given-name"
                  />
                </div>

                <div style={s.fieldWrap}>
                  <label style={s.label} htmlFor="f-phone">WhatsApp number</label>
                  <div style={s.phoneWrap}>
                    <div style={s.countryCode}>
                      <span>🇮🇳</span>
                      <span>+91</span>
                    </div>
                    <input
                      id="f-phone"
                      className="input"
                      style={{ borderRadius: '0 12px 12px 0', borderLeft: 'none', flex: 1 }}
                      type="tel"
                      inputMode="numeric"
                      maxLength={10}
                      placeholder="10-digit mobile number"
                      value={phone}
                      onChange={e => { setPhone(e.target.value.replace(/\D/g, '')); setError('') }}
                    />
                  </div>
                </div>

                {error && <ErrorBox msg={error} />}

                <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '13px 24px', fontSize: 14 }} disabled={loading}>
                  {loading ? <Spinner /> : <>Send OTP to WhatsApp →</>}
                </button>

                <p style={s.hint}>We only use your number for verification. No spam, ever.</p>
              </form>
            </>
          )}

          {step === 'verify' && (
            <>
              <div style={s.formHeader}>
                <div style={s.otpIcon}>📲</div>
                <h2 style={s.formTitle}>Check your WhatsApp</h2>
                <p style={s.formSub}>
                  We sent a 6-digit OTP to <strong>+91 {phone}</strong>.<br />
                  It expires in 10 minutes.
                </p>
              </div>

              {demoOtp && (
                <div style={s.demoAlert}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span style={{ fontSize: 18, flexShrink: 0 }}>🔧</span>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 13, color: '#92400E' }}>Demo Mode — Twilio not configured</div>
                      <div style={{ fontSize: 13, color: '#B45309', marginTop: 4 }}>
                        Your OTP: <span style={{ fontFamily: 'Geist Mono, monospace', fontWeight: 700, fontSize: 18, letterSpacing: 4, color: '#78350F' }}>{demoOtp}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <form onSubmit={handleVerify} style={s.form}>
                <div style={s.fieldWrap}>
                  <label style={s.label} htmlFor="f-otp">Enter OTP</label>
                  <input
                    id="f-otp"
                    className="input"
                    style={{ textAlign: 'center', fontSize: 24, fontFamily: 'Geist Mono, monospace', fontWeight: 700, letterSpacing: 10, padding: '16px' }}
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="• • • • • •"
                    value={otp}
                    onChange={e => { setOtp(e.target.value.replace(/\D/g, '')); setError('') }}
                    autoFocus
                  />
                </div>

                {error && <ErrorBox msg={error} />}

                <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '13px 24px' }} disabled={loading}>
                  {loading ? <Spinner /> : <>Verify & continue →</>}
                </button>

                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ width: '100%', justifyContent: 'center', fontSize: 13 }}
                  onClick={() => { setStep('input'); setOtp(''); setError(''); setDemoOtp(null) }}
                >
                  ← Change number
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Spinner() {
  return <span className="anim-spin" style={{ width: 16, height: 16, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block' }} />
}

function ErrorBox({ msg }) {
  return (
    <div style={{
      background: '#FFF1F2', border: '1px solid #FECDD3', borderRadius: 10,
      padding: '10px 14px', fontSize: 13, color: '#BE123C', display: 'flex', gap: 8, alignItems: 'flex-start',
    }}>
      <span>⚠</span><span>{msg}</span>
    </div>
  )
}

const s = {
  root: {
    height: '100vh', display: 'flex', background: '#F8F9FB', overflow: 'hidden',
  },
  brand: {
    width: 420, flexShrink: 0, background: '#FFFFFF',
    borderRight: '1px solid rgba(0,0,0,0.06)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: '48px 40px',
  },
  brandInner: { width: '100%', maxWidth: 340 },
  logo: {
    display: 'inline-flex', alignItems: 'center', gap: 10,
  },
  logoIcon: {
    width: 36, height: 36, borderRadius: 10,
    background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
    border: '1px solid #C7D2FE',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 8px rgba(79,70,229,0.15)',
  },
  logoText: {
    fontSize: 16, fontWeight: 800, color: '#1E1E2E', letterSpacing: '-0.01em',
  },
  brandHeading: {
    fontSize: 34, fontWeight: 800, color: '#0A0A0F',
    lineHeight: 1.2, letterSpacing: '-0.03em',
  },
  brandSub: {
    fontSize: 14, color: '#64748B', marginTop: 14, lineHeight: 1.7,
  },
  featurePill: {
    display: 'flex', gap: 14, alignItems: 'center',
    padding: '12px 16px', background: '#FAFAFA',
    border: '1px solid rgba(0,0,0,0.06)', borderRadius: 12,
  },
  statsRow: {
    display: 'flex', justifyContent: 'space-between',
    marginTop: 48, paddingTop: 24, borderTop: '1px solid rgba(0,0,0,0.06)',
  },
  formSide: {
    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 24, overflow: 'auto',
  },
  formCard: {
    width: '100%', maxWidth: 420,
    background: '#FFFFFF', borderRadius: 20,
    padding: '40px 40px',
    border: '1px solid rgba(0,0,0,0.08)',
    boxShadow: '0 8px 40px rgba(0,0,0,0.08)',
  },
  formHeader: { marginBottom: 28 },
  formTitle: { fontSize: 22, fontWeight: 800, color: '#0A0A0F', letterSpacing: '-0.02em' },
  formSub: { fontSize: 14, color: '#64748B', marginTop: 6, lineHeight: 1.65 },
  otpIcon: { fontSize: 36, marginBottom: 12 },
  form: { display: 'flex', flexDirection: 'column', gap: 16 },
  fieldWrap: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: { fontSize: 13, fontWeight: 600, color: '#4A5568' },
  phoneWrap: { display: 'flex', overflow: 'hidden', borderRadius: 12, border: '1px solid rgba(0,0,0,0.10)' },
  countryCode: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '12px 14px', background: '#F8F9FB',
    borderRight: '1px solid rgba(0,0,0,0.08)',
    fontSize: 14, fontWeight: 600, color: '#4A5568', flexShrink: 0,
  },
  hint: { fontSize: 12, color: '#94A3B8', textAlign: 'center' },
  demoAlert: {
    background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 12,
    padding: '14px 16px', marginBottom: 4,
  },
}
