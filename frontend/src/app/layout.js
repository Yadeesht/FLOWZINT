import './globals.css'

export const metadata = {
  title: 'EduFlow AI — Intelligent Course Advisor',
  description: 'AI-powered support and sales bot for EduFlow Coaching Institute. Get instant answers about courses, fees, batch schedules, and enroll in minutes.',
  keywords: 'EduFlow, AI coaching bot, course enquiry, online coaching, AI/ML bootcamp',
  openGraph: {
    title: 'EduFlow AI — Intelligent Course Advisor',
    description: 'Proactive AI that recovers abandoned enquiries and turns visitors into enrolled students.',
    type: 'website',
  },
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        {/* Fonts — Plus Jakarta Sans + Geist Mono */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&family=Geist+Mono:wght@400;500&display=swap"
        />
      </head>
      <body style={{ margin: 0, height: '100vh', overflow: 'hidden', background: '#F8F9FB' }}>
        {children}
      </body>
    </html>
  )
}
