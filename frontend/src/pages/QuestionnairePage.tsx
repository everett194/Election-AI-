import { useEffect, useState } from 'react'
import { useNav } from '../context/nav'
import { useAppData, type ImportanceLevel } from '../context/appData'

const POSITION_OPTIONS = [1, 2, 3, 4, 5]

const IMPORTANCE_OPTS: { val: ImportanceLevel; label: string; desc: string }[] = [
  { val: 'low', label: 'Low', desc: 'Not a top priority for me' },
  { val: 'medium', label: 'Medium', desc: 'Somewhat important' },
  { val: 'high', label: 'High', desc: 'Very important to me' },
]

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

function ProgressHeader({ step, total, answeredCount }: { step: number; total: number; answeredCount: number }) {
  const pct = Math.round(((step + 1) / total) * 100)
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-navy">Question {step + 1} of {total}</span>
        <span className="text-xs text-muted font-mono">{answeredCount} answered · {pct}% complete</span>
      </div>
      <div className="relative h-2 bg-soft-mid rounded-full overflow-hidden">
        <div className="h-full bg-civic rounded-full transition-all duration-500 ease-out" style={{ width: `${pct}%` }} />
      </div>
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
    quizAnswers, quizImportance, setQuizAnswer, setQuizImportance, resetQuiz,
    computeResults, resultsStatus, resultsError,
  } = useAppData()

  const [step, setStep] = useState(0)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    void ensureQuestionsLoaded()
  }, [ensureQuestionsLoaded])

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

  const total = questions.length
  const q = questions[step]
  const answerValue = quizAnswers[q.id]
  const importanceVal = quizImportance[q.id] ?? 'medium'
  const answeredCount = Object.values(quizAnswers).filter((v) => v !== undefined).length
  const isAnswered = answerValue !== undefined

  const handleNext = () => {
    if (step < total - 1) setStep(step + 1)
    else setSubmitted(true)
  }
  const handlePrev = () => { if (step > 0) setStep(step - 1) }
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
        onRetake={() => { setStep(0); setSubmitted(false); resetQuiz() }}
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
          <ProgressHeader step={step} total={total} answeredCount={answeredCount} />
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        {resultsError && (
          <div className="mb-5 px-3 py-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">{resultsError}</div>
        )}

        <div className="bg-surface rounded-2xl border border-border shadow-sm overflow-hidden">
          <div className="px-6 sm:px-8 pt-7 pb-5">
            <CategoryBadge id={q.category} label={q.category_label} />

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

          <div className="px-6 sm:px-8 py-5 border-t border-border bg-soft/40">
            <p className="text-xs font-medium text-muted-light uppercase tracking-widest mb-3">
              How important is this issue to you?
            </p>
            <div className="flex gap-2.5">
              {IMPORTANCE_OPTS.map(({ val, label, desc }) => {
                const selected = importanceVal === val
                const activeStyles: Record<ImportanceLevel, string> = {
                  high: selected ? 'bg-gold-light border-gold text-gold-dark' : '',
                  medium: selected ? 'bg-civic-pale border-civic text-civic' : '',
                  low: selected ? 'bg-soft-mid border-border-strong text-navy/60' : '',
                }
                return (
                  <button
                    key={val}
                    onClick={() => setQuizImportance(q.id, val)}
                    title={desc}
                    className={`flex-1 py-3 rounded-xl border text-xs font-semibold capitalize transition-all
                      ${activeStyles[val] || 'bg-surface border-border text-muted hover:border-border-strong hover:bg-soft'}`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </div>

          {step === total - 1 && !isAnswered && (
            <div className="mx-6 mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-center gap-2 text-xs text-amber-700">
              You haven't answered this question. You can still submit — unanswered questions are excluded from match calculations.
            </div>
          )}

          <div className="px-6 sm:px-8 py-5 border-t border-border flex items-center justify-between gap-4">
            <button
              onClick={handlePrev}
              disabled={step === 0}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-border text-sm font-medium text-muted hover:text-navy hover:border-border-strong transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Previous
            </button>

            <div className="hidden sm:flex items-center gap-1 overflow-hidden max-w-[160px] flex-wrap">
              {questions.map((question, i) => {
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
