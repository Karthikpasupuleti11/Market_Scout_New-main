import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import * as Sentry from '@sentry/react'
import Clarity from '@microsoft/clarity'

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  integrations: [
    Sentry.browserTracingIntegration(),
  ],
  tracesSampleRate: 1.0,

  beforeSend(event, hint) {
    const error = hint?.originalException;
    const msg = (error?.message || event?.message || '').toLowerCase();

    // Network errors — expected when API is slow or user loses connection
    if (
      msg.includes('failed to fetch') ||
      msg.includes('networkerror') ||
      msg.includes('load failed') ||
      msg.includes('cors') ||
      msg.includes('aborted')
    ) {
      return null;
    }

    // ResizeObserver loop — harmless browser quirk, not a bug
    if (msg.includes('resizeobserver loop')) {
      return null;
    }

    // HTTP 4xx from our API — normal client errors (404, 400, etc.)
    if (error?.status >= 400 && error?.status < 500) {
      return null;
    }

    return event;
  },
})

Clarity.init(import.meta.env.VITE_CLARITY_PROJECT_ID)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
