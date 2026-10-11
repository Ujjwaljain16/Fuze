import React, { useEffect, useState } from 'react'
import { Link2, CheckCircle2 } from 'lucide-react'
import api from '../services/api'
import { startGoogleOAuth, OAUTH_MODES } from '../services/oauth'

const ConnectedAccounts = () => {
  const [connected, setConnected] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get('/api/profile')
      .then((res) => setConnected(Boolean(res.data?.google_connected)))
      .catch(() => setConnected(false))
  }, [])

  const connect = () => {
    setError(null)
    try {
      startGoogleOAuth(OAUTH_MODES.LINK)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl p-4 md:p-6 hover:border-cyan-500/30 transition-all duration-300">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="p-2 md:p-3 bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-xl">
            <i className="fab fa-google text-cyan-400" aria-hidden="true" style={{ fontSize: 20 }} />
          </div>
          <div>
            <h2 className="text-lg md:text-xl font-semibold text-white">Google sign-in</h2>
            <p className="text-sm text-gray-400">
              {connected ? 'You can sign in with Google.' : 'Connect the Google account that uses this email.'}
            </p>
          </div>
        </div>
        {connected ? (
          <span className="flex items-center gap-2 text-sm text-emerald-400">
            <CheckCircle2 className="w-4 h-4" /> Connected
          </span>
        ) : (
          <button
            type="button"
            onClick={connect}
            disabled={connected === null}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-600 text-white hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            <Link2 className="w-4 h-4" /> Connect Google
          </button>
        )}
      </div>
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </div>
  )
}

export default ConnectedAccounts
