import { useEffect, useState } from 'react'
import { api } from '../api'

// Réglages globaux : connexion au serveur LLM OpenAI-compatible (Strata / Ollama).
export default function HubSettings({ onClose, onSaved }) {
  const [form, setForm] = useState({ llm_base_url: '', llm_model: '', llm_api_key: '' })
  const [models, setModels] = useState([])
  const [keySet, setKeySet] = useState(false)
  const [keyMasked, setKeyMasked] = useState('')
  const [reachable, setReachable] = useState(null)
  const [status, setStatus] = useState('')

  useEffect(() => {
    api.hubSettings().then((s) => {
      setForm({ ...form, llm_base_url: s.llm_base_url, llm_model: s.llm_model, llm_api_key: '' })
      setKeySet(!!s.llm_api_key_set)
      setKeyMasked(s.llm_api_key_masked || '')
    }).catch(() => {})
    api.health().then((h) => { setReachable(h.llm_reachable); setModels(h.llm_models || []) }).catch(() => setReachable(false))
  }, [])

  const test = () => {
    setStatus('Test en cours…')
    api.saveHubSettings(form).then(() => api.health()).then((h) => {
      setReachable(h.llm_reachable)
      setModels(h.llm_models || [])
      setStatus(h.llm_reachable ? `Serveur joignable (${(h.llm_models || []).length} modèle(s))` : 'Serveur injoignable')
      onSaved?.()
    }).catch((e) => setStatus('Erreur : ' + e.message))
  }

  const save = () => {
    api.saveHubSettings(form).then(() => { setStatus('Enregistré ✓'); onSaved?.() })
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
            placeholder="http://192.168.1.10:8080/v1 (Strata) ou http://127.0.0.1:11434/v1 (Ollama)"
            onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
          />
          <div className="hint">
            Strata côté Windows : <code>strata launch --access lan</code> — accepte n'importe quel nom de modèle.
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
