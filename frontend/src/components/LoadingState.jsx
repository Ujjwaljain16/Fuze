import { Loader2, Zap } from 'lucide-react'

const LoadingState = ({
  message = 'Loading...',
  size = 'default',
  variant = 'spinner',
  className = '',
  fullScreen = false
}) => {
  const sizeClasses = {
    small: 'w-4 h-4',
    default: 'w-6 h-6',
    large: 'w-8 h-8',
    xl: 'w-12 h-12'
  }

  const containerClasses = fullScreen
    ? 'fixed inset-0 flex items-center justify-center bg-[#0F0F1E]/80 backdrop-blur-sm z-50'
    : 'flex items-center justify-center p-8'

  if (variant === 'skeleton') {
    return (
      <div className={`${containerClasses} ${className}`}>
        <div className="space-y-3 w-full max-w-md">
          <div className="h-4 bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 rounded animate-pulse"></div>
          <div className="h-4 bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 rounded animate-pulse w-3/4"></div>
          <div className="h-4 bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 rounded animate-pulse w-1/2"></div>
        </div>
      </div>
    )
  }

  if (variant === 'card') {
    return (
      <div className={`bg-gradient-to-br from-[#1a1a2e] to-[#252540] rounded-xl border border-cyan-500/20 p-6 ${className}`}>
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 bg-cyan-500/20 rounded-lg flex items-center justify-center">
              <Zap className="w-6 h-6 text-cyan-400 animate-pulse" />
            </div>
            <div className="absolute inset-0 bg-cyan-400/20 rounded-lg animate-ping"></div>
          </div>
          <div>
            <div className="h-4 bg-gradient-to-r from-gray-700 to-gray-600 rounded animate-pulse w-32 mb-2"></div>
            <div className="h-3 bg-gradient-to-r from-gray-800 to-gray-700 rounded animate-pulse w-24"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`${containerClasses} ${className}`}>
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <Loader2 className={`${sizeClasses[size]} text-cyan-400 animate-spin`} />
          <div className="absolute inset-0 bg-cyan-400/20 rounded-full animate-ping opacity-20"></div>
        </div>

        {message && (
          <div className="text-center">
            <p className="text-gray-300 font-medium">{message}</p>
            <p className="text-gray-500 text-sm mt-1">This may take a moment...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default LoadingState
