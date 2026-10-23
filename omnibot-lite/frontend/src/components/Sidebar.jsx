import { useState } from 'react'

export default function Sidebar({ bots, selectedId, processingIds, onSelect, onCreate, onOpenHubSettings, hubOk }) {
  const [name, setName] = useState('')
  const [adding, setAdding] = useState(false)

  const create = () => {
    const n = name.trim()
    if (!n) return
    onCreate(n)
    setName('')
    setAdding(false)
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <span className="logo">◉ omnibot-lite</span>
        <span className={`llm-dot ${hubOk ? 'ok' : 'ko'}`} title={hubOk ? 'Serveur LLM joignable' : 'Serveur LLM injoignable — Règlages hub'} />
      </div>

      <div className="bots-list">
        {bots.map((b) => {
          const proc = processingIds.has(b.device_id)
          return (
            <button
              key={b.device_id}
              className={`bot-card ${selectedId === b.device_id ? 'selected' : ''}`}
              onClick={() => onSelect(b.device_id)}
            >
              <span className={`status-dot ${proc ? 'processing' : 'online'}`} />
              <span className="bot-name">{b.display_name}</span>
              <span className="bot-state">{proc ? 'traitement…' : 'prêt'}</span>
            </button>
          )
        })}
        {bots.length === 0 && <div className="no-bots">Aucun bot. Ajoute ton premier compagnon.</div>}
      </div>

      {adding ? (
        <div className="add-bot">
          <input
            autoFocus
            value={name}
            placeholder="Nom du bot…"
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') create(); if (e.key === 'Escape') setAdding(false) }}
          />
          <div className="add-bot-actions">
            <button className="ghost" onClick={() => setAdding(false)}>Annuler</button>
            <button className="primary" onClick={create}>Créer</button>
          </div>
        </div>
      ) : (
        <button className="add-bot-btn" onClick={() => setAdding(true)}>+ Nouveau bot</button>
      )}

      <button className="hub-settings-btn" onClick={onOpenHubSettings}>⚙ Règlages du hub</button>
    </aside>
  )
}
