import React, { useState } from 'react';
import { Server, User, KeyRound, Radio, Bot, Sparkles, Loader2, ArrowRight, Music } from 'lucide-react';

interface SetupWizardProps {
  onComplete: () => void;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({ onComplete }) => {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [url, setUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'local' | 'llm'>('local');
  const [llmProvider, setLlmProvider] = useState<'openai' | 'anthropic'>('openai');
  const [apiKey, setApiKey] = useState('');
  const [lastFmKey, setLastFmKey] = useState('');
  const [lastFmSecret, setLastFmSecret] = useState('');

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    setStep(2);
  };

  const handleFinish = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    const payload: any = {
      SUBSONIC_URL: url,
      SUBSONIC_USER: username,
      SUBSONIC_PASS: password,
      RECOMMENDATION_MODE: mode,
      LLM_PROVIDER: llmProvider,
      LASTFM_API_KEY: lastFmKey,
      LASTFM_API_SECRET: lastFmSecret
    };

    if (mode === 'llm' && apiKey) {
      if (llmProvider === 'openai') payload.OPENAI_API_KEY = apiKey;
      else payload.ANTHROPIC_API_KEY = apiKey;
    }

    try {
      const res = await fetch('/api/setup/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      if (data.status === 'success') {
        onComplete();
      } else {
        setError(data.message || 'Setup failed.');
      }
    } catch (err) {
      setError('A network error occurred connecting to Orbit.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 py-12 sm:px-6 lg:px-8 bg-[#050508]">
      {/* Background visual decoration */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-900/20 rounded-full blur-[120px] pointer-events-none"></div>
      
      <div className="w-full max-w-lg space-y-8 p-10 bg-slate-900/60 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-2xl relative z-10">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-gradient-to-tr from-indigo-500 to-violet-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/30 mb-6 transform rotate-12">
            <Radio className="h-8 w-8 text-white -rotate-12" />
          </div>
          <h2 className="mt-2 text-3xl font-extrabold text-white tracking-tight">Welcome to Orbit</h2>
          <p className="mt-2 text-sm text-gray-400">
            Let's get your intelligent, self-hosted jukebox connected to your music.
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        {step === 1 && (
          <form className="mt-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500" onSubmit={handleNext}>
            <div className="space-y-4">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Connect to Navidrome / Subsonic</h3>
                <p className="text-sm text-gray-400">
                  This sets up the <strong>global admin service account</strong> for Orbit. 
                  Provide the URL and credentials of a Navidrome user that has full access to the music library. 
                  Regular users will log in using their own accounts later.
                </p>
              </div>
              
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Server className="h-5 w-5 text-gray-500" />
                </div>
                <input
                  type="url"
                  required
                  className="appearance-none rounded-xl relative block w-full px-3 py-3.5 pl-10 border border-white/10 bg-slate-950/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-200"
                  placeholder="Server URL (e.g., https://music.example.com)"
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-5 w-5 text-gray-500" />
                  </div>
                  <input
                    type="text"
                    required
                    className="appearance-none rounded-xl relative block w-full px-3 py-3.5 pl-10 border border-white/10 bg-slate-950/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-200"
                    placeholder="Username"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                  />
                </div>
                
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <KeyRound className="h-5 w-5 text-gray-500" />
                  </div>
                  <input
                    type="password"
                    required
                    className="appearance-none rounded-xl relative block w-full px-3 py-3.5 pl-10 border border-white/10 bg-slate-950/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-200"
                    placeholder="Password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              className="group relative w-full flex justify-center py-3.5 px-4 border border-transparent text-sm font-bold rounded-xl text-white bg-white/10 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 focus:ring-offset-slate-900 transition duration-200"
            >
              Continue <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>
        )}

        {step === 2 && (
          <form className="mt-8 space-y-6 animate-in fade-in slide-in-from-right-8 duration-500" onSubmit={handleFinish}>
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <h3 className="text-lg font-medium text-white">Step 2: Choose Engine</h3>
                <button type="button" onClick={() => setStep(1)} className="text-xs text-indigo-400 hover:text-indigo-300">Back</button>
              </div>
              <p className="text-xs text-gray-400">Orbit can run entirely locally, or use an LLM for advanced context-aware playlists.</p>
              
              <div className="grid grid-cols-2 gap-4 pt-2">
                <div 
                  onClick={() => setMode('local')}
                  className={`cursor-pointer rounded-xl p-4 border ${mode === 'local' ? 'border-indigo-500 bg-indigo-500/10' : 'border-white/10 bg-slate-950/50 hover:bg-white/5'} transition-all`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Radio className={`w-5 h-5 ${mode === 'local' ? 'text-indigo-400' : 'text-gray-500'}`} />
                    <span className="font-semibold text-white">Local Only</span>
                  </div>
                  <p className="text-[10px] text-gray-400">Uses acoustic analysis and metadata. No API keys required.</p>
                </div>

                <div 
                  onClick={() => setMode('llm')}
                  className={`cursor-pointer rounded-xl p-4 border ${mode === 'llm' ? 'border-violet-500 bg-violet-500/10' : 'border-white/10 bg-slate-950/50 hover:bg-white/5'} transition-all`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className={`w-5 h-5 ${mode === 'llm' ? 'text-violet-400' : 'text-gray-500'}`} />
                    <span className="font-semibold text-white">Cloud DJ</span>
                  </div>
                  <p className="text-[10px] text-gray-400">Context-aware radio. Requires OpenAI or Anthropic API key.</p>
                </div>
              </div>

              {mode === 'llm' && (
                <div className="space-y-3 pt-4 animate-in fade-in duration-300">
                  <div className="flex gap-4 mb-2">
                    <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                      <input type="radio" name="provider" value="openai" checked={llmProvider === 'openai'} onChange={() => setLlmProvider('openai')} className="text-violet-500 focus:ring-violet-500 bg-slate-900 border-white/20" />
                      OpenAI
                    </label>
                    <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                      <input type="radio" name="provider" value="anthropic" checked={llmProvider === 'anthropic'} onChange={() => setLlmProvider('anthropic')} className="text-violet-500 focus:ring-violet-500 bg-slate-900 border-white/20" />
                      Anthropic
                    </label>
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <KeyRound className="h-5 w-5 text-gray-500" />
                    </div>
                    <input
                      type="password"
                      required={mode === 'llm'}
                      className="appearance-none rounded-xl relative block w-full px-3 py-3.5 pl-10 border border-white/10 bg-slate-950/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-500 sm:text-sm transition duration-200"
                      placeholder={`${llmProvider === 'openai' ? 'sk-...' : 'sk-ant-...'} API Key`}
                      value={apiKey}
                      onChange={e => setApiKey(e.target.value)}
                    />
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-px bg-white/10"></div>
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">Metadata Enrichment</span>
                  <div className="flex-1 h-px bg-white/10"></div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-gray-400">Last.fm API Key <span className="text-gray-600 font-normal">(Optional)</span></label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Music className="h-4 w-4 text-gray-500 group-focus-within:text-indigo-400 transition" />
                    </div>
                    <input
                      type="text"
                      className="block w-full pl-10 pr-3 py-3 border border-white/10 rounded-xl bg-slate-800/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-slate-800 focus:border-transparent transition"
                      placeholder="Enter your Last.fm API key..."
                      value={lastFmKey}
                      onChange={(e) => setLastFmKey(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-gray-400">Last.fm API Secret <span className="text-gray-600 font-normal">(Optional)</span></label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Music className="h-4 w-4 text-gray-500 group-focus-within:text-indigo-400 transition" />
                    </div>
                    <input
                      type="password"
                      className="block w-full pl-10 pr-3 py-3 border border-white/10 rounded-xl bg-slate-800/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-slate-800 focus:border-transparent transition"
                      placeholder="Enter your Last.fm Shared Secret..."
                      value={lastFmSecret}
                      onChange={(e) => setLastFmSecret(e.target.value)}
                    />
                  </div>
                  <p className="text-[10px] text-gray-500 mt-1">Used to pull high-res album art and rich artist biographies from Last.fm.</p>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative w-full flex justify-center py-3.5 px-4 border border-transparent text-sm font-bold rounded-xl text-white bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 focus:ring-offset-slate-900 shadow-lg shadow-indigo-500/25 disabled:opacity-50 transition duration-200"
            >
              {isSubmitting ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'Save & Launch Orbit'
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
