import React, { useState } from 'react';
import { useAudioPlayer } from '../context/AudioPlayerContext';
import { RefreshCw, Radio, User, Sliders, Cpu, BrainCircuit, Activity } from 'lucide-react';

export const DiscoveryHub: React.FC = () => {
  const { 
    userProfile, 
    regenerateProfile, 
    isLoading, 
    clearQueue, 
    refreshQueue,
    recommendationMode,
    llmAvailable,
    acousticStats,
    setRecommendationMode,
    refreshStats
  } = useAudioPlayer();
  
  const [isUpdating, setIsUpdating] = useState(false);

  const handleRegenerate = async () => {
    setIsUpdating(true);
    await regenerateProfile();
    setIsUpdating(false);
  };

  const handleResetQueue = async () => {
    if (window.confirm("Are you sure you want to reset and clear the current rolling queue?")) {
      await clearQueue();
      await refreshQueue();
    }
  };

  const profileText = userProfile?.llm_preferences?.generated_profile;
  
  // Calculate analysis progress percentage
  const total = acousticStats?.cached_tracks || 0;
  const analyzed = acousticStats?.analyzed_tracks || 0;
  const percent = total > 0 ? Math.round((analyzed / total) * 100) : 0;

  return (
    <div className="flex flex-col w-full max-w-md mx-auto mt-6 p-6 bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl shadow-2xl">
      <div className="flex items-center gap-2 mb-4 border-b border-white/5 pb-3 justify-between">
        <div className="flex items-center gap-2">
          <User className="w-5 h-5 text-indigo-400" />
          <h3 className="text-md font-bold text-gray-200 font-sans">DJ Intelligence Hub</h3>
        </div>
        
        {/* Refresh Stats button */}
        <button 
          onClick={() => refreshStats()} 
          title="Refresh library statistics"
          className="p-1 hover:bg-white/5 rounded text-gray-500 hover:text-gray-300 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Mode Selector Tabs — Only show if LLM is actually configured with an API key */}
      {llmAvailable && (
        <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-slate-950/60 border border-white/5 mb-4">
        <button
          onClick={() => setRecommendationMode('llm')}
          className={`flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition duration-200 cursor-pointer ${
            recommendationMode === 'llm'
              ? 'bg-gradient-to-r from-indigo-500/25 to-violet-500/25 border border-indigo-500/30 text-white shadow'
              : 'text-gray-500 hover:text-gray-300 border border-transparent'
          }`}
        >
          <BrainCircuit className="w-3.5 h-3.5" />
          AI Cloud DJ
        </button>
        <button
          onClick={() => setRecommendationMode('local')}
          className={`flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition duration-200 cursor-pointer ${
            recommendationMode === 'local'
              ? 'bg-gradient-to-r from-indigo-500/25 to-violet-500/25 border border-indigo-500/30 text-white shadow'
              : 'text-gray-500 hover:text-gray-300 border border-transparent'
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          Local Engine
        </button>
        </div>
      )}

      {/* Dynamic Content Panel */}
      {recommendationMode === 'llm' ? (
        /* LLM Mode Panel */
        <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 animate-pulse" />
              Music Taste Persona
            </span>
            
            <button
              onClick={handleRegenerate}
              disabled={isLoading || isUpdating}
              className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 px-2.5 py-1 rounded-lg border border-white/5 disabled:opacity-30 cursor-pointer transition duration-150"
            >
              <RefreshCw className={`w-3 h-3 ${isUpdating ? 'animate-spin' : ''}`} />
              Regenerate
            </button>
          </div>

          <div className="text-xs leading-relaxed text-gray-400 overflow-y-auto max-h-[160px] no-scrollbar pr-1">
            {profileText ? (
              <div className="prose prose-invert prose-xs">
                {profileText.split('\n').map((line, idx) => {
                  if (line.startsWith('#')) return null;
                  return <p key={idx} className="mb-2">{line}</p>;
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-6 text-center">
                <p className="text-gray-500 font-medium">No listening profile generated yet.</p>
                <p className="text-[10px] text-gray-600 mt-1 max-w-[200px]">
                  Listen to a few songs, like/skip tracks, and click Regenerate to train your local DJ.
                </p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Local Mode Panel */
        <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" />
              Acoustic Analysis
            </span>
            <span className="text-xs font-bold text-gray-300">
              {percent}% Analyzed
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-950/80 rounded-full h-1.5 overflow-hidden border border-white/5">
            <div 
              className="bg-indigo-500 h-1.5 rounded-full shadow-lg shadow-indigo-500/50 transition-all duration-500" 
              style={{ width: `${percent}%` }}
            ></div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-2 mt-1">
            <div className="p-2 rounded-xl bg-slate-950/40 border border-white/5 text-center">
              <div className="text-[10px] text-gray-500 font-semibold">Total</div>
              <div className="text-sm font-bold text-gray-200 mt-0.5">{total}</div>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/40 border border-white/5 text-center">
              <div className="text-[10px] text-indigo-400/80 font-semibold">Analyzed</div>
              <div className="text-sm font-bold text-indigo-400 mt-0.5">{analyzed}</div>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/40 border border-white/5 text-center">
              <div className="text-[10px] text-gray-500 font-semibold">Pending</div>
              <div className="text-sm font-bold text-gray-400 mt-0.5">
                {(acousticStats?.pending_tracks || 0)}
              </div>
            </div>
          </div>

          {(acousticStats?.failed_tracks !== undefined && acousticStats.failed_tracks > 0) && (
            <div className="text-[10px] font-semibold text-red-400 bg-red-500/5 border border-red-500/10 p-2 rounded-xl text-center">
              ⚠ {acousticStats.failed_tracks} files failed analysis. Check container logs.
            </div>
          )}

          <div className="text-[10px] leading-relaxed text-gray-500 italic mt-1 text-center">
            Local hybrid engine scores tracks combining vector cosine similarity, metadata tagging, ListenBrainz graphs, and history.
          </div>
        </div>
      )}

      {/* Admin / Utility actions */}
      <div className="mt-4 flex items-center gap-2 justify-between">
        <span className="text-[11px] text-gray-600 flex items-center gap-1">
          <Sliders className="w-3.5 h-3.5" />
          Manage Station
        </span>
        <button
          onClick={handleResetQueue}
          className="text-[10px] font-bold text-red-400/80 hover:text-red-300 bg-red-500/5 hover:bg-red-500/10 border border-red-500/10 px-2.5 py-1 rounded-lg cursor-pointer transition duration-200"
        >
          Reset Queue
        </button>
      </div>
    </div>
  );
};
