import { useEffect, useState } from 'react'
import { api } from '../api'

const FILES = [
  { key: 'agents', label: 'AGENTS' },
  { key: 'soul', label: 'SOUL' },
  { key: 'identity', label: 'IDENTITY' },
  { key: 'user', label: 'USER' },
  { key: 'tools', label: 'TOOLS' },
  { key: 'memory', label: 'MEMORY' },
  { key: 'heartbeat', label: 'HEARTBEAT' },
]

// Éditeur des fichiers persona du bot (markdown sur le hub).
export default function PersonaEditor({ botId, refreshSignal }) {
  const [file, setFile] = useState('soul')
  const [markdown, setMarkdown] = useState('')
  const [dirty, setDirty] = useState(false)
  const [status, setStatus] = useState('')

  const load = (f) => {
    api.personaFile(botId, f)
      .then((r) => { setMarkdown(r.markdown); setDirty(false); setStatus('') })
      .catch((e) => setStatus('Erreur : ' + e.message))
  }

  useEffect(() => { load(file) }, [file, botId])
  // Rafraîchit si le bot ou le hub modifie le fichier pendant l'édition (sauf si non sauvegardé)
  useEffect(() => { if (refreshSignal) load(file) }, [refreshSignal])

  const save = () => {
    api.putPersonaFile(botId, file, markdown)
      .then(() => { setDirty(false); setStatus('Enregistré ✓') })
      .catch((e) => setStatus('Erreur : ' + e.message))
  }

  return (
    <div className="persona-editor">
      <div className="persona-tabs">
        {FILES.map((f) => (
          <button
            key={f.key}
            className={file === f.key ? 'tab active' : 'tab'}
            onClick={() => { if (!dirty || window.confirm('Modifications non enregistrées, changer quand même ?')) setFile(f.key) }}
          >
            {f.label}
          </button>
        ))}
      </div>
      <textarea
        value={markdown}
        onChange={(e) => { setMarkdown(e.target.value); setDirty(true) }}
        spellCheck={false}
      />
      <div className="persona-foot">
        <span className={`status ${status.startsWith('Erreur') ? 'err' : ''}`}>{status}</span>
        <button className="primary" onClick={save} disabled={!dirty}>Enregistrer</button>
      </div>
    </div>
  )
}
