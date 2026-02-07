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
import Layout from './components/Common/Layout'
import Users from './components/Settings/Users'
import IVR from './components/Settings/IVR'
import Trunks from './components/Settings/Trunks'
import QueuesManager from './components/Queues/QueuesManager'
import ContactsManager from './components/Contacts/ContactsManager'
import RecordingsManager from './components/Recordings/RecordingsManager'

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
        <Layout>
          <Toaster position="top-right" />
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/agent-console" element={<AgentConsole />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/users" element={<Users />} />
            <Route path="/ivr" element={<IVR />} />
            <Route path="/trunks" element={<Trunks />} />
            <Route path="/queues" element={<QueuesManager />} />
            <Route path="/contacts" element={<ContactsManager />} />
            <Route path="/recordings" element={<RecordingsManager />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  )
}

export default App
