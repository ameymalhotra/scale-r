import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './styles/fonts.css'
import './index.css'

/* Icon font is ~313 KB and is not used in the About hero. Loading it after
   `load` keeps it off the LCP image's network contention. */
const loadMaterialSymbols = () => {
  import('@fontsource/material-symbols-outlined/latin-400.css')
}
if (document.readyState === 'complete') {
  loadMaterialSymbols()
} else {
  window.addEventListener('load', loadMaterialSymbols, { once: true })
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)