import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/utils/utils'

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center gap-6">
          <span className="font-semibold text-gray-900">Care Plan Generator</span>
          <Link
            to="/"
            className={cn(
              'text-sm',
              location.pathname === '/' ? 'text-blue-600 font-medium' : 'text-gray-500 hover:text-gray-700'
            )}
          >
            New Order
          </Link>
        </div>
      </nav>
      <main className="max-w-4xl mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  )
}
