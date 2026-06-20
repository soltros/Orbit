import React, { useState, useEffect, useRef } from 'react';
import { X, Server, KeyRound, Save, Loader2, Sparkles, HardDrive, Download, Upload, Shield, RefreshCw } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'general' | 'api' | 'data' | 'users'>('general');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [config, setConfig] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [usersList, setUsersList] = useState<any[]>([]);

  // Form states
  const [url, setUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [llmProvider, setLlmProvider] = useState<'openai' | 'anthropic'>('openai');
  const [apiKey, setApiKey] = useState('');
  const [lastFmKey, setLastFmKey] = useState('');
  const [lastFmSecret, setLastFmSecret] = useState('');
  const [mode, setMode] = useState<'local' | 'llm'>('local');

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      fetch('/api/setup/config')
        .then(res => res.json())
        .then(data => {
          setConfig(data);
          setUrl(data.SUBSONIC_URL || '');
          setUsername(data.SUBSONIC_USER || '');
          setMode(data.RECOMMENDATION_MODE || 'local');
          setLlmProvider(data.LLM_PROVIDER || 'openai');
          setIsLoading(false);
        })
        .catch(() => {
          setMessage({ type: 'error', text: 'Failed to load configuration.' });
          setIsLoading(false);
        });
        
      // Fetch users list
      fetch('/api/setup/users')
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            setUsersList(data.users);
          }
        })
        .catch(() => console.error('Failed to load users'));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);

    const payload: any = {
      SUBSONIC_URL: url,
      SUBSONIC_USER: username,
      RECOMMENDATION_MODE: mode,
      LLM_PROVIDER: llmProvider
    };

    if (password) payload.SUBSONIC_PASS = password;
    
    if (apiKey) {
      if (llmProvider === 'openai') payload.OPENAI_API_KEY = apiKey;
      else payload.ANTHROPIC_API_KEY = apiKey;
    }
    
    if (lastFmKey) {
      payload.LASTFM_API_KEY = lastFmKey;
    }
    if (lastFmSecret) {
      payload.LASTFM_API_SECRET = lastFmSecret;
    }

    try {
      const res = await fetch('/api/setup/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      if (data.status === 'success') {
        setMessage({ type: 'success', text: 'Settings saved successfully!' });
        setPassword('');
        setApiKey('');
        setLastFmKey('');
        setLastFmSecret('');
        // Update local config state
        setConfig({
          ...config,
          RECOMMENDATION_MODE: mode,
          LLM_PROVIDER: llmProvider,
          HAS_OPENAI_KEY: llmProvider === 'openai' && apiKey ? true : config.HAS_OPENAI_KEY,
          HAS_ANTHROPIC_KEY: llmProvider === 'anthropic' && apiKey ? true : config.HAS_ANTHROPIC_KEY,
          HAS_LASTFM_KEY: lastFmKey ? true : config.HAS_LASTFM_KEY,
          HAS_LASTFM_SECRET: lastFmSecret ? true : config.HAS_LASTFM_SECRET
        });
        
        // Reload page after a delay to apply backend config changes
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to save settings.' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Network error saving settings.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetFailedAnalysis = async () => {
    try {
      const res = await fetch('/api/library/reset-failed-analysis', { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setMessage({ type: 'success', text: data.message });
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to reset analysis.' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Network error resetting analysis.' });
    }
  };

  const handleExportDb = () => {
    window.location.href = '/api/setup/export-db';
  };

  const handleImportDb = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('db_file', file);

    setIsLoading(true);
    try {
      const res = await fetch('/api/setup/import-db', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setMessage({ type: 'success', text: data.message });
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to import database.' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Network error importing database.' });
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose}></div>
      <div className="relative w-full max-w-2xl bg-slate-900 border border-white/10 rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            Settings
          </h2>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="p-12 flex justify-center">
            <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          </div>
        ) : (
          <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
            {/* Sidebar */}
            <div className="w-full md:w-48 bg-slate-950/50 border-r border-white/5 p-4 flex flex-row md:flex-col gap-2 overflow-x-auto md:overflow-y-auto no-scrollbar">
              <button
                onClick={() => setActiveTab('general')}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-lg transition-colors whitespace-nowrap ${
                  activeTab === 'general' ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                }`}
              >
                <Server className="w-4 h-4" /> Server
              </button>
              <button
                onClick={() => setActiveTab('api')}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-lg transition-colors whitespace-nowrap ${
                  activeTab === 'api' ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                }`}
              >
                <KeyRound className="w-4 h-4" /> API Keys
              </button>
              <button
                onClick={() => setActiveTab('data')}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-lg transition-colors whitespace-nowrap ${
                  activeTab === 'data' ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                }`}
              >
                <HardDrive className="w-4 h-4" /> Backup & Data
              </button>
              <button
                onClick={() => setActiveTab('users')}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-lg transition-colors whitespace-nowrap ${
                  activeTab === 'users' ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                }`}
              >
                <Shield className="w-4 h-4" /> Users
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 p-6 overflow-y-auto">
              {message && (
                <div className={`mb-6 p-3 rounded-xl border text-sm font-medium ${
                  message.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
                }`}>
                  {message.text}
                </div>
              )}

              {activeTab === 'general' && (
                <div className="space-y-4 animate-in fade-in duration-300">
                  <h3 className="text-sm font-semibold text-gray-300 mb-4">Navidrome / Subsonic Connection</h3>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Server URL</label>
                    <input
                      type="url"
                      value={url}
                      onChange={e => setUrl(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Username</label>
                      <input
                        type="text"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Password (Leave blank to keep)</label>
                      <input
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>
                  <p className="text-[10px] text-red-400 mt-2">Warning: Changing the Server URL will wipe the local library cache.</p>
                </div>
              )}

              {activeTab === 'api' && (
                <div className="space-y-6 animate-in fade-in duration-300">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-violet-400" /> Recommendation Engine
                    </h3>
                    <div className="flex gap-4 mb-4">
                      <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                        <input type="radio" value="local" checked={mode === 'local'} onChange={() => setMode('local')} className="text-indigo-500 bg-slate-900 border-white/20" />
                        Local Engine
                      </label>
                      <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                        <input type="radio" value="llm" checked={mode === 'llm'} onChange={() => setMode('llm')} className="text-violet-500 bg-slate-900 border-white/20" />
                        Cloud DJ (LLM)
                      </label>
                    </div>

                    {mode === 'llm' && (
                      <div className="p-4 bg-white/5 border border-white/10 rounded-xl space-y-4">
                        <div className="flex gap-4">
                          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                            <input type="radio" value="openai" checked={llmProvider === 'openai'} onChange={() => setLlmProvider('openai')} className="text-violet-500 bg-slate-900 border-white/20" />
                            OpenAI
                          </label>
                          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                            <input type="radio" value="anthropic" checked={llmProvider === 'anthropic'} onChange={() => setLlmProvider('anthropic')} className="text-violet-500 bg-slate-900 border-white/20" />
                            Anthropic
                          </label>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">
                            {llmProvider === 'openai' ? 'OpenAI API Key' : 'Anthropic API Key'}
                            {((llmProvider === 'openai' && config?.HAS_OPENAI_KEY) || (llmProvider === 'anthropic' && config?.HAS_ANTHROPIC_KEY)) && ' (Saved)'}
                          </label>
                          <input
                            type="password"
                            value={apiKey}
                            onChange={e => setApiKey(e.target.value)}
                            placeholder={((llmProvider === 'openai' && config?.HAS_OPENAI_KEY) || (llmProvider === 'anthropic' && config?.HAS_ANTHROPIC_KEY)) ? "••••••••" : "sk-..."}
                            className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-violet-500"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="pt-4 border-t border-white/5">
                    <h3 className="text-sm font-semibold text-gray-300 mb-4">Metadata Integrations</h3>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">
                        Last.fm API Key {config?.HAS_LASTFM_KEY && '(Saved)'}
                      </label>
                      <input
                        type="password"
                        value={lastFmKey}
                        onChange={e => setLastFmKey(e.target.value)}
                        placeholder={config?.HAS_LASTFM_KEY ? "••••••••" : "Leave blank if unused"}
                        className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1 mt-4">
                        Last.fm API Secret {config?.HAS_LASTFM_SECRET && '(Saved)'}
                      </label>
                      <input
                        type="password"
                        value={lastFmSecret}
                        onChange={e => setLastFmSecret(e.target.value)}
                        placeholder={config?.HAS_LASTFM_SECRET ? "••••••••" : "Leave blank if unused"}
                        className="w-full px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'data' && (
                <div className="space-y-4 animate-in fade-in duration-300">
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">Backup & Data Management</h3>
                  <p className="text-xs text-gray-400 mb-6">Orbit stores acoustic features, cached lists, and your playback history in a local SQLite database.</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <button 
                      onClick={handleExportDb}
                      className="flex flex-col items-center justify-center gap-2 p-6 bg-white/5 border border-white/10 hover:border-indigo-500/50 hover:bg-indigo-500/10 rounded-xl transition"
                    >
                      <Download className="w-6 h-6 text-indigo-400" />
                      <span className="text-sm font-bold text-white">Export Database</span>
                      <span className="text-[10px] text-gray-400 text-center">Download orbit.db for safekeeping</span>
                    </button>
                    
                    <button 
                      onClick={() => fileInputRef.current?.click()}
                      className="flex flex-col items-center justify-center gap-2 p-6 bg-white/5 border border-white/10 hover:border-violet-500/50 hover:bg-violet-500/10 rounded-xl transition"
                    >
                      <Upload className="w-6 h-6 text-violet-400" />
                      <span className="text-sm font-bold text-white">Import Database</span>
                      <span className="text-[10px] text-gray-400 text-center">Restore from a previous backup</span>
                    </button>
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      className="hidden" 
                      accept=".db,.sqlite,.sqlite3" 
                      onChange={handleImportDb} 
                    />

                    <button 
                      onClick={handleResetFailedAnalysis}
                      className="flex flex-col items-center justify-center gap-2 p-6 bg-white/5 border border-white/10 hover:border-amber-500/50 hover:bg-amber-500/10 rounded-xl transition md:col-span-2"
                    >
                      <RefreshCw className="w-6 h-6 text-amber-400" />
                      <span className="text-sm font-bold text-white">Reset Failed Analysis Tracks</span>
                      <span className="text-[10px] text-gray-400 text-center">Re-queues tracks that previously failed acoustic analysis.</span>
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'users' && (
                <div className="space-y-4 animate-in fade-in duration-300">
                  <h3 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-emerald-400" /> User Management
                  </h3>
                  <p className="text-xs text-gray-400 mb-6">
                    Orbit uses the users from your Subsonic/Navidrome server. When they log in to Orbit, their profile appears here.
                  </p>
                  
                  {usersList.length === 0 ? (
                    <div className="text-center p-6 bg-white/5 rounded-xl border border-white/10">
                      <p className="text-sm text-gray-400">No users have logged into Orbit yet.</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {usersList.map(user => (
                        <div key={user.id} className="flex items-center justify-between p-4 bg-slate-950/50 border border-white/10 rounded-xl">
                          <div>
                            <div className="font-bold text-white text-sm">{user.username}</div>
                            <div className="text-[10px] text-gray-500">First Login: {new Date(user.created_at).toLocaleDateString()}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs font-bold text-indigo-400">{user.play_count} Tracks Played</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-white/5 bg-slate-950/30 rounded-b-2xl">
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-semibold text-gray-400 hover:text-white transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isLoading || isSaving}
              className="flex items-center gap-2 px-6 py-2 bg-indigo-500 hover:bg-indigo-400 text-white text-sm font-bold rounded-lg shadow-lg shadow-indigo-500/25 transition disabled:opacity-50"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Changes
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
