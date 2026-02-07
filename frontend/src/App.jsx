import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

// Components
import Dashboard from './components/Dashboard/Dashboard'
import AgentConsole from './components/AgentConsole/AgentConsole'
import Campaigns from './components/Campaigns/Campaigns'
import Reports from './components/Reports/Reports'
import Login from './components/Common/Login'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  const [isAuthenticated, setIsAuthenticated] = React.useState(
    !!localStorage.getItem('token')
  )

  if (!isAuthenticated) {
    return <Login onLogin={() => setIsAuthenticated(true)} />
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="app">
          <Toaster position="top-right" />
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/agent-console" element={<AgentConsole />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App
