/**
 * Pure helpers for the "Make a plan to vote" card -- building a downloadable
 * .ics file and Google/Outlook "add event" URLs entirely client-side. No
 * network calls, no stored data; the voter's plan never leaves the browser.
 */

export type VotingMethod = 'mail' | 'early' | 'election_day'

export interface PlanEvent {
  title: string
  description: string
  /** Plain "YYYY-MM-DD", interpreted as a local all-day date -- voting is a
   *  day-level plan, not a specific time, and we don't know polling hours. */
  date: string
}

function icsDateStamp(isoDate: string): string {
  return isoDate.replace(/-/g, '')
}

function foldIcsLine(line: string): string {
  // RFC 5545 §3.1: lines over 75 octets must be folded with a leading space
  // on the continuation. Our lines are short enough in practice, but this
  // keeps the output spec-correct if a title/description ever gets long.
  if (line.length <= 75) return line
  const chunks: string[] = []
  let rest = line
  while (rest.length > 75) {
    chunks.push(rest.slice(0, 75))
    rest = ' ' + rest.slice(75)
  }
  chunks.push(rest)
  return chunks.join('\r\n')
}

function escapeIcsText(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/,/g, '\\,').replace(/;/g, '\\;').replace(/\n/g, '\\n')
}

/** Builds a complete .ics file (VCALENDAR + one all-day VEVENT with a
 *  1-day-before alarm) as a string, ready to hand to a Blob. */
export function buildIcsContent(event: PlanEvent): string {
  const stamp = icsDateStamp(event.date)
  const nextDay = new Date(event.date + 'T00:00:00')
  nextDay.setDate(nextDay.getDate() + 1)
  const dtend = `${nextDay.getFullYear()}${String(nextDay.getMonth() + 1).padStart(2, '0')}${String(nextDay.getDate()).padStart(2, '0')}`

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//ElectMatch//Voting Plan//EN',
    'CALSCALE:GREGORIAN',
    'BEGIN:VEVENT',
    `UID:electmatch-vote-${stamp}-${Math.random().toString(36).slice(2, 8)}@electmatch`,
    `DTSTAMP:${stamp}T000000Z`,
    `DTSTART:${stamp}`,
    `DTEND:${dtend}`,
    `SUMMARY:${escapeIcsText(event.title)}`,
    `DESCRIPTION:${escapeIcsText(event.description)}`,
    'BEGIN:VALARM',
    'ACTION:DISPLAY',
    'TRIGGER:-P1D',
    `DESCRIPTION:${escapeIcsText(event.title)}`,
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ]

  return lines.map(foldIcsLine).join('\r\n') + '\r\n'
}

/** Triggers a browser download of the given .ics content. */
export function downloadIcsFile(event: PlanEvent, filename = 'vote-reminder.ics'): void {
  const blob = new Blob([buildIcsContent(event)], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function googleCalendarUrl(event: PlanEvent): string {
  const stamp = icsDateStamp(event.date)
  const nextDay = new Date(event.date + 'T00:00:00')
  nextDay.setDate(nextDay.getDate() + 1)
  const dtend = `${nextDay.getFullYear()}${String(nextDay.getMonth() + 1).padStart(2, '0')}${String(nextDay.getDate()).padStart(2, '0')}`

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title,
    dates: `${stamp}/${dtend}`,
    details: event.description,
  })
  return `https://calendar.google.com/calendar/render?${params.toString()}`
}

export function outlookCalendarUrl(event: PlanEvent): string {
  const params = new URLSearchParams({
    path: '/calendar/action/compose',
    rru: 'addevent',
    subject: event.title,
    body: event.description,
    startdt: event.date,
    enddt: event.date,
    allday: 'true',
  })
  return `https://outlook.live.com/calendar/0/deeplink/compose?${params.toString()}`
}

export const VOTING_METHOD_LABELS: Record<VotingMethod, string> = {
  mail: 'By mail',
  early: 'Early, in person',
  election_day: 'On Election Day',
}
