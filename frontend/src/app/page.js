'use client'

import { useState } from 'react'
import OTPScreen from '../components/OTPScreen'
import ChatWindow from '../components/ChatWindow'

export default function Home() {
  const [session, setSession] = useState(null)

  return (
    <div style={{ height: '100vh', overflow: 'hidden', background: '#F8F9FB' }}>
      {!session ? (
        <OTPScreen onVerified={({ sessionToken, student, welcomeMsg }) => setSession({ sessionToken, student, welcomeMsg })} />
      ) : (
        <ChatWindow sessionToken={session.sessionToken} student={session.student} welcomeMsg={session.welcomeMsg} />
      )}
    </div>
  )
}
