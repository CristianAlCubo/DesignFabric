import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
import './styles/globals.css'
import './styles/legacy.css'

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
)
