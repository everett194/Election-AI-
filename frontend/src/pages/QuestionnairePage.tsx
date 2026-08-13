import { useEffect, useMemo, useState } from 'react'
import { useNav } from '../context/nav'
import { useAppData } from '../context/appData'
import type { ApiQuestion } from '../api'
import { MAX_SELECTED_CATEGORIES, MIN_SELECTED_CATEGORIES, RECOMMENDED_SELECTED_CATEGORIES } from '../lib/activeQuestions'

const POSITION_OPTIONS = [1, 2, 3, 4, 5]

const CATEGORY_COLORS: Record<string, string> = {
  housing: 'bg-orange-50 text-orange-700 border-orange-200',
  taxes: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  safety: 'bg-red-50 text-red-700 border-red-200',
  education: 'bg-green-50 text-green-700 border-green-200',
  transportation: 'bg-blue-50 text-blue-700 border-blue-200',
  environment: 'bg-teal-light text-teal border-teal/20',
  accountability: 'bg-purple-50 text-purple-700 border-purple-200',
}

function CategoryBadge({ id, label }: { id: string; label: string }) {
  return (
    <span className={`inline-flex items-center text-[10px] font-mono font-semibold px-3 py-1 rounded-full border uppercase tracking-widest ${CATEGORY_COLORS[id] ?? 'bg-civic-pale text-civic border-civic/20'}`}>
      {label}
    </span>
  )
}

// ─── Stage 1: priority-category picker ──────────────────────────────────────

interface CategoryOption {
  id: string
  label: string
}

function CategoryCard({ option, selected, disabled, onToggle }: {
  option: CategoryOption
  selected: boolean
  disabled: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={selected}
      disabled={disabled}
      className={`text-left px-4 py-3.5 rounded-xl border-2 transition-all duration-150 flex items-start gap-3
        ${selected ? 'border-civic bg-civic-pale shadow-sm' : 'border-border bg-surface hover:border-civic/40 hover:bg-civic-pale/30'}
        ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      <span className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors
        ${selected ? 'bg-civic border-civic' : 'border-border-strong'}`}>
        {selected && (
          <svg viewBox="0 0 16 16" fill="none" stroke="white" strokeWidth="2.5" className="w-3 h-3">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l3.5 3.5L13 5" />
          </svg>
        )}
      </span>
      <span className="text-sm font-medium text-navy leading-snug">{option.label}</span>
    </button>
  )
}

function CategoryStage({ options, selected, onToggle, onContinue }: {
  options: CategoryOption[]
  selected: string[]
  onToggle: (id: string) => void
  onContinue: () => void
}) {
  const { navigate } = useNav()
  const count = selected.length
  const canContinue = count >= MIN_SELECTED_CATEGORIES

  return (
    <div className="min-h-screen bg-soft page-enter">
      <div className="bg-surface border-b border-border sticky top-[60px] z-40">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted">
              <button onClick={() => navigate('home')} className="hover:text-civic">Home</button>
              <span>/</span>
              <span className="text-navy font-medium">Choose your priorities</span>
            </div>
            <span className="text-xs text-muted font-mono">{count} of {MAX_SELECTED_CATEGORIES} selected</span>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <div className="bg-surface rounded-2xl border border-border shadow-sm overflow-hidden">
          <div className="px-6 sm:px-8 pt-7 pb-4">
            <p className="text-xl sm:text-2xl font-semibold text-navy leading-snug" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              Which issues matter most to you?
            </p>
            <p className="mt-2 text-sm text-muted leading-relaxed">
              Pick {MIN_SELECTED_CATEGORIES}-{MAX_SELECTED_CATEGORIES} issues — we recommend {RECOMMENDED_SELECTED_CATEGORIES}. Every issue still counts toward your results; the ones you pick just count more.
            </p>
          </div>

          <div className="px-6 sm:px-8 pb-7 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {options.map((option) => {
              const isSelected = selected.includes(option.id)
              const disabled = !isSelected && count >= MAX_SELECTED_CATEGORIES
              return (
                <CategoryCard
                  key={option.id}
                  option={option}
                  selected={isSelected}
                  disabled={disabled}
                  onToggle={() => onToggle(option.id)}
                />
              )
            })}
          </div>

          <div className="px-6 sm:px-8 py-5 border-t border-border">
            <button
              onClick={onContinue}
              disabled={!canContinue}
              className="w-full py-3 rounded-xl bg-civic text-white font-semibold hover:bg-civic-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Stages 2 & 3: general + personalized policy questions ─────────────────

function ProgressHeader({ step, total, answeredCount, onEditPriorities }: {
  step: number
  total: number
  answeredCount: number
  onEditPriorities: () => void
}) {
  const pct = total > 0 ? Math.round(((step + 1) / total) * 100) : 0
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-navy">Question {step + 1} of {total}</span>
        <span className="text-xs text-muted font-mono">{answeredCount} answered · {pct}% complete</span>
      </div>
      <div className="relative h-2 bg-soft-mid rounded-full overflow-hidden">
        <div className="h-full bg-civic rounded-full transition-all duration-500 ease-out" style={{ width: `${pct}%` }} />
      </div>
      <button onClick={onEditPriorities} className="text-xs text-civic hover:text-civic-light font-medium">
        Edit your priorities
      </button>
    </div>
  )
}

function SubmissionScreen({ answerCount, total, onRetake, onViewResults, computing }: {
  answerCount: number
  total: number
  onRetake: () => void
  onViewResults: () => void
  computing: boolean
}) {
  return (
    <div className="min-h-screen bg-soft flex items-center justify-center p-4 page-enter">
      <div className="max-w-md w-full">
        <div className="bg-surface rounded-2xl border border-border shadow-lg p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-teal-light border-2 border-teal flex items-center justify-center mx-auto mb-5">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-8 h-8 text-teal">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-navy mb-2" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
            Questionnaire complete
          </h2>
          <p className="text-muted text-sm mb-6 leading-relaxed">
            You answered <strong className="text-navy">{answerCount}</strong> of {total} questions.
            Unanswered questions are excluded from match calculations.
          </p>
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-700 text-left mb-6 leading-relaxed">
            <strong>About your results:</strong> Match percentages are estimates based on available evidence and may be incomplete where candidate positions are uncertain. Results are not endorsements.
          </div>
          <button
            onClick={onViewResults}
            disabled={computing}
            className="w-full py-3 rounded-xl bg-civic text-white font-semibold hover:bg-civic-hover transition-colors mb-2.5 disabled:opacity-60"
          >
            {computing ? 'Computing results…' : 'View my alignment results →'}
          </button>
          <button
            onClick={onRetake}
            className="w-full py-3 rounded-xl border border-border text-muted text-sm hover:text-navy hover:border-navy transition-colors"
          >
            Retake from beginning
          </button>
        </div>
      </div>
    </div>
  )
}

export default function QuestionnairePage() {
  const { navigate } = useNav()
  const {
    questions, questionsStatus, ensureQuestionsLoaded,
    selectedIssueCategories, toggleIssueCategory, activeQuestions,
    quizAnswers, setQuizAnswer, resetQuiz,
    computeResults, resultsStatus, resultsError,
  } = useAppData()

  const [stage, setStage] = useState<'categories' | 'questions'>('categories')
  const [step, setStep] = useState(0)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    void ensureQuestionsLoaded()
  }, [ensureQuestionsLoaded])

  // Keep the current step in range if changing categories mid-flow shrinks
  // the active question list.
  useEffect(() => {
    setStep((prev) => (activeQuestions.length === 0 ? 0 : Math.min(prev, activeQuestions.length - 1)))
  }, [activeQuestions.length])

  const categoryOptions = useMemo<CategoryOption[]>(() => {
    const seen = new Set<string>()
    const options: CategoryOption[] = []
    for (const q of questions) {
      if (seen.has(q.category)) continue
      seen.add(q.category)
      options.push({ id: q.category, label: q.category_label })
    }
    return options
  }, [questions])

  if (questionsStatus === 'loading' || questionsStatus === 'idle') {
    return <div className="min-h-screen bg-soft flex items-center justify-center text-muted text-sm">Loading questionnaire…</div>
  }
  if (questionsStatus === 'error' || questions.length === 0) {
    return (
      <div className="min-h-screen bg-soft flex items-center justify-center p-4 text-center">
        <p className="text-sm text-red-700">Could not load the questionnaire. Check that the ElectMatch server is running.</p>
      </div>
    )
  }

  if (stage === 'categories') {
    return (
      <CategoryStage
        options={categoryOptions}
        selected={selectedIssueCategories}
        onToggle={toggleIssueCategory}
        onContinue={() => { setStep(0); setStage('questions') }}
      />
    )
  }

  const total = activeQuestions.length
  const q: ApiQuestion | undefined = activeQuestions[step]
  const answeredCount = activeQuestions.filter((question) => quizAnswers[question.id] !== undefined).length

  if (!q) {
    // Shouldn't happen (every voter has at least the 5 core questions), but
    // fall back to the category picker rather than rendering a blank page.
    return (
      <CategoryStage
        options={categoryOptions}
        selected={selectedIssueCategories}
        onToggle={toggleIssueCategory}
        onContinue={() => { setStep(0); setStage('questions') }}
      />
    )
  }

  const answerValue = quizAnswers[q.id]
  const isAnswered = answerValue !== undefined

  const handleNext = () => {
    if (step < total - 1) setStep(step + 1)
    else setSubmitted(true)
  }
  const handlePrev = () => {
    if (step > 0) setStep(step - 1)
    else setStage('categories')
  }
  const jumpTo = (i: number) => setStep(i)

  const handleViewResults = () => {
    void computeResults().then(() => navigate('results'))
  }

  if (submitted) {
    return (
      <SubmissionScreen
        answerCount={answeredCount}
        total={total}
        computing={resultsStatus === 'loading'}
        onViewResults={handleViewResults}
        onRetake={() => { setStep(0); setSubmitted(false); setStage('categories'); resetQuiz() }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-soft page-enter">
      <div className="bg-surface border-b border-border sticky top-[60px] z-40">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-xs text-muted">
              <button onClick={() => navigate('home')} className="hover:text-civic">Home</button>
              <span>/</span>
              <span className="text-navy font-medium">Questionnaire</span>
            </div>
          </div>
          <ProgressHeader
            step={step}
            total={total}
            answeredCount={answeredCount}
            onEditPriorities={() => setStage('categories')}
          />
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        {resultsError && (
          <div className="mb-5 px-3 py-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">{resultsError}</div>
        )}

        <div className="bg-surface rounded-2xl border border-border shadow-sm overflow-hidden">
          <div className="px-6 sm:px-8 pt-7 pb-5">
            <div className="flex items-center gap-2">
              <CategoryBadge id={q.category} label={q.category_label} />
              {q.is_core && (
                <span className="text-[10px] font-mono font-semibold px-2.5 py-1 rounded-full border border-border text-muted uppercase tracking-widest">
                  General
                </span>
              )}
            </div>

            <p
              className="mt-5 text-xl sm:text-2xl font-semibold text-navy leading-snug"
              style={{ fontFamily: 'Fraunces, Georgia, serif' }}
            >
              {q.text}
            </p>
          </div>

          <div className="px-6 sm:px-8 pb-5 space-y-3">
            <div className="grid grid-cols-2 gap-3 text-xs text-muted">
              <p><span className="font-semibold text-navy">1-2:</span> {q.approach_1}</p>
              <p className="text-right"><span className="font-semibold text-navy">4-5:</span> {q.approach_2}</p>
            </div>

            <p className="text-xs font-medium text-muted-light uppercase tracking-widest pt-2">
              Where do you stand?
            </p>

            <div className="hidden sm:flex gap-2">
              {POSITION_OPTIONS.map((val) => {
                const selected = answerValue === val
                return (
                  <button
                    key={val}
                    onClick={() => setQuizAnswer(q.id, val)}
                    className={`flex-1 py-4 rounded-xl border text-center text-sm font-bold transition-all duration-150
                      ${selected
                        ? 'bg-civic text-white border-civic shadow-sm shadow-civic/20 scale-[1.03]'
                        : 'bg-surface border-border text-navy/60 hover:border-civic/40 hover:text-civic hover:bg-civic-pale'
                      }`}
                  >
                    {val}
                  </button>
                )
              })}
            </div>

            <div className="sm:hidden flex gap-2">
              {POSITION_OPTIONS.map((val) => {
                const selected = answerValue === val
                return (
                  <button
                    key={val}
                    onClick={() => setQuizAnswer(q.id, val)}
                    className={`flex-1 py-3 rounded-xl border text-sm font-bold transition-all
                      ${selected ? 'bg-civic text-white border-civic' : 'bg-surface border-border text-navy/70 hover:border-civic hover:bg-civic-pale'}`}
                  >
                    {val}
                  </button>
                )
              })}
            </div>

            <button
              onClick={() => setQuizAnswer(q.id, null)}
              className={`mt-2.5 w-full py-2.5 rounded-xl border text-sm font-medium transition-all
                ${answerValue === null
                  ? 'bg-soft-mid border-border-strong text-muted'
                  : 'bg-surface border-border text-muted hover:border-border-strong hover:bg-soft'
                }`}
            >
              Not Sure / Skip this question
            </button>
          </div>

          {step === total - 1 && !isAnswered && (
            <div className="mx-6 mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-center gap-2 text-xs text-amber-700">
              You haven't answered this question. You can still submit — unanswered questions are excluded from match calculations.
            </div>
          )}

          <div className="px-6 sm:px-8 py-5 border-t border-border flex items-center justify-between gap-4">
            <button
              onClick={handlePrev}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-border text-sm font-medium text-muted hover:text-navy hover:border-border-strong transition-all"
            >
              ← Previous
            </button>

            <div className="hidden sm:flex items-center gap-1 overflow-hidden max-w-[160px] flex-wrap">
              {activeQuestions.map((question, i) => {
                const isDone = quizAnswers[question.id] !== undefined
                const isCurr = i === step
                return (
                  <button
                    key={question.id}
                    onClick={() => jumpTo(i)}
                    className={`transition-all rounded-full shrink-0 ${
                      isCurr ? 'w-5 h-2 bg-civic' : isDone ? 'w-2 h-2 bg-teal' : 'w-2 h-2 bg-soft-mid hover:bg-border-strong'
                    }`}
                    title={`Question ${i + 1}`}
                  />
                )
              })}
            </div>

            <button
              onClick={handleNext}
              className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-all shadow-sm"
            >
              {step < total - 1 ? 'Next →' : 'View Results →'}
            </button>
          </div>
        </div>

        <p className="mt-5 text-center text-xs text-muted">
          {answeredCount} of {total} answered
        </p>
      </div>
    </div>
  )
}
