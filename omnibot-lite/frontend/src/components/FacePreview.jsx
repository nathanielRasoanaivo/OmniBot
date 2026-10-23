import { useEffect, useRef } from 'react'

// Visage web paramétrique : interpole les paramètres fournis par le catalogue
// du backend (animations.py) et rejoue les 10 expressions du repo initial.
export default function FacePreview({ anim }) {
  const svg = {
    head: useRef(null),
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
  const tgt = useRef({ ...cur.current })
  const animRef = useRef(anim)
  animRef.current = anim

  useEffect(() => {
    let raf = 0
    let blinkUntil = 0
    let nextBlink = performance.now() + 2200

    const loop = (t) => {
      const a = animRef.current || { face: {}, speaking: false, deco: [], color: '#8aa2c8' }
      tgt.current = { ...cur.current, ...a.face }
      const c = cur.current
      for (const k of Object.keys(tgt.current)) {
        c[k] += (tgt.current[k] - c[k]) * 0.12
      }

      const sleepy = (a.deco || []).includes('zzz')
      const speaking = !!a.speaking

      // Clignement (sauf endormi)
      if (!sleepy && t > nextBlink) {
        blinkUntil = t + 130
        nextBlink = t + 2200 + Math.random() * 3000
      }
      const blink = !sleepy && t < blinkUntil ? 0.06 : 1
      let eyeOpen = Math.max(0.06, c.eye_open) * blink

      // Micro-dérive du regard au repos
      let px = 0
      let py = c.pupil_y
      if (a.name === 'idle' || speaking) {
        px += 4 * Math.sin(t / 3700)
        py += 2 * Math.sin(t / 2300)
      }

      // Bouche qui parle
      let mouthOpen = c.mouth_open
      if (speaking) {
        const wob = 0.5 + 0.5 * Math.sin(t / 95) * (0.6 + 0.4 * Math.sin(t / 53))
        mouthOpen = 0.18 + 0.42 * wob
      }

      // Application SVG
      if (svg.head.current) svg.head.current.setAttribute('stroke', a.color || '#8aa2c8')

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

      for (const [g, p] of [[svg.eyeL, svg.pupilL], [svg.eyeR, svg.pupilR]]) {
        if (g.current) g.current.setAttribute('transform', `scale(1 ${eyeOpen.toFixed(3)})`)
        if (p.current) p.current.setAttribute('transform', `translate(${px.toFixed(1)} ${py.toFixed(1)})`)
      }

      const w = 34 * c.mouth_width
      const openNorm = Math.min(1, Math.max(0, (mouthOpen - 0.12) / 0.3))
      if (svg.mouthLine.current) {
        svg.mouthLine.current.setAttribute('d', `M ${100 - w} 148 Q 100 ${148 + c.mouth_curve * 20 + mouthOpen * 4} ${100 + w} 148`)
        svg.mouthLine.current.setAttribute('opacity', (1 - openNorm).toFixed(2))
      }
      if (svg.mouthOpen.current) {
        svg.mouthOpen.current.setAttribute('rx', (w * 0.72).toFixed(1))
        svg.mouthOpen.current.setAttribute('ry', (4 + mouthOpen * 16).toFixed(1))
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
        <rect ref={svg.head} x="14" y="14" width="172" height="172" rx="42" fill="#1b1f27" strokeWidth="3" />
        {/* Sourcils */}
        <line ref={svg.browL} stroke="#e8eef7" strokeWidth="5" strokeLinecap="round" />
        <line ref={svg.browR} stroke="#e8eef7" strokeWidth="5" strokeLinecap="round" />
        {/* Yeux (à gauche) */}
        <g transform="translate(66 86)">
          {!hearts && (
            <g ref={svg.eyeL}>
              <ellipse cx="0" cy="0" rx="17" ry="20" fill="#e8eef7" />
              <circle ref={svg.pupilL} cx="0" cy="0" r="7" fill="#1b1f27" />
            </g>
          )}
          {hearts && <path d="M0 8 C -12 -4 -12 -16 -4 -16 C 0 -16 0 -12 0 -10 C 0 -12 0 -16 4 -16 C 12 -16 12 -4 0 8 Z" fill="#e56aa0" className="deco-pop" />}
        </g>
        <g transform="translate(134 86)">
          {!hearts && (
            <g ref={svg.eyeR}>
              <ellipse cx="0" cy="0" rx="17" ry="20" fill="#e8eef7" />
              <circle ref={svg.pupilR} cx="0" cy="0" r="7" fill="#1b1f27" />
            </g>
          )}
          {hearts && <path d="M0 8 C -12 -4 -12 -16 -4 -16 C 0 -16 0 -12 0 -10 C 0 -12 0 -16 4 -16 C 12 -16 12 -4 0 8 Z" fill="#e56aa0" className="deco-pop" />}
        </g>
        {/* Bouche */}
        <path ref={svg.mouthLine} stroke="#e8eef7" strokeWidth="5" strokeLinecap="round" fill="none" />
        <ellipse ref={svg.mouthOpen} cx="100" cy="148" fill="#0d1015" stroke="#e8eef7" strokeWidth="3" opacity="0" />
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
      </svg>
    </div>
  )
}
