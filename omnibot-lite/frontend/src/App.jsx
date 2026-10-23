import { useCallback, useEffect, useRef, useState } from 'react'
import { api, connectMonitor } from './api'
import Sidebar from './components/Sidebar'
import ChatFeed from './components/ChatFeed'
import FacePreview from './components/FacePreview'
import HubSettings from './components/HubSettings'
import BotSettings from './components/BotSettings'

export default function App() {
  const [bots, setBots] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [messages, setMessages] = useState([])
  const [liveTurns, setLiveTurns] = useState({})
  const [errors, setErrors] = useState({})
  const [processing, setProcessing] = useState(new Set())
  const [catalog, setCatalog] = useState([])
  const [faces, setFaces] = useState({})
  const [showHub, setShowHub] = useState(false)
  const [showBot, setShowBot] = useState(false)
  const [drawer, setDrawer] = useState(false)
  const [hubOk, setHubOk] = useState(null)
  const faceTimers = useRef({})
  const selectedRef = useRef(null)
  selectedRef.current = selectedId

  const selectedBot = bots.find((b) => b.device_id === selectedId) || null

  const setFace = useCallback((did, name, durationMs) => {
    clearTimeout(faceTimers.current[did])
    setFaces((f) => ({ ...f, [did]: name }))
    if (durationMs) {
      faceTimers.current[did] = setTimeout(() => setFaces((f) => ({ ...f, [did]: 'idle' })), durationMs)
    }
  }, [])

  const refreshBots = useCallback(() => {
    return api.bots().then((r) => {
      setBots(r.bots)
      setSelectedId((sel) => (sel && r.bots.some((b) => b.device_id === sel) ? sel : r.bots[0]?.device_id || null))
    }).catch(() => {})
  }, [])

  const loadHistory = useCallback((did) => {
    return api.history(did).then((h) => {
      setMessages(h.messages)
      setProcessing((p) => { const n = new Set(p); if (h.processing) n.add(did); else n.delete(did); return n })
    }).catch(() => setMessages([]))
  }, [])

  useEffect(() => {
    api.animations().then((r) => setCatalog(r.animations)).catch(() => {})
    refreshBots()
    const ping = () => api.health().then((h) => setHubOk(h.llm_reachable)).catch(() => setHubOk(false))
    ping()
    const t = setInterval(ping, 15000)
    return () => clearInterval(t)
  }, [refreshBots])

  useEffect(() => {
    if (selectedId) { setMessages([]); setLiveTurns({}); loadHistory(selectedId) }
  }, [selectedId, loadHistory])

  useEffect(() => {
    const off = connectMonitor((ev) => {
      const did = ev.device_id
      switch (ev.type) {
        case 'processing_started':
          setProcessing((p) => new Set(p).add(did))
          setErrors((e) => ({ ...e, [did]: '' }))
          setLiveTurns((t) => ({ ...t, [did]: { turnId: ev.turn_id, text: '', tools: [] } }))
          setFace(did, 'thinking', 0)
          break
        case 'chat_delta':
          setLiveTurns((t) => {
            const cur = t[did] || { text: '', tools: [] }
            return { ...t, [did]: { ...cur, text: cur.text + ev.text } }
          })
          setFaces((f) => (f[did] === 'thinking' ? { ...f, [did]: 'speaking' } : f))
          break
        case 'tool_call':
          setLiveTurns((t) => {
            const cur = t[did] || { text: '', tools: [] }
            return { ...t, [did]: { ...cur, tools: [...cur.tools, { name: ev.name, summary: ev.summary }] } }
          })
          break
        case 'face_animation':
          setFace(did, ev.animation, ev.duration_ms)
          break
        case 'chat_done':
          setLiveTurns(({ [did]: _drop, ...rest }) => rest)
          setProcessing((p) => { const n = new Set(p); n.delete(did); return n })
          setFace(did, 'idle', 0)
          if (did === selectedRef.current) loadHistory(did)
          break
        case 'chat_error':
          setErrors((e) => ({ ...e, [did]: ev.error }))
          setLiveTurns(({ [did]: _drop, ...rest }) => rest)
          setProcessing((p) => { const n = new Set(p); n.delete(did); return n })
          setFace(did, 'idle', 0)
          break
        case 'bots_changed':
          refreshBots()
          break
        case 'heartbeat_done':
          if (did === selectedRef.current) {
            setMessages((m) => [...m, { role: 'system', content: `♥ Heartbeat — ${ev.memory_updated ? 'MEMORY.md mis à jour' : 'rien à changer'}` }])
          }
          break
        case 'persona_file_changed':
          if (did === selectedRef.current && showBotRef.current) loadHistory(did)
          break
        default:
          break
      }
    })
    return off
  }, [setFace, refreshBots, loadHistory])

  const showBotRef = useRef(false)
  showBotRef.current = showBot

  const send = (text) => {
    if (!selectedId) return
    setMessages((m) => [...m, { role: 'user', content: text }])
    setErrors((e) => ({ ...e, [selectedId]: '' }))
    api.chat(selectedId, text).catch((err) => {
      setErrors((e) => ({ ...e, [selectedId]: err.message }))
      setMessages((m) => m.filter((x) => !(x.role === 'user' && x.content === text)))
    })
  }

  const resetChat = () => {
    if (!selectedId || !window.confirm('Effacer la conversation ? (les fichiers persona sont conservés)')) return
    api.resetChat(selectedId).then(() => loadHistory(selectedId))
  }

  const createBot = (name) => {
    api.createBot(name).then((b) => { refreshBots().then(() => setSelectedId(b.device_id)) })
  }

  const bootstrap = () => {
    if (!selectedId) return
    setMessages([])
    api.bootstrap(selectedId).catch((e) => setErrors((x) => ({ ...x, [selectedId]: e.message })))
  }

  const animMap = Object.fromEntries(catalog.map((a) => [a.name, a]))
  const currentFace = animMap[faces[selectedId] || 'idle'] || animMap.idle || { name: 'idle', label_fr: 'Repos', face: {}, deco: [], color: '#8aa2c8' }

  return (
    <div className={`app${drawer ? ' drawer-open' : ''}`} style={{ '--accent': currentFace.color }}>
      <Sidebar
        bots={bots}
        selectedId={selectedId}
        processingIds={processing}
        onSelect={(id) => { setSelectedId(id); setDrawer(false) }}
        onCreate={createBot}
        onOpenHubSettings={() => { setShowHub(true); setDrawer(false) }}
        hubOk={hubOk}
      />
      {drawer && <div className="scrim" onClick={() => setDrawer(false)} />}

      <main className="main">
        {selectedBot ? (
          <>
            <div className="topbar">
              <button className="menu-btn" onClick={() => setDrawer(true)} aria-label="Ouvrir la liste des bots">☰</button>
              <h1>{selectedBot.display_name}</h1>
              <span className={`llm-dot topbar-dot ${hubOk ? 'ok' : 'ko'}`} title={hubOk ? 'Serveur LLM joignable' : 'Serveur LLM injoignable — Règlages hub'} />
              <div className="topbar-actions">
                <button className="ghost" onClick={bootstrap} title="Rituel Give me a soul (réinitialise la persona)">✨<span className="btn-label"> Donne-moi une âme</span></button>
                <button className="ghost" onClick={() => setShowBot(true)} title="Réglages du bot">⚙<span className="btn-label"> Réglages</span></button>
              </div>
            </div>

            <div className="content">
              <ChatFeed
                bot={selectedBot}
                messages={messages}
                liveTurn={liveTurns[selectedId]}
                error={errors[selectedId]}
                processing={processing.has(selectedId)}
                onSend={send}
                onReset={resetChat}
              />

              <div className="face-panel">
                <FacePreview anim={currentFace} />
                <div className="face-label">
                  <b>{currentFace.label_fr}</b>
                  {currentFace.description_fr && <span>{currentFace.description_fr}</span>}
                </div>
                <div className="face-chips">
                  {catalog.filter((a) => a.name !== 'idle').map((a) => (
                    <button
                      key={a.name}
                      className="chip"
                      style={{ '--chip': a.color }}
                      title={a.description_fr}
                      onClick={() => api.faceAnimation(selectedId, a.name).catch(() => {})}
                    >
                      {a.label_fr}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="placeholder">
            <h1>omnibot-lite</h1>
            <p>Hub de bots virtuels à personnalité — propulsé par ton serveur LLM local (Strata ou Ollama).</p>
            <p>Crée un bot dans la barre latérale pour commencer.</p>
          </div>
        )}
      </main>

      {showHub && <HubSettings onClose={() => setShowHub(false)} onSaved={() => api.health().then((h) => setHubOk(h.llm_reachable)).catch(() => {})} />}
      {showBot && selectedBot && (
        <BotSettings
          bot={selectedBot}
          onClose={() => setShowBot(false)}
          onChanged={refreshBots}
          onBootstrap={bootstrap}
        />
      )}
    </div>
  )
}
