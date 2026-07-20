import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import '../styles/globals.css'
import '../styles/legacy.css'
import SettingsApp from './SettingsApp'

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <SettingsApp />
  </StrictMode>
)
