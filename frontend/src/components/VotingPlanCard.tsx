/**
 * "Make a plan to vote" card for the results page. Picking a method + date
 * and downloading a calendar reminder is the one action on this page that
 * matters regardless of how confident anyone is in the match percentages
 * below it -- closing the gap between "I know who I'd vote for" and
 * actually voting is the whole point.
 *
 * Entirely client-side: the chosen plan is saved to localStorage only (keyed
 * by zipcode + election date) so it survives a reload, but it's never sent
 * to the backend -- matches this app's "no accounts, no stored PII" model.
 */

import { useEffect, useState } from 'react'
import { Button } from './ui'
import {
  downloadIcsFile,
  googleCalendarUrl,
  outlookCalendarUrl,
  VOTING_METHOD_LABELS,
  type PlanEvent,
  type VotingMethod,
} from '../lib/calendar'

interface VotingPlanCardProps {
  zipcode: string
  /** Earliest election date among the races just researched, "YYYY-MM-DD". */
  electionDate: string | null
  officeLabels: string[]
}

interface StoredPlan {
  method: VotingMethod
  date: string
}

function storageKey(zipcode: string, electionDate: string): string {
  return `electmatch:voting-plan:${zipcode}:${electionDate}`
}

function loadStoredPlan(zipcode: string, electionDate: string): StoredPlan | null {
  try {
    const raw = localStorage.getItem(storageKey(zipcode, electionDate))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<StoredPlan>
    if (typeof parsed.method === 'string' && typeof parsed.date === 'string') {
      return { method: parsed.method as VotingMethod, date: parsed.date }
    }
    return null
  } catch {
    return null
  }
}

function saveStoredPlan(zipcode: string, electionDate: string, plan: StoredPlan): void {
  try {
    localStorage.setItem(storageKey(zipcode, electionDate), JSON.stringify(plan))
  } catch {
    // Best-effort only -- a private window or blocked storage just means
    // the plan won't survive a reload, not a broken page.
  }
}

function formatLongDate(isoDate: string): string {
  return new Date(isoDate + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })
}

const METHOD_ORDER: VotingMethod[] = ['mail', 'early', 'election_day']

export function VotingPlanCard({ zipcode, electionDate, officeLabels }: VotingPlanCardProps) {
  const [method, setMethod] = useState<VotingMethod | null>(null)
  const [date, setDate] = useState('')
  const [confirmed, setConfirmed] = useState(false)

  useEffect(() => {
    if (!electionDate) return
    const stored = loadStoredPlan(zipcode, electionDate)
    if (stored) {
      setMethod(stored.method)
      setDate(stored.date)
      setConfirmed(true)
    } else {
      setMethod(null)
      setDate(electionDate)
      setConfirmed(false)
    }
  }, [zipcode, electionDate])

  const today = new Date().toISOString().slice(0, 10)
  if (!electionDate || electionDate < today) return null

  const title = officeLabels.length > 0 ? `Vote: ${officeLabels.join(', ')}` : 'Vote'
  const description = `Your ElectMatch voting plan${officeLabels.length > 0 ? ` for ${officeLabels.join(', ')}` : ''}.`
  const planDate = date || electionDate
  const event: PlanEvent = { title, description, date: planDate }

  const selectMethod = (m: VotingMethod) => {
    setMethod(m)
    if (m === 'election_day') setDate(electionDate)
    else if (!date) setDate(electionDate)
  }

  const commitPlan = () => {
    if (!method) return
    saveStoredPlan(zipcode, electionDate, { method, date: planDate })
    setConfirmed(true)
  }

  const handleDownload = () => {
    if (!method) return
    downloadIcsFile(event, 'my-voting-plan.ics')
    commitPlan()
  }

  if (confirmed && method) {
    return (
      <div className="bg-teal-light border border-teal/20 rounded-2xl p-5 flex items-start gap-3.5">
        <div className="w-9 h-9 rounded-full bg-teal/15 flex items-center justify-center shrink-0 text-teal">
          <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" clipRule="evenodd" d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="font-semibold text-navy text-sm" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
            You're set to vote {VOTING_METHOD_LABELS[method].toLowerCase()} — {formatLongDate(planDate)}
          </p>
          <p className="text-xs text-navy/60 mt-1">
            Download the reminder below if you haven't already, or add it to your calendar.
          </p>
          <div className="flex flex-wrap items-center gap-3 mt-2.5">
            <button onClick={handleDownload} className="text-xs text-civic hover:text-civic-light font-medium">
              Download .ics
            </button>
            <a href={googleCalendarUrl(event)} target="_blank" rel="noopener noreferrer"
               className="text-xs text-civic hover:text-civic-light font-medium">
              Google Calendar
            </a>
            <a href={outlookCalendarUrl(event)} target="_blank" rel="noopener noreferrer"
               className="text-xs text-civic hover:text-civic-light font-medium">
              Outlook
            </a>
            <button onClick={() => setConfirmed(false)} className="text-xs text-muted hover:text-navy font-medium">
              Change plan
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface border border-teal/30 rounded-2xl p-5 sm:p-6 shadow-sm shadow-teal/5">
      <div className="flex items-center gap-2.5 mb-1">
        <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 text-teal">
          <path fillRule="evenodd" clipRule="evenodd" d="M4.5 1.75a.75.75 0 00-1.5 0V3H2A1.5 1.5 0 00.5 4.5v9A1.5 1.5 0 002 15h12a1.5 1.5 0 001.5-1.5v-9A1.5 1.5 0 0014 3h-1V1.75a.75.75 0 00-1.5 0V3h-7V1.75zM2 6.5h12v7H2v-7z" />
        </svg>
        <h2 className="font-semibold text-navy text-lg" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
          Make a plan to vote
        </h2>
      </div>
      <p className="text-sm text-muted leading-relaxed mb-4 max-w-xl">
        Deciding how and when you'll vote makes you far more likely to follow through. Election day is {formatLongDate(electionDate)}.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
        {METHOD_ORDER.map((m) => (
          <button
            key={m}
            onClick={() => selectMethod(m)}
            className={`py-2.5 px-3 rounded-xl border text-sm font-medium transition-colors text-center
              ${method === m ? 'bg-teal text-white border-teal' : 'border-border text-navy hover:border-teal/50 hover:bg-teal-light/40'}`}
          >
            {VOTING_METHOD_LABELS[m]}
          </button>
        ))}
      </div>

      {method && method !== 'election_day' && (
        <div className="mb-4">
          <label className="block text-xs font-medium text-navy mb-1.5">When do you plan to vote?</label>
          <input
            type="date"
            value={planDate}
            min={today}
            max={electionDate}
            onChange={(e) => setDate(e.target.value)}
            className="py-2 px-3 rounded-xl border border-border text-sm text-navy focus:outline-none focus:ring-2 focus:ring-civic"
          />
        </div>
      )}

      {method && (
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" size="sm" onClick={handleDownload}>
            Add reminder to calendar
          </Button>
          <a href={googleCalendarUrl(event)} target="_blank" rel="noopener noreferrer" onClick={commitPlan}
             className="text-xs text-civic hover:text-civic-light font-medium">
            Google Calendar
          </a>
          <a href={outlookCalendarUrl(event)} target="_blank" rel="noopener noreferrer" onClick={commitPlan}
             className="text-xs text-civic hover:text-civic-light font-medium">
            Outlook
          </a>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-border/60">
        <p className="text-xs text-muted">
          Need to confirm you're registered or find your polling place?{' '}
          <a href="https://www.vote.org" target="_blank" rel="noopener noreferrer"
             className="text-civic hover:text-civic-light font-medium">
            Check at Vote.org ↗
          </a>
        </p>
      </div>
    </div>
  )
}
