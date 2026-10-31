import { createContext, useContext, useEffect, useState } from 'react'
import { supabase, authEnabled } from './supabaseClient.js'

const AuthCtx = createContext({ user: null, ready: false, authEnabled })

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(!authEnabled)

  useEffect(() => {
    if (!authEnabled) return
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user ?? null)
      setReady(true)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user ?? null)
    })
    return () => sub.subscription.unsubscribe()
  }, [])

  return <AuthCtx.Provider value={{ user, ready, authEnabled }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)
