// Accès API + WebSocket monitor du hub omnibot-lite.

async function j(url, opts = {}) {
  const r = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts })
  if (!r.ok) {
    let detail = r.statusText
    try { detail = (await r.json()).detail || detail } catch { /* ignore */ }
    throw new Error(detail)
  }
  return r.json()
}

export const api = {
  health: () => j('/api/health'),
  bots: () => j('/api/bots'),
  createBot: (display_name) => j('/api/bots', { method: 'POST', body: JSON.stringify({ display_name }) }),
  deleteBot: (id) => j(`/api/bots/${id}`, { method: 'DELETE' }),
  renameBot: (id, display_name) => j(`/api/bots/${id}/rename`, { method: 'POST', body: JSON.stringify({ display_name }) }),
  settings: (id) => j(`/api/bots/${id}/settings`),
  saveSettings: (id, s) => j(`/api/bots/${id}/settings`, { method: 'POST', body: JSON.stringify(s) }),
  history: (id) => j(`/api/bots/${id}/history`),
  chat: (id, message) => j(`/api/bots/${id}/chat`, { method: 'POST', body: JSON.stringify({ message }) }),
  resetChat: (id) => j(`/api/bots/${id}/chat/reset`, { method: 'POST' }),
  bootstrap: (id) => j(`/api/bots/${id}/bootstrap`, { method: 'POST' }),
  resetPersona: (id) => j(`/api/bots/${id}/reset-persona`, { method: 'POST' }),
  runHeartbeat: (id) => j(`/api/bots/${id}/heartbeat/run`, { method: 'POST' }),
  personaFile: (id, file) => j(`/api/persona/${id}/${file}`),
  putPersonaFile: (id, file, markdown) => j(`/api/persona/${id}/${file}`, { method: 'PUT', body: JSON.stringify({ markdown }) }),
  animations: () => j('/api/animations'),
  faceAnimation: (id, animation, duration_ms) =>
    j(`/api/bots/${id}/face-animation`, { method: 'POST', body: JSON.stringify({ animation, duration_ms }) }),
  hubSettings: () => j('/api/hub/settings'),
  saveHubSettings: (s) => j('/api/hub/settings', { method: 'POST', body: JSON.stringify(s) }),
  saveHubServer: (s) => j('/api/hub/servers', { method: 'POST', body: JSON.stringify(s) }),
  deleteHubServer: (id) => j(`/api/hub/servers/${id}`, { method: 'DELETE' }),
  activateHubServer: (id) => j(`/api/hub/servers/${id}/activate`, { method: 'POST' }),
}

// WebSocket monitor avec reconnexion automatique. onEvent(ev) reçoit tous les événements.
export function connectMonitor(onEvent) {
  let ws = null
  let closed = false
  let retry = 500

  function open() {
    if (closed) return
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${proto}//${location.host}/ws/monitor`)
    ws.onopen = () => { retry = 500 }
    ws.onmessage = (m) => {
      try { onEvent(JSON.parse(m.data)) } catch { /* ignore */ }
    }
    ws.onclose = () => {
      if (!closed) {
        setTimeout(open, retry)
        retry = Math.min(retry * 2, 5000)
      }
    }
  }
  open()
  return () => { closed = true; ws?.close() }
}
