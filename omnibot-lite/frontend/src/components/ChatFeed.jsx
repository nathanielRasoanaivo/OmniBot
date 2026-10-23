import { useEffect, useRef, useState } from 'react'

// Flux d'intelligence : historique + tour en cours (deltas streaming, outils joués).
export default function ChatFeed({ bot, messages, liveTurn, error, processing, onSend, onReset }) {
  const [draft, setDraft] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, liveTurn, error])

  const send = () => {
    const text = draft.trim()
    if (!text || processing) return
    setDraft('')
    onSend(text)
  }

  if (!bot) return <div className="chat-feed empty">Sélectionne un bot dans la barre latérale.</div>

  return (
    <div className="chat-feed">
      <div className="feed-scroll" ref={scrollRef}>
        {messages.length === 0 && !liveTurn && (
          <div className="feed-hint">
            Écris lui un message — ou lance <b>Donne-moi une âme</b> dans les réglages du bot
            pour le rituel de naissance.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.role === 'user' ? <span className="who">Toi</span> : <span className="who">{bot.display_name}</span>}
            <div className="body">{m.content}</div>
          </div>
        ))}
        {liveTurn && (
          <div className="msg assistant live">
            <span className="who">{bot.display_name}</span>
            {liveTurn.tools.length > 0 && (
              <div className="tool-chips">
                {liveTurn.tools.map((t, i) => (
                  <span key={i} className="tool-chip">⚙ {t.name}{t.summary ? ` · ${t.summary}` : ''}</span>
                ))}
              </div>
            )}
            {liveTurn.text && <div className="body">{liveTurn.text}</div>}
            {!liveTurn.text && liveTurn.tools.length === 0 && <div className="body dim">…</div>}
          </div>
        )}
        {error && <div className="feed-error">⚠ {error}</div>}
      </div>
      <div className="feed-input">
        <textarea
          value={draft}
          placeholder={processing ? 'Le bot réfléchit…' : 'Écris un message à ' + bot.display_name + '…'}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          rows={2}
          disabled={processing}
        />
        <div className="feed-input-actions">
          <button className="ghost" onClick={onReset} title="Effacer l'historique de conversation">Historique ⌫</button>
          <button className="primary" onClick={send} disabled={processing || !draft.trim()}>Envoyer</button>
        </div>
      </div>
    </div>
  )
}
