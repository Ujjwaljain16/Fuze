import { AlertCircle, RefreshCw, Wifi, Shield, Clock, Server } from 'lucide-react'
import { ERROR_TYPES } from '../services/api'

const ErrorDisplay = ({
  error,
  onRetry,
  className = '',
  showRetry = true,
  compact = false,
  context = ''
}) => {
  if (!error) return null

  const getErrorConfig = (errorType) => {
    switch (errorType) {
      case ERROR_TYPES.NETWORK:
        return {
          icon: Wifi,
          title: 'Connection Problem',
          color: 'text-orange-400',
          bgColor: 'bg-orange-500/10',
          borderColor: 'border-orange-500/20'
        }
      case ERROR_TYPES.AUTH:
        return {
          icon: Shield,
          title: 'Authentication Required',
          color: 'text-red-400',
          bgColor: 'bg-red-500/10',
          borderColor: 'border-red-500/20'
        }
      case ERROR_TYPES.RATE_LIMIT:
        return {
          icon: Clock,
          title: 'Too Many Requests',
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-500/10',
          borderColor: 'border-yellow-500/20'
        }
      case ERROR_TYPES.SERVER:
        return {
          icon: Server,
          title: 'Server Issue',
          color: 'text-cyan-400',
          bgColor: 'bg-cyan-500/10',
          borderColor: 'border-cyan-500/20'
        }
      case ERROR_TYPES.VALIDATION:
        return {
          icon: AlertCircle,
          title: 'Invalid Input',
          color: 'text-cyan-400',
          bgColor: 'bg-cyan-500/10',
          borderColor: 'border-cyan-500/20'
        }
      default:
        return {
          icon: AlertCircle,
          title: 'Something Went Wrong',
          color: 'text-gray-400',
          bgColor: 'bg-gray-500/10',
          borderColor: 'border-gray-500/20'
        }
    }
  }

  const config = getErrorConfig(error.type)
  const Icon = config.icon

  if (compact) {
    return (
      <div className={`flex items-center gap-2 p-3 rounded-lg ${config.bgColor} border ${config.borderColor} ${className}`}>
        <Icon size={16} className={config.color} />
        <span className={`text-sm ${config.color}`}>{error.userMessage}</span>
        {showRetry && onRetry && (
          <button
            onClick={onRetry}
            className="ml-auto p-1 rounded hover:bg-white/10 transition-colors"
            title="Retry"
          >
            <RefreshCw size={14} />
          </button>
        )}
      </div>
    )
  }

  return (
    <div className={`rounded-xl border p-6 ${config.bgColor} ${config.borderColor} ${className}`}>
      <div className="flex items-start gap-4">
        <div className={`p-2 rounded-lg ${config.bgColor} ${config.borderColor}`}>
          <Icon size={24} className={config.color} />
        </div>

        <div className="flex-1 min-w-0">
          <h3 className={`font-semibold text-lg mb-2 ${config.color}`}>
            {config.title}
          </h3>

          <p className="text-gray-300 mb-4">
            {error.userMessage}
            {context && <span className="text-gray-400"> ({context})</span>}
          </p>

          {showRetry && onRetry && (
            <button
              onClick={onRetry}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all hover:scale-105 ${config.bgColor} ${config.borderColor} border hover:bg-opacity-20`}
            >
              <RefreshCw size={16} />
              Try Again
            </button>
          )}
        </div>
      </div>

      {/* Development error details */}
      {import.meta.env.DEV && error.originalError && (
        <details className="mt-4">
          <summary className="text-sm text-gray-400 cursor-pointer hover:text-gray-300">
            Error Details (Development)
          </summary>
          <pre className="mt-2 p-3 bg-black/30 rounded text-xs text-red-400 overflow-auto max-h-32">
            {error.originalError.toString()}
          </pre>
        </details>
      )}
    </div>
  )
}

export default ErrorDisplay
