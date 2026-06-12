import { useState, useEffect, createContext, useContext, type ReactNode } from 'react'
import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
} from 'amazon-cognito-identity-js'

const USER_POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID || ''
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || ''
const AUTH_ENABLED = !!(USER_POOL_ID && CLIENT_ID)

const userPool = AUTH_ENABLED
  ? new CognitoUserPool({ UserPoolId: USER_POOL_ID, ClientId: CLIENT_ID })
  : null

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  user: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  completeNewPassword: (newPassword: string) => Promise<void>
  needsNewPassword: boolean
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: true,
  user: null,
  login: async () => {},
  logout: () => {},
  completeNewPassword: async () => {},
  needsNewPassword: false,
})

export function useAuth() {
  return useContext(AuthContext)
}

/** Get the current user's Cognito access token — for AgentCore Runtime (validates client_id claim). */
export function getAccessToken(): Promise<string> {
  return new Promise((resolve) => {
    if (!userPool) return resolve('')
    const currentUser = userPool.getCurrentUser()
    if (!currentUser) return resolve('')
    currentUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session?.isValid()) return resolve('')
      resolve(session.getAccessToken().getJwtToken())
    })
  })
}

/** Get the current user's Cognito ID token — for API Gateway (validates aud claim). */
export function getIdToken(): Promise<string> {
  return new Promise((resolve) => {
    if (!userPool) return resolve('')
    const currentUser = userPool.getCurrentUser()
    if (!currentUser) return resolve('')
    currentUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session?.isValid()) return resolve('')
      resolve(session.getIdToken().getJwtToken())
    })
  })
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(!AUTH_ENABLED)
  const [isLoading, setIsLoading] = useState(AUTH_ENABLED)
  const [user, setUser] = useState<string | null>(AUTH_ENABLED ? null : 'demo@voltcycle.com')
  const [needsNewPassword, setNeedsNewPassword] = useState(false)
  const [cognitoUser, setCognitoUser] = useState<CognitoUser | null>(null)
  const [pendingEmail, setPendingEmail] = useState<string>('')

  useEffect(() => {
    if (!userPool) return
    const currentUser = userPool.getCurrentUser()
    if (currentUser) {
      currentUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (!err && session?.isValid()) {
          setIsAuthenticated(true)
          // Get email attribute instead of internal username
          currentUser.getUserAttributes((attrErr, attributes) => {
            const emailAttr = attributes?.find(a => a.getName() === 'email')
            setUser(emailAttr?.getValue() || currentUser.getUsername())
          })
        }
        setIsLoading(false)
      })
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    if (!userPool) return
    return new Promise<void>((resolve, reject) => {
      const authUser = new CognitoUser({ Username: email, Pool: userPool })
      const authDetails = new AuthenticationDetails({ Username: email, Password: password })

      authUser.authenticateUser(authDetails, {
        onSuccess: () => {
          setIsAuthenticated(true)
          setUser(email)
          setNeedsNewPassword(false)
          resolve()
        },
        onFailure: (err) => reject(err),
        newPasswordRequired: () => {
          setCognitoUser(authUser)
          setPendingEmail(email)
          setNeedsNewPassword(true)
          resolve()
        },
      })
    })
  }

  const completeNewPassword = async (newPassword: string) => {
    return new Promise<void>((resolve, reject) => {
      if (!cognitoUser) return reject(new Error('No user session'))
      cognitoUser.completeNewPasswordChallenge(newPassword, {}, {
        onSuccess: () => {
          setIsAuthenticated(true)
          setUser(pendingEmail || cognitoUser.getUsername())
          setNeedsNewPassword(false)
          resolve()
        },
        onFailure: (err) => reject(err),
      })
    })
  }

  const logout = () => {
    if (userPool) {
      const currentUser = userPool.getCurrentUser()
      currentUser?.signOut()
    }
    setIsAuthenticated(false)
    setUser(null)
  }

  // ── Session expiry check ──────────────────────────────────────────
  useEffect(() => {
    if (!userPool || !isAuthenticated) return
    const checkSession = () => {
      const currentUser = userPool.getCurrentUser()
      if (!currentUser) { logout(); return }
      currentUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session?.isValid()) {
          logout()
        }
      })
    }
    // Check every 60 seconds
    const interval = setInterval(checkSession, 60_000)
    return () => clearInterval(interval)
  }, [isAuthenticated])

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, user, login, logout, completeNewPassword, needsNewPassword }}>
      {children}
    </AuthContext.Provider>
  )
}

export function LoginPage() {
  const { login, completeNewPassword, needsNewPassword } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
    } catch (err: any) {
      setError(err.message || 'Login failed')
    }
    setLoading(false)
  }

  const handleNewPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await completeNewPassword(newPassword)
    } catch (err: any) {
      setError(err.message || 'Password change failed')
    }
    setLoading(false)
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '11px 14px', borderRadius: '8px',
    border: '1px solid #334155', background: '#0f172a', color: '#f1f5f9',
    boxSizing: 'border-box', fontSize: '14px', outline: 'none',
    transition: 'border-color 0.15s',
  }

  const formCard = (title: string, subtitle: string, content: React.ReactNode) => (
    <div style={{
      display: 'flex', minHeight: '100vh', background: '#0f172a',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Left branding panel */}
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '60px', background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
      }}>
        <div style={{ maxWidth: 420 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
            <img src="/vite.svg" alt="VoltCycle" style={{ width: 36, height: 36 }} />
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.02em' }}>VoltCycle</div>
              <div style={{ fontSize: 11, color: '#64748b', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.04em' }}>SUPPLY CHAIN OPS</div>
            </div>
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 700, color: '#f1f5f9', lineHeight: 1.2, margin: '0 0 16px' }}>
            AI-Powered Procurement Optimization
          </h1>
          <p style={{ fontSize: 15, color: '#94a3b8', lineHeight: 1.6, margin: '0 0 32px' }}>
            Multi-agent orchestration for e-bike manufacturing. Demand forecasting, supplier optimization, and risk simulation — all in one platform.
          </p>
        </div>
      </div>

      {/* Right form panel */}
      <div style={{
        width: 440, display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '60px 48px', background: '#1e293b',
        borderLeft: '1px solid #334155',
      }}>
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ color: '#f1f5f9', margin: '0 0 6px', fontSize: 22, fontWeight: 700 }}>{title}</h2>
          <p style={{ color: '#94a3b8', fontSize: 14, margin: 0 }}>{subtitle}</p>
        </div>
        {error && (
          <div style={{
            color: '#fca5a5', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
            padding: '10px 14px', borderRadius: 8, fontSize: 13, marginBottom: 16,
          }}>{error}</div>
        )}
        {content}
      </div>
    </div>
  )

  if (needsNewPassword) {
    return formCard('Set New Password', 'Your temporary password must be changed.', (
      <form onSubmit={handleNewPassword}>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 6 }}>New Password</label>
        <input type="password" placeholder="Enter new password" value={newPassword} onChange={e => setNewPassword(e.target.value)}
          style={{ ...inputStyle, marginBottom: 20 }} />
        <button type="submit" disabled={loading} style={{
          width: '100%', padding: '11px', borderRadius: '8px', border: 'none',
          background: loading ? '#1e40af' : '#3b82f6', color: 'white', fontWeight: 600,
          fontSize: 14, cursor: loading ? 'wait' : 'pointer', transition: 'background 0.15s',
        }}>
          {loading ? 'Setting...' : 'Set Password'}
        </button>
      </form>
    ))
  }

  return formCard('Welcome back', 'Sign in to your VoltCycle account', (
    <form onSubmit={handleLogin}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 6 }}>Email</label>
      <input type="email" placeholder="you@voltcycle.com" value={email} onChange={e => setEmail(e.target.value)}
        style={{ ...inputStyle, marginBottom: 16 }} />
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 6 }}>Password</label>
      <input type="password" placeholder="Enter your password" value={password} onChange={e => setPassword(e.target.value)}
        style={{ ...inputStyle, marginBottom: 24 }} />
      <button type="submit" disabled={loading} style={{
        width: '100%', padding: '11px', borderRadius: '8px', border: 'none',
        background: loading ? '#1e40af' : '#3b82f6', color: 'white', fontWeight: 600,
        fontSize: 14, cursor: loading ? 'wait' : 'pointer', transition: 'background 0.15s',
      }}>
        {loading ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  ))
}
