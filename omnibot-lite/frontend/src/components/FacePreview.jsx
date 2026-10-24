import { useEffect, useId, useRef } from 'react'

const reducedMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

// Ressort (spring) : remplace le lerp plat par un mouvement avec inertie et
// léger rebond — les expressions « vivent » au lieu de glisser mollement.
function spring(pos, vel, target, k, damp) {
  vel += (target - pos) * k
  vel *= damp
  return [pos + vel, vel]
}

// Visage web paramétrique : interpole les paramètres fournis par le catalogue
// du backend (animations.py) et rejoue les 10 expressions du repo initial.
export default function FacePreview({ anim }) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const svg = {
    group: useRef(null),
    head: useRef(null),
    antennaTip: useRef(null),
    browL: useRef(null),
    browR: useRef(null),
    eyeL: useRef(null),
    eyeR: useRef(null),
    pupilL: useRef(null),
    pupilR: useRef(null),
    mouthLine: useRef(null),
    mouthOpen: useRef(null),
  }
  const cur = useRef({ brow_tilt_l: 0, brow_tilt_r: 0, brow_y: 0, eye_open: 1, pupil_y: 0, mouth_curve: 0.15, mouth_open: 0, mouth_width: 1 })
  const vel = useRef({})
  const animRef = useRef(anim)
  animRef.current = anim

  useEffect(() => {
    let raf = 0
    let blinkStart = -1
    let blink2Start = -1
    let nextBlink = performance.now() + 2200
    let lookPos = 0, lookVel = 0, lookTgt = 0
    let nextSaccade = performance.now() + 2500

    const loop = (t) => {
      const a = animRef.current || { face: {}, speaking: false, deco: [], color: '#8aa2c8' }
      const reduced = reducedMotion()
      const tgt = { ...cur.current, ...a.face }
      const c = cur.current
      const v = vel.current
      for (const k of Object.keys(tgt)) {
        const [p, nv] = spring(c[k], v[k] || 0, tgt[k], 0.16, 0.7)
        c[k] = p
        v[k] = nv
      }

      const sleepy = (a.deco || []).includes('zzz')
      const speaking = !!a.speaking

      // Clignement : onde sinusoïdale (paupière douce), double-clignement occasionnel.
      if (!sleepy && t > nextBlink) {
        blinkStart = t
        blink2Start = Math.random() < 0.18 ? t + 260 : -1
        nextBlink = t + 2200 + Math.random() * 3000
      }
      const BLINK_MS = 150
      const env = (start) =>
        start >= 0 && t - start < BLINK_MS ? Math.sin(Math.PI * (t - start) / BLINK_MS) : 0
      const blinkAmt = Math.max(env(blinkStart), env(blink2Start))
      let eyeOpen = Math.max(0.06, c.eye_open) * (1 - 0.94 * blinkAmt)

      // Saccades : le regard saute vers de nouveaux points plutôt que dérive en sinus.
      if (!reduced && !sleepy && (a.name === 'idle' || a.name === 'thinking' || speaking) && t > nextSaccade) {
        lookTgt = (Math.random() - 0.5) * 12
        nextSaccade = t + 2500 + Math.random() * 3500
      }
      if (sleepy) lookTgt = 0
      ;[lookPos, lookVel] = spring(lookPos, lookVel, lookTgt, 0.25, 0.55)
      let px = lookPos
      let py = c.pupil_y
      if (!reduced && (a.name === 'idle' || speaking)) {
        px += 1.5 * Math.sin(t / 3700)
        py += 1 * Math.sin(t / 2300)
      }

      // Bouche qui parle (mouvement aléatoire doux plutôt qu'un simple sinus).
      let mouthOpen = c.mouth_open
      if (speaking) {
        const wob = 0.5 + 0.5 * Math.sin(t / 95) * (0.6 + 0.4 * Math.sin(t / 53 + 1.7))
        mouthOpen = 0.18 + 0.42 * wob
      }

      // Vie au repos : respiration + micro-tilt de toute la tête.
      const breathe = reduced || sleepy ? 0 : Math.sin(t / 1700)
      const tilt = reduced ? 0 : (sleepy ? 3.5 : 1.4) * Math.sin(t / 4300)
      if (svg.group.current) {
        const s = 1 + 0.018 * breathe + (sleepy && !reduced ? 0.012 * Math.sin(t / 1100) : 0)
        svg.group.current.setAttribute('transform', `translate(100 100) rotate(${tilt.toFixed(2)}) scale(${s.toFixed(4)}) translate(-100 -100)`)
      }

      // Application SVG
      if (svg.head.current) svg.head.current.setAttribute('stroke', a.color || '#8aa2c8')
      if (svg.antennaTip.current) {
        const sway = reduced ? 0 : 2.2 * Math.sin(t / 900 + breathe)
        svg.antennaTip.current.setAttribute('cx', (100 + sway).toFixed(1))
        svg.antennaTip.current.setAttribute('fill', a.color || '#8aa2c8')
      }

      const by = 52 + c.brow_y
      if (svg.browL.current) {
        svg.browL.current.setAttribute('x1', 48)
        svg.browL.current.setAttribute('y1', by + c.brow_tilt_l * -0.15)
        svg.browL.current.setAttribute('x2', 82)
        svg.browL.current.setAttribute('y2', by + c.brow_tilt_l * 0.85)
      }
      if (svg.browR.current) {
        svg.browR.current.setAttribute('x1', 152)
        svg.browR.current.setAttribute('y1', by + c.brow_tilt_r * -0.15)
        svg.browR.current.setAttribute('x2', 118)
        svg.browR.current.setAttribute('y2', by + c.brow_tilt_r * 0.85)
      }

      // Yeux : la paupière réduit le blanc de l'œil (ry) et la pupille s'estompe
      // au lieu d'être écrasée en ligne — clin d'œil plus naturel.
      const eyeRy = Math.max(1.5, 20 * eyeOpen)
      const pupilOp = Math.max(0, Math.min(1, (eyeOpen - 0.28) / 0.35))
      if (svg.eyeL.current) svg.eyeL.current.setAttribute('ry', eyeRy.toFixed(2))
      if (svg.eyeR.current) svg.eyeR.current.setAttribute('ry', eyeRy.toFixed(2))
      if (svg.pupilL.current) {
        svg.pupilL.current.setAttribute('transform', `translate(${px.toFixed(1)} ${py.toFixed(1)})`)
        svg.pupilL.current.setAttribute('opacity', pupilOp.toFixed(2))
      }
      if (svg.pupilR.current) {
        svg.pupilR.current.setAttribute('transform', `translate(${px.toFixed(1)} ${py.toFixed(1)})`)
        svg.pupilR.current.setAttribute('opacity', pupilOp.toFixed(2))
      }

      // Bouche : trait courbe + ouverture en « lentille » dont le bas suit le sourire.
      const w = 34 * c.mouth_width
      const my = 148
      const curveY = c.mouth_curve * 22
      const openNorm = Math.min(1, Math.max(0, (mouthOpen - 0.12) / 0.3))
      if (svg.mouthLine.current) {
        svg.mouthLine.current.setAttribute('d', `M ${100 - w} ${my} Q 100 ${my + curveY + mouthOpen * 4} ${100 + w} ${my}`)
        svg.mouthLine.current.setAttribute('opacity', (1 - openNorm).toFixed(2))
      }
      if (svg.mouthOpen.current) {
        const h = 4 + mouthOpen * 20
        const ow = w * 0.82
        const midY = my + curveY * 0.45
        svg.mouthOpen.current.setAttribute(
          'd',
          `M ${100 - ow} ${my} Q 100 ${midY - h * 0.35} ${100 + ow} ${my} Q 100 ${midY + h} ${100 - ow} ${my} Z`
        )
        svg.mouthOpen.current.setAttribute('opacity', openNorm.toFixed(2))
      }

      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [])

  const deco = anim?.deco || []
  const hearts = deco.includes('heart_eyes')

  return (
    <div className={`face-preview ${anim?.name || 'idle'}`} style={{ '--accent': anim?.color || '#8aa2c8' }}>
      <svg viewBox="0 0 200 200" width="100%" role="img" aria-label={`Visage : ${anim?.label_fr || 'repos'}`}>
        <defs>
          <radialGradient id={`${uid}-fill`} cx="0.5" cy="0.38" r="0.85">
            <stop offset="0" stopColor="#242b38" />
            <stop offset="0.75" stopColor="#1a1f29" />
            <stop offset="1" stopColor="#14181f" />
          </radialGradient>
        </defs>
        <g ref={svg.group}>
          {/* Antenne : petite lumière d'humeur qui suit la couleur du bot */}
          <line x1="100" y1="14" x2="100" y2="5" stroke="#2c3546" strokeWidth="3" strokeLinecap="round" />
          <circle ref={svg.antennaTip} cx="100" cy="4" r="3.2" fill="#8aa2c8" className="antenna-tip" />
          <rect ref={svg.head} x="14" y="14" width="172" height="172" rx="42" fill={`url(#${uid}-fill)`} strokeWidth="3" />
          {/* Sourcils */}
          <line ref={svg.browL} stroke="#e8eef7" strokeWidth="5" strokeLinecap="round" />
          <line ref={svg.browR} stroke="#e8eef7" strokeWidth="5" strokeLinecap="round" />
          {/* Yeux (à gauche) */}
          <g transform="translate(66 86)">
            {!hearts && (
              <g>
                <ellipse ref={svg.eyeL} cx="0" cy="0" rx="17" ry="20" fill="#e8eef7" className="eye-white" />
                <circle ref={svg.pupilL} cx="0" cy="0" r="7" fill="#1b1f27" />
              </g>
            )}
            {hearts && <path d="M0 8 C -12 -4 -12 -16 -4 -16 C 0 -16 0 -12 0 -10 C 0 -12 0 -16 4 -16 C 12 -16 12 -4 0 8 Z" fill="#e56aa0" className="deco-pop" />}
          </g>
          <g transform="translate(134 86)">
            {!hearts && (
              <g>
                <ellipse ref={svg.eyeR} cx="0" cy="0" rx="17" ry="20" fill="#e8eef7" className="eye-white" />
                <circle ref={svg.pupilR} cx="0" cy="0" r="7" fill="#1b1f27" />
              </g>
            )}
            {hearts && <path d="M0 8 C -12 -4 -12 -16 -4 -16 C 0 -16 0 -12 0 -10 C 0 -12 0 -16 4 -16 C 12 -16 12 -4 0 8 Z" fill="#e56aa0" className="deco-pop" />}
          </g>
          {/* Bouche */}
          <path ref={svg.mouthLine} stroke="#e8eef7" strokeWidth="5" strokeLinecap="round" fill="none" />
          <path ref={svg.mouthOpen} fill="#0d1015" stroke="#e8eef7" strokeWidth="3" strokeLinejoin="round" opacity="0" />
          {/* Décorations */}
          {deco.includes('blush') && (
            <g className="deco-fade" fill="#f08080" opacity="0.5">
              <ellipse cx="46" cy="118" rx="11" ry="6" />
              <ellipse cx="154" cy="118" rx="11" ry="6" />
            </g>
          )}
          {deco.includes('tear') && <path className="deco-tear" d="M150 106 q 4 8 0 12 q -4 -4 0 -12 Z" fill="#6e9bd8" />}
          {deco.includes('steam') && (
            <g className="deco-steam" stroke="#9fb6d8" strokeWidth="3" fill="none" strokeLinecap="round">
              <path d="M162 30 q 6 -8 0 -16 q -6 -8 0 -14" />
              <path d="M174 34 q 6 -8 0 -16" />
            </g>
          )}
          {deco.includes('zzz') && (
            <g className="deco-zzz" fill="#aab4e0" fontFamily="monospace" fontWeight="bold">
              <text x="158" y="42" fontSize="14">z</text>
              <text x="172" y="30" fontSize="18">z</text>
              <text x="186" y="18" fontSize="22">Z</text>
            </g>
          )}
          {deco.includes('question') && <text className="deco-pop" x="100" y="26" fontSize="24" fill="#4fc3a1" textAnchor="middle" fontWeight="bold">?</text>}
          {deco.includes('sweat') && <path className="deco-fade" d="M44 46 q 6 10 0 15 q -6 -5 0 -15 Z" fill="#7fc8e8" />}
          {deco.includes('sparkles') && (
            <g className="deco-sparkle" fill="#f2c14e">
              <path d="M30 40 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 Z" />
              <path d="M170 60 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2 Z" />
              <path d="M40 160 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2 Z" />
            </g>
          )}
        </g>
      </svg>
    </div>
  )
}
