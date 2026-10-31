import { useState, useCallback, useEffect, useRef } from 'react'
import { useAuth } from './auth.jsx'
import { supabase, authEnabled } from './supabaseClient.js'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const PAGE_SIZE = 10
const FETCH_TIMEOUT_MS = 15000

const SUGGESTED = ['83', '183', '101', 'Kamakshipalya']

const inr = (v) =>
  v == null
    ? null
    : new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

const dmy = (iso) =>
  iso ? new Date(iso + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : null

/* Distinct badge class per status — never red; gray means "no info" */
function StatusBadge({ status }) {
  const s = (status || 'UNKNOWN').toUpperCase()
  const cls =
    s === 'COMPLETED' ? 'st-completed' :
    s === 'ONGOING' ? 'st-ongoing' :
    s === 'OVERDUE' ? 'st-overdue' :
    s === 'NO_COMPLETION_INFORMATION' ? 'st-noinfo' : 'st-unknown'
  const label =
    s === 'NO_COMPLETION_INFORMATION' ? 'no completion info' :
    s === 'UNKNOWN' ? 'status unknown' : s.replaceAll('_', ' ').toLowerCase()
  return <span className={`badge ${cls}`}>{label}</span>
}

function Amount({ value }) {
  const f = inr(value)
  if (!f) return <span className="amount-none">Amount not published</span>
  return <span className="amount">{f}</span>
}

export default function App() {
  const { user, ready } = useAuth()
  const [query, setQuery] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastQuery, setLastQuery] = useState('')
  const [pVisible, setPVisible] = useState(PAGE_SIZE)   // tenders shown
  const [wVisible, setWVisible] = useState(PAGE_SIZE)   // work orders shown
  const [savedList, setSavedList] = useState([])        // user's saved wards, e.g. ['8','101']
  const [wardNames, setWardNames] = useState({})        // {'8': 'Kodigehalli', ...}
  const [savedBusy, setSavedBusy] = useState(false)
  const [email, setEmail] = useState('')
  const [showEmailBox, setShowEmailBox] = useState(false)
  const [authMsg, setAuthMsg] = useState(null)

  const run = useCallback(async (q) => {
    const term = (q || '').trim()
    if (!term) return
    setLoading(true)
    setError(null)
    setData(null)
    setLastQuery(term)
    setPVisible(PAGE_SIZE)
    setWVisible(PAGE_SIZE)
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS)
    try {
      const res = await fetch(`${API_URL}/report?ward=${encodeURIComponent(term)}`, { signal: ctrl.signal })
      if (res.status === 503) throw new Error('upstream')
      if (!res.ok) throw new Error(`status ${res.status}`)
      setData(await res.json())
    } catch (err) {
      setError(
        err.name === 'AbortError'
          ? 'The server took too long to respond. Check that the backend terminal is running, then try again.'
          : 'Couldn\u2019t reach the server \u2014 is the backend running? Start it from the project root with: python -m uvicorn backend.main:app --port 8000, then try again.'
      )
    } finally {
      clearTimeout(timer)
      setLoading(false)
    }
  }, [])

  function onSubmit(e) {
    e.preventDefault()
    run(query)
  }

  /* ---- Saved-wards list (the ONLY auth-gated feature) ---- */

  async function refreshSaved(uid) {
    const { data } = await supabase
      .from('saved_wards')
      .select('ward')
      .eq('user_id', uid)
      .order('created_at', { ascending: true })
    const wards = (data ?? []).map((r) => String(r.ward))
    const missing = wards.filter((w) => !(w in wardNames))
    if (missing.length) {
      const nums = missing.map(Number).filter((n) => !Number.isNaN(n))
      if (nums.length) {
        const { data: wd } = await supabase
          .from('wards')
          .select('ward_number,ward_name')
          .in('ward_number', nums)
        const map = {}
        for (const w of wd ?? []) map[String(w.ward_number)] = w.ward_name
        setWardNames((prev) => ({ ...prev, ...map }))
      }
    }
    setSavedList(wards)
    return wards
  }

  // On login: complete a pending save (from a logged-out save click), then load the list.
  // Ref guard: React StrictMode runs effects twice in dev — second run must be a no-op.
  const loadedForUser = useRef(null)
  useEffect(() => {
    if (!authEnabled || !ready || !user) return
    if (loadedForUser.current === user.id) return
    loadedForUser.current = user.id

    ;(async () => {
      const pending = localStorage.getItem('pendingWard')
      if (pending) {
        localStorage.removeItem('pendingWard')
        await supabase.from('saved_wards').insert({ user_id: user.id, ward: pending })
        setAuthMsg(`Ward ${pending} was added to your saved list.`)
      }
      await refreshSaved(user.id)
    })()
  }, [user, ready])

  const isSaved = data ? savedList.includes(String(data.ward)) : false

  async function saveCurrent() {
    const ward = data?.ward
    if (!user || !ward) return
    if (savedList.includes(String(ward))) return   // already saved — no duplicates
    setSavedBusy(true)
    const { error } = await supabase
      .from('saved_wards')
      .insert({ user_id: user.id, ward: String(ward) })
    if (!error) await refreshSaved(user.id)
    setSavedBusy(false)
  }

  async function removeWard(ward) {
    if (!user || !ward) return
    setSavedList((list) => list.filter((w) => w !== String(ward)))   // optimistic
    await supabase
      .from('saved_wards')
      .delete()
      .eq('user_id', user.id)
      .eq('ward', String(ward))
    await refreshSaved(user.id)
  }

  async function signOut() {
    await supabase.auth.signOut()
    setSavedList([])
    setAuthMsg(null)
    setShowEmailBox(false)
  }

  function onSaveClick() {
    const ward = data?.ward
    if (!ward) return
    if (!user) {
      localStorage.setItem('pendingWard', String(ward))
      setShowEmailBox(true)
      setAuthMsg(null)
    } else {
      saveCurrent()
    }
  }

  async function onMagicLink(e) {
    e.preventDefault()
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: window.location.origin },
    })
    setAuthMsg(
      error
        ? `Could not send the link: ${error.message}`
        : 'Login link sent — check your email and click it to finish saving your ward.'
    )
    if (!error) setShowEmailBox(false)
  }

  return (
    <div className="page">
      <header className="hero">
        <h1>WHOSE MONEY<span className="q">?</span></h1>
        <hr className="rule" />
        <p className="subtitle">See what public BBMP records say about spending in your ward.</p>

        <form onSubmit={onSubmit} className="search" role="search">
          <span className="field">
            <label className="vh" htmlFor="ward-input">Ward number or locality</label>
            <input
              id="ward-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter ward number or locality (e.g. 101 or Kamakshipalya)"
              autoComplete="off"
              disabled={loading}
            />
          </span>
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? <>Checking<span className="spinner" aria-hidden="true" /></> : 'Check My Ward'}
          </button>
        </form>

        <p className="hint">
          Try:{' '}
          {SUGGESTED.map((s, i) => (
            <span key={s}>
              {i > 0 && ' · '}
              <button type="button" className="chip-btn" onClick={() => { setQuery(s); run(s) }} disabled={loading}>
                {s}
              </button>
            </span>
          ))}
        </p>
      </header>

      {authEnabled && user && (
        <section className="card saved-panel" aria-labelledby="saved-heading">
          <div className="saved-head">
            <h3 id="saved-heading">My Saved Wards</h3>
            <button type="button" className="signout" onClick={signOut}>Sign out</button>
          </div>
          {savedList.length === 0 ? (
            <p className="muted">No saved wards yet — open a ward report and click “Save this ward”.</p>
          ) : (
            <ul className="saved-list">
              {savedList.map((w) => (
                <li key={w}>
                  <button type="button" className="ward-link" onClick={() => { setQuery(w); run(w) }}>
                    Ward {w}{wardNames[w] ? ` — ${wardNames[w]}` : ''}
                  </button>
                  <button type="button" className="remove-x" aria-label={`Remove ward ${w}`} onClick={() => removeWard(w)}>×</button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {loading && (
        <div className="card state-card" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          <p className="loading-text">Searching public BBMP records for “{lastQuery}”…</p>
        </div>
      )}

      {error && !loading && (
        <div className="card state-card error-card" role="alert">
          <h2>Something went wrong</h2>
          <p>{error}</p>
          <button type="button" onClick={() => run(lastQuery || query)}>Try again</button>
        </div>
      )}

      {!loading && !error && data && data.message && data.projects.length === 0 && (
        <div className="card state-card" role="status">
          <p className="empty-title">No public tender records were found for this ward in the current dataset.</p>
          <p className="muted">{data.message}</p>
        </div>
      )}

      {!loading && !error && data && !data.message && (
        <main>
          <section className="card ward-card" aria-labelledby="ward-heading">
            <p className="ward-kicker">Ward report</p>
            <h2 id="ward-heading">Ward {data.ward_number} — {data.ward_name}</h2>
            <div className="summary-block">
              <p style={{ margin: 0 }}>{data.summary}</p>
            </div>
            <p className="assessment">{data.assessment}</p>

            {authEnabled && (
              <div className="save-row">
                {user ? (
                  <button
                    type="button"
                    className="save-btn"
                    onClick={saveCurrent}
                    disabled={savedBusy || isSaved}
                    title={isSaved ? 'Already saved — remove it from My Saved Wards' : undefined}
                  >
                    {savedBusy ? 'Saving…' : isSaved ? 'Saved ✓' : 'Save this ward'}
                  </button>
                ) : (
                  <button type="button" className="save-btn" onClick={onSaveClick}>
                    Save this ward
                  </button>
                )}
                {user && <span className="muted">Signed in as {user.email}</span>}

                {showEmailBox && !user && (
                  <form onSubmit={onMagicLink} className="magic-form">
                    <label className="vh" htmlFor="magic-email">Email for magic link</label>
                    <input
                      id="magic-email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                    />
                    <button type="submit">Email me a login link</button>
                  </form>
                )}
                {authMsg && <p className="muted auth-msg">{authMsg}</p>}
              </div>
            )}
          </section>

          <div className="stats">
            <div className="stat"><div className="n">{data.projects.length}</div><div className="l">Tenders (2017-18)</div></div>
            <div className="stat"><div className="n">{data.work_orders.length}</div><div className="l">Work orders w/ payments</div></div>
            <div className="stat"><div className="n">{data.complaints?.total ?? 0}</div><div className="l">Grievances (2024)</div></div>
          </div>

          <section className="card">
            <h3>What the records show</h3>
            <ul className="findings">
              {data.findings.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </section>

          <section className="card">
            <h3>Tendered works ({data.projects.length})</h3>
            {data.projects.slice(0, pVisible).map((p, i) => (
              <article key={i} className="project">
                <div className="project-top">
                  <div className="project-title">{p.title}</div>
                  <StatusBadge status={p.status} />
                </div>
                <div className="project-top" style={{ margin: '4px 0 6px' }}>
                  <Amount value={p.amount} />
                </div>
                <p className="project-sub">
                  Tender published {dmy(p.tender_date) || '—'} · Tender closing date {dmy(p.tender_last_date) || '—'}
                  {p.category ? ` · ${p.category}` : ''}
                </p>
                <dl className="meta">
                  {p.tender_number && <div><dt>Tender number</dt><dd className="mono">{p.tender_number}</dd></div>}
                  <div><dt>Finding</dt><dd>{p.finding}</dd></div>
                </dl>
                {p.evidence?.length > 0 && (
                  <p className="evidence">
                    Source:{' '}
                    {p.evidence.map((ev, j) =>
                      ev.source_url
                        ? <a key={j} href={ev.source_url} target="_blank" rel="noreferrer">{ev.source}</a>
                        : <span key={j}>{ev.source}</span>
                    )}
                  </p>
                )}
              </article>
            ))}
            {data.projects.length > pVisible && (
              <button type="button" className="show-more" onClick={() => setPVisible((n) => n + PAGE_SIZE)}>
                Show 10 more ({data.projects.length - pVisible} remaining)
              </button>
            )}
          </section>

          {data.work_orders.length > 0 && (
            <section className="card">
              <h3>Work orders with payments ({data.work_orders.length})</h3>
              {data.work_orders.slice(0, wVisible).map((w, i) => (
                <article key={i} className="project">
                  <div className="project-top">
                    <div className="project-title">{w.description || w.wo_id || 'Work order'}</div>
                  </div>
                  <div className="project-top" style={{ margin: '4px 0 6px' }}>
                    <Amount value={w.amount} />
                  </div>
                  <dl className="meta">
                    {w.contractor && <div><dt>Contractor</dt><dd>{w.contractor}</dd></div>}
                    {w.payment_ref && <div><dt>Payment ref</dt><dd className="mono small">{w.payment_ref}</dd></div>}
                  </dl>
                  {w.source_url && (
                    <p className="evidence">Source: <a href={w.source_url} target="_blank" rel="noreferrer">OpenCity work orders</a></p>
                  )}
                </article>
              ))}
              {data.work_orders.length > wVisible && (
                <button type="button" className="show-more" onClick={() => setWVisible((n) => n + PAGE_SIZE)}>
                  Show 10 more ({data.work_orders.length - wVisible} remaining)
                </button>
              )}
            </section>
          )}

          {data.complaints && (
            <section className="card">
              <h3>Citizen grievances ({data.complaints.total} in 2024)</h3>
              {data.complaints.top_categories?.length > 0 && (
                <ul className="cats">
                  {data.complaints.top_categories.map((c) => (
                    <li key={c.category}>{c.category} <span className="count">{c.count}</span></li>
                  ))}
                </ul>
              )}
              <p className="muted">{data.complaints.note}</p>
            </section>
          )}
        </main>
      )}

      <footer className="disclaimer">
        <strong>Disclaimer:</strong> Information shown is based on publicly available records.
        A missing update or discrepancy does not by itself establish wrongdoing.
        {data?.data_vintage_note ? ` ${data.data_vintage_note}` : ''}
      </footer>
    </div>
  )
}
