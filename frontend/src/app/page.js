'use client'

import { useState } from 'react'
import OTPScreen from '../components/OTPScreen'
import ChatWindow from '../components/ChatWindow'
import AdminDashboard from '../components/AdminDashboard'

export default function Home() {
  const [view, setView] = useState('choice') // 'choice' | 'chatbot' | 'admin'
  const [session, setSession] = useState(null)

  if (view === 'chatbot') {
    return (
      <div style={{ height: '100vh', overflow: 'hidden', background: '#F8F9FB', position: 'relative' }}>
        {/* Quick Portal Switcher Bar */}
        <div style={s.navBackBar}>
          <button onClick={() => setView('choice')} style={s.navBackBtn}>
            ← Back to Portal Gateway
          </button>
        </div>
        <div style={{ height: 'calc(100vh - 40px)', overflow: 'hidden' }}>
          {!session ? (
            <OTPScreen onVerified={({ sessionToken, student, welcomeMsg }) => setSession({ sessionToken, student, welcomeMsg })} />
          ) : (
            <ChatWindow sessionToken={session.sessionToken} student={session.student} welcomeMsg={session.welcomeMsg} />
          )}
        </div>
      </div>
    )
  }

  if (view === 'admin') {
    return (
      <div style={{ height: '100vh', overflow: 'hidden', background: '#F8F9FB', position: 'relative' }}>
        {/* Quick Portal Switcher Bar */}
        <div style={s.navBackBar}>
          <button onClick={() => setView('choice')} style={s.navBackBtn}>
            ← Back to Portal Gateway
          </button>
        </div>
        <div style={{ height: 'calc(100vh - 40px)', overflow: 'hidden' }}>
          <AdminDashboard />
        </div>
      </div>
    )
  }

  return (
    <div style={s.gatewayWrap}>
      <div style={s.gatewayContainer} className="anim-slide-up">
        {/* Brand header */}
        <header style={s.gatewayHeader}>
          <div style={s.badge}>FLOWZINT HACKATHON 2026</div>
          <div style={s.logoWrap}>
            <div style={s.logoIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#4F46E5" />
              </svg>
            </div>
            <h1 style={s.logoText}>EduFlow AI</h1>
          </div>
          <h2 style={s.title}>Experience the Proactive AI Advisor</h2>
          <p style={s.subtitle}>
            Explore our state-of-the-art dual-view platform. Choose your entry point to evaluate the customer journey or view administrative intelligence.
          </p>
        </header>

        {/* Portal Cards */}
        <div style={s.grid}>
          {/* Card 1: Chatbot */}
          <div
            style={s.portalCard}
            onClick={() => setView('chatbot')}
            className="card hover-elevate"
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-6px)'
              e.currentTarget.style.boxShadow = '0 20px 40px rgba(79, 70, 229, 0.12)'
              e.currentTarget.style.borderColor = 'rgba(79, 70, 229, 0.3)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'none'
              e.currentTarget.style.boxShadow = '0 8px 30px rgba(0,0,0,0.06)'
              e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'
            }}
          >
            <div style={s.iconWrap(false)}>
              <span style={{ fontSize: 28 }}>🤖</span>
            </div>
            <div style={s.cardMeta}>CUSTOMER-FACING EXPERIENCES</div>
            <h3 style={s.cardTitle}>Student AI Advisor</h3>
            <p style={s.cardDesc}>
              Simulate a student's journey. Request a WhatsApp OTP, enquire about premium bootcamps, trigger live sentiments, and experience our <strong>Abandoned Enquiry Recovery System</strong>.
            </p>
            <ul style={s.featuresList}>
              <li>🔐 <strong>Instant WhatsApp OTP</strong> onboarding</li>
              <li>💬 <strong>Sentiment-Adaptive</strong> UI themes</li>
              <li>⚡ <strong>Inactivity cart nudges</strong> (Demo mode toggle)</li>
            </ul>
            <button className="btn btn-primary" style={s.cardBtn(false)}>
              Enter Student View →
            </button>
          </div>

          {/* Card 2: Admin Dashboard */}
          <div
            style={s.portalCard}
            onClick={() => setView('admin')}
            className="card hover-elevate"
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-6px)'
              e.currentTarget.style.boxShadow = '0 20px 40px rgba(16, 185, 129, 0.12)'
              e.currentTarget.style.borderColor = 'rgba(16, 185, 129, 0.3)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'none'
              e.currentTarget.style.boxShadow = '0 8px 30px rgba(0,0,0,0.06)'
              e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'
            }}
          >
            <div style={s.iconWrap(true)}>
              <span style={{ fontSize: 28 }}>📊</span>
            </div>
            <div style={s.cardMeta}>ANALYTICS & CONVERSIONS</div>
            <h3 style={s.cardTitle}>Admin Dashboard</h3>
            <p style={s.cardDesc}>
              Dive into management analytics. Monitor student pipeline groups, inspect cumulative sentiment models, trigger manual Twilio nudges, and observe real-time simulated WhatsApp messages.
            </p>
            <ul style={s.featuresList}>
              <li>📈 <strong>Live student pipeline</strong> analytics</li>
              <li>◉ <strong>WhatsApp outbound logs</strong> (Delivered/Simulated)</li>
              <li>⭐ <strong>Course ratings</strong> & review distributions</li>
            </ul>
            <button className="btn" style={s.cardBtn(true)}>
              Enter Admin Console →
            </button>
          </div>
        </div>

        {/* Footer */}
        <footer style={s.footer}>
          <span>Built for FlowZint AI Hackathon 2026</span>
          <span style={s.footerDot}>•</span>
          <span>Zero-setup fallback mode active</span>
        </footer>
      </div>
    </div>
  )
}

const s = {
  gatewayWrap: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #F8F9FB 0%, #E8ECF3 100%)',
    padding: '40px 24px',
    overflowY: 'auto',
  },
  gatewayContainer: {
    width: '100%',
    maxWidth: 960,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  gatewayHeader: {
    textAlign: 'center',
    marginBottom: 44,
    maxWidth: 640,
  },
  badge: {
    display: 'inline-block',
    padding: '5px 12px',
    background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
    border: '1px solid #C7D2FE',
    color: '#4F46E5',
    fontSize: 11,
    fontWeight: 800,
    borderRadius: 999,
    letterSpacing: '0.06em',
    marginBottom: 16,
  },
  logoWrap: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  logoIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    background: '#FFFFFF',
    border: '1px solid rgba(0,0,0,0.06)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 12px rgba(79,70,229,0.15)',
  },
  logoText: {
    fontSize: 22,
    fontWeight: 800,
    color: '#0A0A0F',
    letterSpacing: '-0.02em',
  },
  title: {
    fontSize: 32,
    fontWeight: 800,
    color: '#0A0A0F',
    letterSpacing: '-0.03em',
    lineHeight: 1.25,
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 15,
    color: '#64748B',
    lineHeight: 1.6,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
    gap: 24,
    width: '100%',
    marginBottom: 48,
  },
  portalCard: {
    background: '#FFFFFF',
    border: '1px solid rgba(0,0,0,0.06)',
    borderRadius: 24,
    padding: '36px',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    boxShadow: '0 8px 30px rgba(0,0,0,0.06)',
  },
  iconWrap: (isAdmin) => ({
    width: 56,
    height: 56,
    borderRadius: 16,
    background: isAdmin ? 'linear-gradient(135deg, #ECFDF5, #D1FAE5)' : 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
    border: `1px solid ${isAdmin ? '#A7F3D0' : '#C7D2FE'}`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    boxShadow: `0 4px 14px ${isAdmin ? 'rgba(16,185,129,0.15)' : 'rgba(79,70,229,0.15)'}`,
  }),
  cardMeta: {
    fontSize: 10.5,
    fontWeight: 800,
    color: '#94A3B8',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: 800,
    color: '#0A0A0F',
    letterSpacing: '-0.02em',
    marginBottom: 10,
  },
  cardDesc: {
    fontSize: 13.5,
    color: '#64748B',
    lineHeight: 1.6,
    marginBottom: 20,
  },
  featuresList: {
    padding: 0,
    margin: '0 0 28px 0',
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    fontSize: 13,
    color: '#4A5568',
  },
  cardBtn: (isAdmin) => ({
    width: '100%',
    padding: '13px 20px',
    fontSize: 13.5,
    fontWeight: 700,
    borderRadius: 12,
    border: isAdmin ? '1px solid #10B981' : 'none',
    background: isAdmin ? 'transparent' : '#4F46E5',
    color: isAdmin ? '#10B981' : '#FFFFFF',
    marginTop: 'auto',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  }),
  footer: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    fontSize: 12,
    color: '#94A3B8',
    fontWeight: 500,
  },
  footerDot: {
    color: '#CBD5E1',
  },
  navBackBar: {
    height: 40,
    background: '#0F172A',
    display: 'flex',
    alignItems: 'center',
    padding: '0 16px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    zIndex: 1000,
    position: 'relative',
  },
  navBackBtn: {
    background: 'none',
    border: 'none',
    color: '#E2E8F0',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    transition: 'color 0.15s ease',
  },
}
