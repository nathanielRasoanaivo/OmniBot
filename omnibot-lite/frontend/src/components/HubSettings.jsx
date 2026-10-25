import { useEffect, useState } from 'react'
import { api } from '../api'

// Réglages globaux : connexion au serveur LLM OpenAI-compatible (Strata / Ollama)
// + profils de serveurs enregistrés pour basculer d'un moteur à l'autre sans .env.
export default function HubSettings({ onClose, onSaved }) {
  const [form, setForm] = useState({ llm_base_url: '', llm_model: '', llm_api_key: '' })
  const [models, setModels] = useState([])
  const [keySet, setKeySet] = useState(false)
  const [keyMasked, setKeyMasked] = useState('')
  const [reachable, setReachable] = useState(null)
  const [status, setStatus] = useState('')
  const [servers, setServers] = useState([])
  const [newName, setNewName] = useState('')

  const applySettings = (s) => {
    setForm({ ...form, llm_base_url: s.llm_base_url, llm_model: s.llm_model, llm_api_key: '' })
    setKeySet(!!s.llm_api_key_set)
    setKeyMasked(s.llm_api_key_masked || '')
    setServers(s.llm_servers || [])
  }

  useEffect(() => {
    api.hubSettings().then(applySettings).catch(() => {})
    api.health().then((h) => { setReachable(h.llm_reachable); setModels(h.llm_models || []) }).catch(() => setReachable(false))
  }, [])

  const test = () => {
    setStatus('Test en cours…')
    api.saveHubSettings(form).then(() => api.health()).then((h) => {
      setReachable(h.llm_reachable)
      setModels(h.llm_models || [])
      setStatus(h.llm_reachable ? `Serveur joignable (${(h.llm_models || []).length} modèle(s))` : 'Serveur injoignable')
      api.hubSettings().then((s) => setServers(s.llm_servers || []))
      onSaved?.()
    }).catch((e) => setStatus('Erreur : ' + e.message))
  }

  const save = () => {
    api.saveHubSettings(form).then(() => { setStatus('Enregistré ✓'); onSaved?.() })
      .catch((e) => setStatus('Erreur : ' + e.message))
  }

  const addServer = () => {
    if (!form.llm_base_url.trim()) { setStatus('URL du serveur actuelle vide — rien à enregistrer'); return }
    api.saveHubServer({
      name: newName.trim() || form.llm_base_url.trim(),
      base_url: form.llm_base_url,
      model: form.llm_model,
      api_key: form.llm_api_key,
    }).then((s) => {
      setServers(s.llm_servers || [])
      setNewName('')
      setForm({ ...form, llm_api_key: '' })
      setStatus('Profil serveur enregistré ✓')
    }).catch((e) => setStatus('Erreur : ' + e.message))
  }

  const activate = (id) => {
    api.activateHubServer(id).then((s) => {
      applySettings(s)
      setStatus('Serveur activé ✓')
      return api.health().then((h) => { setReachable(h.llm_reachable); setModels(h.llm_models || []) })
    }).catch((e) => setStatus('Erreur : ' + e.message))
    onSaved?.()
  }

  const del = (id) => {
    api.deleteHubServer(id).then((s) => setServers(s.llm_servers || []))
      .catch((e) => setStatus('Erreur : ' + e.message))
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Règlages du hub</h2>
          <button className="ghost" onClick={onClose}>✕</button>
        </div>

        <div className="field">
          <label>URL du serveur LLM (OpenAI-compatible)</label>
          <input
            value={form.llm_base_url}
            placeholder="http://192.168.1.31:8081/v1 (llama.cpp) ou http://127.0.0.1:11434/v1 (Ollama)"
            onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
          />
          <div className="hint">
            llama.cpp / Strata côté Windows : accès LAN, accepte n'importe quel nom de modèle.
            Ollama : <code>OLLAMA_HOST=0.0.0.0</code>.
          </div>
        </div>

        <div className="field">
          <label>Modèle</label>
          <input
            list="llm-models"
            value={form.llm_model}
            placeholder="default"
            onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
          />
          <datalist id="llm-models">
            {models.map((m) => <option key={m} value={m} />)}
          </datalist>
        </div>

        <div className="field">
          <label>Clé API</label>
          <input
            type="password"
            value={form.llm_api_key}
            placeholder={keySet ? `Déjà configurée (${keyMasked}) — laisser vide pour garder` : 'optionnelle'}
            onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })}
          />
        </div>

        <hr className="modal-sep" />

        <div className="field">
          <label>Serveurs enregistrés</label>
          <div className="hint">
            Profils réutilisables (URL + modèle + clé). « Utiliser » bascule le hub dessus instantanément —
            pas besoin de retoucher le <code>.env</code> (qui ne sert plus que de valeur par défaut au premier démarrage).
          </div>
          <div className="server-list">
            {servers.map((s) => (
              <div key={s.id} className={`server-row ${s.active ? 'active' : ''}`}>
                <span className={`llm-dot ${s.active ? 'ok' : ''}`} />
                <div className="server-info">
                  <div className="server-name">{s.name}</div>
                  <div className="server-url">{s.base_url} · {s.model || 'modèle par défaut'}{s.api_key_set ? ' · clé ••••' : ''}</div>
                </div>
                <button className="ghost" onClick={() => activate(s.id)} disabled={s.active}>
                  {s.active ? 'Actif' : 'Utiliser'}
                </button>
                <button className="danger-btn" onClick={() => del(s.id)}>Suppr.</button>
              </div>
            ))}
            {!servers.length && <div className="hint">Aucun profil enregistré — remplissez les champs ci-dessus puis « Enregistrer le serveur actuel ».</div>}
          </div>
          <div className="server-add">
            <input
              value={newName}
              placeholder="Nom du profil (ex. Bolt, Qwen, Ollama)"
              onChange={(e) => setNewName(e.target.value)}
            />
            <button className="ghost" onClick={addServer}>＋ Enregistrer le serveur actuel</button>
          </div>
        </div>

        <div className="modal-foot">
          <span className={`status ${reachable === false ? 'err' : reachable ? 'ok' : ''}`}>
            {reachable === null ? '…' : reachable ? '● serveur LLM joignable' : '○ serveur LLM injoignable'}
          </span>
          <span className="status">{status}</span>
          <button className="ghost" onClick={test}>Tester</button>
          <button className="primary" onClick={save}>Enregistrer</button>
        </div>
      </div>
    </div>
  )
}
