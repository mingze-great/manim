import type { ReactNode } from 'react'

import './GuidedExperience.css'

export function GuidedHero({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description: string
  actions?: ReactNode
}) {
  return (
    <section className="guided-hero">
      <div className="guided-hero__glow" />
      <div className="guided-hero__content">
        {eyebrow ? <div className="guided-hero__eyebrow">{eyebrow}</div> : null}
        <h1 className="guided-hero__title">{title}</h1>
        <p className="guided-hero__desc">{description}</p>
        {actions ? <div className="guided-hero__actions">{actions}</div> : null}
      </div>
    </section>
  )
}

export function StepRail({
  title,
  subtitle,
  steps,
  active,
}: {
  title: string
  subtitle?: string
  steps: Array<{ title: string; desc?: string }>
  active: number
}) {
  return (
    <section className="step-rail">
      <div className="step-rail__header">
        <div>
          <div className="step-rail__title">{title}</div>
          {subtitle ? <div className="step-rail__subtitle">{subtitle}</div> : null}
        </div>
        <div className="step-rail__badge">第 {active + 1} 步</div>
      </div>
      <div className="step-rail__grid">
        {steps.map((step, index) => (
          <div key={`${step.title}-${index}`} className={`step-rail__item ${index === active ? 'is-active' : ''} ${index < active ? 'is-done' : ''}`}>
            <div className="step-rail__index">{String(index + 1).padStart(2, '0')}</div>
            <div className="step-rail__body">
              <div className="step-rail__item-title">{step.title}</div>
              {step.desc ? <div className="step-rail__item-desc">{step.desc}</div> : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export function TipCard({
  title,
  children,
  tone = 'default',
}: {
  title: string
  children: ReactNode
  tone?: 'default' | 'gold' | 'soft'
}) {
  return (
    <div className={`tip-card tip-card--${tone}`}>
      <div className="tip-card__title">{title}</div>
      <div className="tip-card__body">{children}</div>
    </div>
  )
}

export function ChallengeStrip({
  title,
  actions,
}: {
  title: string
  actions: ReactNode
}) {
  return (
    <section className="challenge-strip">
      <div className="challenge-strip__title">{title}</div>
      <div className="challenge-strip__actions">{actions}</div>
    </section>
  )
}

export function SectionShell({ children }: { children: ReactNode }) {
  return <section className="section-shell">{children}</section>
}
