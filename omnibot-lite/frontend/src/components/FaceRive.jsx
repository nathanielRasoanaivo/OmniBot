import { useEffect, useRef, useState } from 'react'
import { useRive } from '@rive-app/react-canvas'
import FacePreview from './FacePreview'

// Personnage Rive : norabot.riv (assistant "Nora"). Contrairement au panda, ce
// fichier est piloté par son state machine + data binding (View Model) : on
// change la valeur de l'enum "States" et le SM fait les transitions lui-même.
const SM_NAME = 'State Machine 1'

// Mapping des 11 états du backend vers les valeurs de l'enum "States"
// (valeurs autorisées : Thinking, Excited, Idle, Happy, Sad, Surprised).
const STATE = {
  idle: 'Idle',
  thinking: 'Thinking',
  confused: 'Thinking',
  happy: 'Happy',
  love: 'Happy',
  excited: 'Excited',
  sad: 'Sad',
  mad: 'Sad',
  surprised: 'Surprised',
  sleepy: 'Idle',
  speaking: 'Idle', // la bouche est animée par le visème "TTS" pendant la parole
}

// "TTS" est un index de visème (0 = silence, 1..21 = phonèmes) : pendant la
// parole on le fait tourner pour le lip-sync.
const VISEME_COUNT = 21
const VISEME_INTERVAL_MS = 110

// Rendu Rive du visage ; retombe sur le SVG paramétrique si le .riv ne charge pas.
export default function FaceRive({ anim }) {
  const [failed, setFailed] = useState(false)
  const nameRef = useRef(anim?.name || 'idle')
  nameRef.current = anim?.name || 'idle'

  const { rive, RiveComponent } = useRive({
    src: '/norabot.riv',
    stateMachine: SM_NAME,
    autoplay: true,
    autoBind: true,
    onLoadError: () => setFailed(true),
  })

  // État backend -> valeur de l'enum liée (le SM assure la transition).
  useEffect(() => {
    if (!rive) return
    // Le fichier sert aussi de démo : on coupe le fond de chambre embarqué.
    const env = rive.viewModelInstance?.enum?.('Enviroment')
    if (env) env.value = 'None'
    const states = rive.viewModelInstance?.enum?.('States')
    if (states) states.value = STATE[nameRef.current] ?? 'Idle'
  }, [rive, anim?.name])

  // Parole -> cycle de visèmes aléatoires sur "TTS", remis à zéro sinon.
  useEffect(() => {
    if (!rive) return
    const tts = rive.viewModelInstance?.number?.('TTS')
    if (!tts) return
    if (nameRef.current !== 'speaking') {
      tts.value = 0
      return
    }
    const id = setInterval(() => {
      tts.value = 1 + Math.floor(Math.random() * VISEME_COUNT)
    }, VISEME_INTERVAL_MS)
    return () => {
      clearInterval(id)
      tts.value = 0
    }
  }, [rive, anim?.name])

  if (failed) return <FacePreview anim={anim} />

  return (
    <div className={`face-preview rive ${anim?.name || 'idle'}`} style={{ '--accent': anim?.color || '#8aa2c8' }}>
      <RiveComponent />
    </div>
  )
}
