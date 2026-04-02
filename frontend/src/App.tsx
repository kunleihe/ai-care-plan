import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { NewOrderPage } from './pages/NewOrderPage'
import { CarePlanPage } from './pages/CarePlanPage'
import { DashboardPage } from './pages/DashboardPage'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<NewOrderPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/care-plans/:id" element={<CarePlanPage />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
