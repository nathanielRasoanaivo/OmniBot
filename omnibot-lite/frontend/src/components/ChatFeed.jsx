import { useEffect, useRef, useState } from 'react'

// Flux d'intelligence : historique + tour en cours (deltas streaming, outils joués).
export default function ChatFeed({ bot, messages, liveTurn, error, processing, onSend, onReset }) {
  const [draft, setDraft] = useState('')
  const scrollRef = useRef(null)
  const taRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, liveTurn, error])

  // Le textarea s'étire jusqu'à ~5 lignes puis scrolle.
  useEffect(() => {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }, [draft])

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
            Écris-lui un message — ou lance <b>✨ Donne-moi une âme</b> pour le rituel de naissance.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="body">{m.content}</div>
          </div>
        ))}
        {liveTurn && (
          <div className="msg assistant live">
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
          ref={taRef}
          value={draft}
          placeholder={processing ? 'Le bot réfléchit…' : `Écrire à ${bot.display_name}…`}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          rows={1}
          disabled={processing}
          enterKeyHint="send"
          aria-label="Message"
        />
        <div className="feed-input-actions">
          <button className="ghost" onClick={onReset} title="Effacer l'historique de conversation">Historique ⌫</button>
          <button className="primary" onClick={send} disabled={processing || !draft.trim()}>Envoyer</button>
        </div>
      </div>
    </div>
  )
}
