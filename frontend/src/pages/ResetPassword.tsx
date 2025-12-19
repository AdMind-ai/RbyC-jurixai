import React, { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import { fetchWithoutAuth } from '../api/fetchWithoutAuth'
import { CircularProgress, useTheme } from '@mui/material'

const ResetPassword: React.FC = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const uid = searchParams.get('uid') || ''
  const token = searchParams.get('token') || searchParams.get('t') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const theme = useTheme()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (password.length < 6) {
      toast.error('La password deve contenere almeno 6 caratteri')
      return
    }
    if (password !== confirmPassword) {
      toast.error('Le password non corrispondono')
      return
    }

    if (!token) {
      toast.error('Token di reimpostazione mancante o non valido')
      return
    }

    setLoading(true)

    try {
      // Some backends expect uid + token + new_password, others token + password.
      const payload: Partial<Record<'token' | 'uid' | 'new_password' | 'password', string>> = { token }
      if (uid) payload.uid = uid
      // common field names used by various backends
      payload.new_password = password
      payload.password = password

      const res = await fetchWithoutAuth('/auth/password-reset/confirm/', {
        method: 'POST',
        body: JSON.stringify(payload),
        headers: { 'Content-Type': 'application/json' },
      })

      const data = await res.json().catch(() => null)
      const msg = data?.detail || data?.error || data?.message || null

      if (res.ok) {
        toast.success(msg || 'Password reimpostata con successo. Puoi effettuare il login.')
        navigate('/login')
      } else {
        toast.error(String(msg || "Impossibile reimpostare la password"))
      }
    } catch (err) {
      console.error('Reset error', err)
      toast.error('An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8">
        <div className="flex flex-col items-center mb-6">
          <img src="/logo.png" alt="Logo" className="w-24 h-24 object-contain" />
          <h1 className="mt-4 text-2xl font-semibold text-gray-800">Reimposta password</h1>
          {!token ? (
            <p className="mt-2 text-sm text-gray-500 text-center">Token di reimpostazione mancante. Usa il link ricevuto via email.</p>
          ) : (
            <p className="mt-2 text-sm text-gray-500 text-center">Inserisci una nuova password per il tuo account.</p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Nuova password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              className="appearance-none block w-full px-4 py-3 border border-gray-200 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          <div>
            <label htmlFor="confirm" className="block text-sm font-medium text-gray-700 mb-1">Conferma password</label>
            <input
              id="confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              className="appearance-none block w-full px-4 py-3 border border-gray-200 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-white font-medium ${loading ? 'cursor-wait' : 'hover:opacity-95'}`}
              style={{
                backgroundColor: loading ? (theme.palette.action?.disabled || theme.palette.primary.main) : theme.palette.primary.main,
                color: theme.palette.primary.contrastText || '#fff',
              }}
            >
              {loading ? (
                <CircularProgress size={20} color="inherit" />
              ) : null}
              {loading ? 'Salvataggio in corso...' : 'Salva nuova password'}
            </button>
          </div>

          <div className="text-center">
            <button type="button" onClick={() => navigate('/login')} className="text-sm text-gray-500 hover:underline">Torna al login</button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ResetPassword
