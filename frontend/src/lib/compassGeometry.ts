export interface CompassInputPoint {
  key: string
  econ: number
  social: number
}

export interface CompassLaidOutPoint extends CompassInputPoint {
  renderEcon: number
  renderSocial: number
  jittered: boolean
  clusterSize: number
}

const DOMAIN = 120
const NEAR_THRESHOLD = 6
const SEPARATION = 9
const MAX_ITERATIONS = 30

function deterministicAngle(key: string): number {
  let hash = 0
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) >>> 0
  return (hash % 360) * (Math.PI / 180)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function separate(
  a: { key: string; renderEcon: number; renderSocial: number },
  b: { key: string; renderEcon: number; renderSocial: number },
): boolean {
  const dx = b.renderEcon - a.renderEcon
  const dy = b.renderSocial - a.renderSocial
  const dist = Math.hypot(dx, dy)
  if (dist >= NEAR_THRESHOLD) return false
  const angle = dist === 0 ? deterministicAngle(a.key + b.key) : Math.atan2(dy, dx)
  const push = (SEPARATION - dist) / 2
  a.renderEcon -= Math.cos(angle) * push
  a.renderSocial -= Math.sin(angle) * push
  b.renderEcon += Math.cos(angle) * push
  b.renderSocial += Math.sin(angle) * push
  return true
}

/**
 * Nudges points that sit almost on top of each other apart, purely for
 * legibility. Callers should keep using the original econ/social values
 * (not renderEcon/renderSocial) for tooltips and any details panel.
 */
export function layoutCompassPoints(
  points: CompassInputPoint[],
  voter: { econ: number; social: number },
): CompassLaidOutPoint[] {
  const anchors = points.map((p) => ({ ...p, renderEcon: p.econ, renderSocial: p.social }))

  for (let iter = 0; iter < MAX_ITERATIONS; iter++) {
    let moved = false
    for (let i = 0; i < anchors.length; i++) {
      for (let j = i + 1; j < anchors.length; j++) {
        if (separate(anchors[i], anchors[j])) moved = true
      }
      const a = anchors[i]
      const dx = a.renderEcon - voter.econ
      const dy = a.renderSocial - voter.social
      const dist = Math.hypot(dx, dy)
      if (dist < NEAR_THRESHOLD) {
        const angle = dist === 0 ? deterministicAngle(a.key) : Math.atan2(dy, dx)
        a.renderEcon += Math.cos(angle) * (SEPARATION - dist)
        a.renderSocial += Math.sin(angle) * (SEPARATION - dist)
        moved = true
      }
    }
    if (!moved) break
  }

  return anchors.map((a) => {
    const clusterSize = 1 + points.filter(
      (p) => p.key !== a.key && Math.hypot(p.econ - a.econ, p.social - a.social) < NEAR_THRESHOLD,
    ).length
    return {
      ...a,
      renderEcon: clamp(a.renderEcon, -DOMAIN, DOMAIN),
      renderSocial: clamp(a.renderSocial, -DOMAIN, DOMAIN),
      jittered: Math.hypot(a.renderEcon - a.econ, a.renderSocial - a.social) > 0.5,
      clusterSize,
    }
  })
}
