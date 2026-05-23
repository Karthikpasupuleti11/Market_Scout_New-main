import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import * as Sentry from '@sentry/react'
import Clarity from '@microsoft/clarity'

const sentryDsn = import.meta.env.VITE_SENTRY_DSN
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 1.0,
    beforeSend(event, hint) {
      const error = hint?.originalException
      const msg = (error?.message || event?.message || '').toLowerCase()

      if (
        msg.includes('failed to fetch') ||
        msg.includes('networkerror') ||
        msg.includes('load failed') ||
        msg.includes('cors') ||
        msg.includes('aborted')
      ) {
        return null
      }

      if (msg.includes('resizeobserver loop')) {
        return null
      }

      if (error?.status >= 400 && error?.status < 500) {
        return null
      }

      return event
    },
  })
}

const clarityId = import.meta.env.VITE_CLARITY_PROJECT_ID
if (clarityId) {
  Clarity.init(clarityId)
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
