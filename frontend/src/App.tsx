import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './views/Dashboard'
import ArticleBrowser from './views/ArticleBrowser'
import ArticleDetail from './views/ArticleDetail'
import ReviewQueue from './views/ReviewQueue'
import AuditLogView from './views/AuditLogView'
import Settings from './views/Settings'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="browser" element={<ArticleBrowser />} />
            <Route path="browser/:id" element={<ArticleDetail />} />
            <Route path="queue" element={<ReviewQueue />} />
            <Route path="audit" element={<AuditLogView />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
