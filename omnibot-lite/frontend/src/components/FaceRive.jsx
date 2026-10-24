import { useEffect, useRef, useState } from 'react'
import { Layout, Rive as RiveRuntime, useRive } from '@rive-app/react-canvas'
import FacePreview from './FacePreview'

// API linéaire volontaire (la seule pilotable avec ce .riv) : on coupe le bruit
// des avertissements de dépréciation correspondants.
RiveRuntime.suppressDeprecationWarnings = ['default-state-machine', 'animation-names', 'loop-events']

// L'artboard du panda (933x749) contient des boutons de démo à droite (x > ~760) :
// on cadre sur une région carrée à gauche qui n'affiche que le personnage.
const PANDA_FRAME = new Layout({ fit: 'contain', minX: 0, minY: 49, maxX: 700, maxY: 749 })

// Personnage Rive (panda-emotion-animation.riv) : 10 animations linéaires nommées.
// Mapping des 11 états du backend vers les clips du panda. Les émotions sans
// équivalent direct prennent la clip au visage le plus proche (à affiner quand
// un .riv plus riche sera choisi).
const CLIP = {
  idle: 'IDLE',
  thinking: 'THINKING',
  speaking: 'LAUGHING', // bouche ouverte qui bouge : substitut de parole
  happy: 'HAPPY',
  excited: 'CELEBRATE',
  surprised: 'SHOCKED',
  sleepy: 'SLEEPY',
  mad: 'SUSPICIOUS',    // regard sombre et soupçonneux
  confused: 'SUSPICIOUS',
  love: 'HAPPY',
  sad: 'IDLE',          // pas de clip triste dans ce fichier
}
// États persistants : si le clip est authoré en one-shot, le filet de sécurité
// ci-dessous le rejoue pour que le visage continue de vivre.
const PERSISTENT = new Set(['idle', 'thinking', 'speaking'])

// Rendu Rive du visage ; retombe sur le SVG paramétrique si le .riv ne charge pas.
export default function FaceRive({ anim }) {
  const [failed, setFailed] = useState(false)
  const nameRef = useRef(anim?.name || 'idle')
  nameRef.current = anim?.name || 'idle'

  const { rive, RiveComponent } = useRive({
    src: '/panda.riv',
    autoplay: 'IDLE',
    layout: PANDA_FRAME,
    onLoadError: () => setFailed(true),
  })

  // Changement d'état backend -> lecture du clip correspondant. En mode linéaire
  // les clips se jouent en parallèle : il faut stopper l'ancien, sinon tout se
  // mélange et rien ne paraît changer.
  const clipRef = useRef('IDLE')
  useEffect(() => {
    if (!rive) return
    const clip = CLIP[nameRef.current] ?? 'IDLE'
    if (clipRef.current && clipRef.current !== clip) rive.stop(clipRef.current)
    clipRef.current = clip
    rive.play(clip, undefined, true)
  }, [rive, anim?.name])

  // Filet de sécurité : un clip one-shot qui s'arrête alors que l'état est
  // persistant (idle/thinking/speaking) est rejoué immédiatement.
  useEffect(() => {
    if (!rive) return
    const onLoop = (e) => {
      const cur = CLIP[nameRef.current] ?? 'IDLE'
      if (e?.animation === cur && e?.type === 'oneshot' && PERSISTENT.has(nameRef.current)) {
        rive.play(cur, undefined, true)
      }
    }
    rive.on('loop', onLoop)
    return () => rive.off('loop', onLoop)
  }, [rive])

  if (failed) return <FacePreview anim={anim} />

  return (
    <div className={`face-preview rive ${anim?.name || 'idle'}`} style={{ '--accent': anim?.color || '#8aa2c8' }}>
      <RiveComponent />
    </div>
  )
}
