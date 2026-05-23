import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import * as Sentry from '@sentry/react'
import Clarity from '@microsoft/clarity'

Sentry.init({
  dsn: "https://627ab330e91f7fe21f6800a3f679d0d1@o4511439056338944.ingest.de.sentry.io/4511439067611216",
  integrations: [
    Sentry.browserTracingIntegration(),
  ],
  tracesSampleRate: 1.0,
})

Clarity.init("wvkr93m76x")

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
