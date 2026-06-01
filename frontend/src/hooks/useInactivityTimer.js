'use client'

import { useEffect, useRef, useCallback } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * useInactivityTimer
 *
 * Tracks user inactivity and fires an abandoned-enquiry WhatsApp nudge
 * via the backend /api/inactive endpoint.
 *
 * @param {object} studentData - { phone, name, courseInterest }
 * @param {boolean} active     - only run when student is verified
 * @param {boolean} demoMode   - true = 30s, false = 3 minutes
 * @param {function} onNudgeSent - callback when nudge is dispatched
 */
export function useInactivityTimer({ studentData, active, demoMode = false, onNudgeSent }) {
  const { phone, name, courseInterest, sessionToken } = studentData || {}
  const timerRef = useRef(null)
  const nudgeSentRef = useRef(false)

  const TIMEOUT_MS = demoMode ? 30_000 : 3 * 60 * 1000  // 30s or 3 min

  const triggerNudge = useCallback(async () => {
    if (!phone || nudgeSentRef.current) return

    nudgeSentRef.current = true

    try {
      await fetch(`${API_BASE}/api/inactive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone,
          name,
          course_interest: courseInterest || 'AI/ML Bootcamp',
          discount: 15,
          session_token: sessionToken || null,
        }),
      })

      if (onNudgeSent) onNudgeSent()
    } catch (err) {
      console.error('[Inactivity] Failed to send nudge:', err)
    }
  }, [phone, name, courseInterest, sessionToken, onNudgeSent])

  const resetTimer = useCallback(() => {
    if (!active) return
    clearTimeout(timerRef.current)
    nudgeSentRef.current = false
    timerRef.current = setTimeout(triggerNudge, TIMEOUT_MS)
  }, [active, TIMEOUT_MS, triggerNudge])

  // Reset nudge flag when student sends a new message
  const onStudentMessage = useCallback(() => {
    nudgeSentRef.current = false
    resetTimer()
  }, [resetTimer])

  // Set up timer when active
  useEffect(() => {
    if (!active) {
      clearTimeout(timerRef.current)
      return
    }
    resetTimer()
    return () => clearTimeout(timerRef.current)
  }, [active, demoMode, resetTimer])

  return { resetTimer, onStudentMessage }
}
