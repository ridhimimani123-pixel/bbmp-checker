import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Auth is optional: without these vars the app stays 100% public (report unaffected)
export const authEnabled = Boolean(url && anonKey)

export const supabase = authEnabled
  ? createClient(url, anonKey)
  : null
