import { useEffect, useState } from 'react'
import { api } from '../api'
import PersonaEditor from './PersonaEditor'

// Réglages d'un bot : identité, humeur par défaut, heartbeat, maintenance, danger + éditeur persona.
export default function BotSettings({ bot, catalog = [], onClose, onChanged, onBootstrap }) {
  const [tab, setTab] = useState('reglages')
  const [settings, setSettings] = useState(null)
  const [name, setName] = useState(bot.display_name)
  const [status, setStatus] = useState('')
  const [personaRefresh, setPersonaRefresh] = useState(0)

  useEffect(() => {
    api.settings(bot.device_id).then(setSettings).catch(() => {})
  }, [bot.device_id])

  const patch = (p) => {
    api.saveSettings(bot.device_id, p).then((s) => { setSettings(s); onChanged?.() }).catch((e) => setStatus(e.message))
  }

  const rename = () => {
    if (!name.trim() || name === bot.display_name) return
    api.renameBot(bot.device_id, name.trim())
      .then(() => { onChanged?.(); setStatus('Renommé ✓') })
      .catch((e) => setStatus(e.message))
  }

  const runHeartbeat = () => {
    setStatus('Passe de heartbeat en cours…')
    api.runHeartbeat(bot.device_id)
      .then((r) => { setStatus(r.memory_updated ? 'MEMORY.md mis à jour ✓' : 'Rien à changer dans MEMORY'); setPersonaRefresh((x) => x + 1) })
      .catch((e) => setStatus('Erreur : ' + e.message))
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{bot.display_name} — réglages</h2>
          <button className="ghost" onClick={onClose}>✕</button>
        </div>

        <div className="settings-tabs">
          <button className={`tab ${tab === 'reglages' ? 'active' : ''}`} onClick={() => setTab('reglages')}>Réglages</button>
          <button className={`tab ${tab === 'persona' ? 'active' : ''}`} onClick={() => setTab('persona')}>Persona</button>
        </div>

        {tab === 'reglages' && settings && (
          <div className="settings-body">
            <div className="field">
              <label>Nom affiché</label>
              <div className="row">
                <input value={name} onChange={(e) => setName(e.target.value)} />
                <button className="ghost" onClick={rename}>Renommer</button>
              </div>
            </div>

            <div className="field">
              <label>Modèle (vide = modèle du hub)</label>
              <input
                value={settings.model || ''}
                placeholder="(modèle global)"
                onChange={(e) => setSettings({ ...settings, model: e.target.value })}
                onBlur={() => patch({ model: settings.model })}
              />
            </div>

            <div className="field">
              <label>Humeur par défaut du visage</label>
              <div className="row">
                <select
                  value={settings.default_face || 'idle'}
                  onChange={(e) => patch({ default_face: e.target.value })}
                >
                  <option value="idle">Repos</option>
                  {catalog.filter((a) => a.name !== 'idle' && a.name !== 'speaking').map((a) => (
                    <option key={a.name} value={a.name}>{a.label_fr}</option>
                  ))}
                </select>
              </div>
              <div className="hint">Expression vers laquelle le visage de ce bot revient après chaque émotion passagère (et entre les tours de conversation).</div>
            </div>

            <div className="field">
              <label className="check">
                <input
                  type="checkbox"
                  checked={!!settings.heartbeat_enabled}
                  onChange={(e) => patch({ heartbeat_enabled: e.target.checked })}
                />
                Heartbeat (fusion des journaux dans MEMORY.md)
              </label>
            </div>

            <div className="field">
              <label>Intervalle heartbeat (minutes)</label>
              <div className="row">
                <input
                  type="number" min="5" max="720"
                  value={settings.heartbeat_interval_minutes}
                  onChange={(e) => setSettings({ ...settings, heartbeat_interval_minutes: Number(e.target.value) })}
                  onBlur={() => patch({ heartbeat_interval_minutes: settings.heartbeat_interval_minutes })}
                />
                <button className="ghost" onClick={runHeartbeat}>Lancer maintenant</button>
              </div>
            </div>

            <hr />

            <div className="field">
              <label>Donne-moi une âme</label>
              <div className="hint">Réinitialise les fichiers persona, efface journaux et historique, puis lance le rituel de naissance (BOOTSTRAP).</div>
              <button
                className="primary"
                onClick={() => { if (window.confirm('Réinitialiser la persona et lancer le rituel ?')) { onBootstrap(); onClose() } }}
              >
                ✨ Lancer le rituel
              </button>
            </div>

            <div className="field">
              <label>Zone dangereuse</label>
              <div className="row danger">
                <button
                  className="ghost"
                  onClick={() => { if (window.confirm('Écraser les fichiers persona par les modèles par défaut ?')) api.resetPersona(bot.device_id).then(() => { setStatus('Persona réinitialisée ✓'); setPersonaRefresh((x) => x + 1) }) }}
                >
                  Persona → défauts
                </button>
                <button
                  className="danger-btn"
                  onClick={() => { if (window.confirm(`Supprimer définitivement ${bot.display_name} (persona, historique, réglages) ?`)) { api.deleteBot(bot.device_id).then(() => { onChanged?.(); onClose() }) } }}
                >
                  Supprimer le bot
                </button>
              </div>
            </div>

            {status && <div className="status">{status}</div>}
          </div>
        )}

        {tab === 'persona' && <PersonaEditor botId={bot.device_id} refreshSignal={personaRefresh} />}
      </div>
    </div>
  )
}
