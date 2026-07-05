import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import History from './pages/History'

export default function App() {
  return (
    <BrowserRouter>
      <div className="noise-overlay">
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="process" element={<Dashboard />} />
            <Route path="history" element={<History />} />
          </Route>
        </Routes>
      </div>
    </BrowserRouter>
  )
}
