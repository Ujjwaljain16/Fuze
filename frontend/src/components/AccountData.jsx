import React, { useState } from 'react'
import { useNavigate } from 'react-router'
import { Download, Trash2, AlertTriangle, Lock } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

const exportFilename = () => `fuze-export-${new Date().toISOString().slice(0, 10)}.json`

// The API is on another site, so Content-Disposition isn't readable here; save the blob ourselves.
const saveBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

const AccountData = ({ hasPassword = true }) => {
  const { logout } = useAuth()
  const { success, error: showError } = useToast()
  const navigate = useNavigate()
  const [exporting, setExporting] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [password, setPassword] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState(null)

  const exportData = async () => {
    setExporting(true)
    try {
      const response = await api.get('/api/account/export', { responseType: 'blob' })
      saveBlob(response.data, exportFilename())
      success('Your data export has been downloaded')
    } catch (err) {
      showError(err.response?.status === 429
        ? 'Too many exports. Please try again later.'
        : 'Failed to export your data. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const cancelDelete = () => {
    setConfirming(false)
    setPassword('')
    setDeleteError(null)
  }

  const deleteAccount = async (e) => {
    e.preventDefault()
    if (hasPassword && !password) {
      setDeleteError('Enter your password to confirm')
      return
    }
    setDeleting(true)
    setDeleteError(null)
    try {
      await api.delete('/api/account', { data: hasPassword ? { password } : {} })
      logout()
      navigate('/', { replace: true })
    } catch (err) {
      const data = err.response?.data
      setDeleteError(data?.error === 'recent_sign_in_required'
        ? 'For your security, sign out and sign in again, then delete your account.'
        : data?.message || 'Failed to delete your account. Please try again.')
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-8">
      <div className="bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl p-4 md:p-6 hover:border-cyan-500/30 transition-all duration-300">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-2 md:p-3 bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-xl">
              <Download className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-lg md:text-xl font-semibold text-white">Your data</h2>
              <p className="text-sm text-gray-400">
                Download your profile, bookmarks, projects and feedback as a JSON file.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={exportData}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-600 text-white hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            <Download className="w-4 h-4" /> {exporting ? 'Preparing...' : 'Export my data'}
          </button>
        </div>
      </div>

      <div className="bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-red-500/30 rounded-2xl p-4 md:p-6 transition-all duration-300">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="p-2 md:p-3 bg-gradient-to-r from-red-600/20 to-orange-600/20 rounded-xl">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h2 className="text-lg md:text-xl font-semibold text-white">Delete account</h2>
              <p className="text-sm text-gray-400">
                Permanently delete your account and everything in it. This cannot be undone.
              </p>
            </div>
          </div>
          {!confirming && (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl border border-red-500/40 text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <Trash2 className="w-4 h-4" /> Delete account
            </button>
          )}
        </div>

        {confirming && (
          <form onSubmit={deleteAccount} className="mt-6 space-y-4">
            <p className="text-sm text-gray-300">
              All your bookmarks, projects, tasks and recommendation history will be deleted, and you
              will be signed out everywhere. Consider exporting your data first.
            </p>
            {hasPassword && (
              <div className="group">
                <label htmlFor="delete-account-password" className="block text-sm font-medium text-gray-300 mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-red-400 transition-colors duration-300" />
                  <input
                    id="delete-account-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    className="w-full pl-12 pr-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/20 transition-all duration-300 text-white placeholder-gray-400"
                    placeholder="Enter your password to confirm"
                  />
                </div>
              </div>
            )}
            {deleteError && <p role="alert" className="text-sm text-red-400">{deleteError}</p>}
            <div className="flex justify-end gap-3 flex-wrap">
              <button
                type="button"
                onClick={cancelDelete}
                disabled={deleting}
                className="px-4 py-2 rounded-xl border border-gray-600 text-white hover:bg-white/5 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={deleting}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600/80 text-white hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" /> {deleting ? 'Deleting...' : 'Delete permanently'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default AccountData
