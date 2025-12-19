import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { fetchWithoutAuth } from '../api/fetchWithoutAuth'
import { CircularProgress, useTheme } from '@mui/material'

const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const theme = useTheme()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) {
      toast.error("Per favore, inserisci la tua email")
      return
    }

    setLoading(true)
    try {
      const res = await fetchWithoutAuth('/auth/password-reset/', {
        method: 'POST',
        body: JSON.stringify({ email }),
        headers: { 'Content-Type': 'application/json' },
      })

      const data = await res.json().catch(() => null)
      const message = data?.detail || data?.message || null

      if (res.ok) {
        toast.success(message || `Inviato: controlla ${email}`)
        navigate('/login')
      } else {
        toast.error(message || "Impossibile inviare l'email di reimpostazione.")
      }
    } catch (err) {
      console.error('Forgot password error', err)
      toast.error('Si è verificato un errore imprevisto')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8">
        <div className="flex flex-col items-center mb-6">
          <img src="/logo.png" alt="Logo" className="p-12 object-contain" />
          <h1 className="mt-4 text-2xl font-semibold text-gray-800">Reimposta password</h1>
          <p className="mt-2 text-sm text-gray-500 text-center">Inserisci l'indirizzo email del tuo account e ti invieremo un link per reimpostare la password.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="appearance-none block w-full px-4 py-3 border border-gray-200 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="seu@exemplo.com"
              aria-label="email"
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
              {loading ? 'Invio in corso...' : 'Invia link di reimpostazione'}
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

export default ForgotPassword
