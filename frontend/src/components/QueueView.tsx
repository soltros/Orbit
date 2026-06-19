import React from 'react';
import { useAudioPlayer } from '../context/AudioPlayerContext';
import type { QueueItem } from '../context/AudioPlayerContext';
import { Sparkles, Music } from 'lucide-react';

export const QueueView: React.FC = () => {
  const { upcomingQueue, playTrack, isLoading, recommendationMode, acousticStats } = useAudioPlayer();

  const nothingSynced = (acousticStats?.cached_tracks ?? 0) === 0;

  return (
    <div className="flex flex-col w-full max-w-md mx-auto mt-6 p-6 bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl shadow-2xl">
      <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
        <h3 className="text-md font-bold text-gray-200 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          Rolling AI Queue
        </h3>
        <span className="text-xs font-semibold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full">
          {upcomingQueue.length} upcoming
        </span>
      </div>

      <div className="flex flex-col gap-3 max-h-[300px] overflow-y-auto no-scrollbar pr-1">
        {upcomingQueue.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Music className="w-8 h-8 text-gray-600 mb-2 animate-bounce" />
            {nothingSynced ? (
              <>
                <p className="text-sm font-medium text-gray-500">No tracks synced yet.</p>
                <p className="text-[10px] text-gray-600 mt-1 max-w-[220px]">
                  Run <code className="text-indigo-400">flask sync-subsonic</code> inside the backend container to load your library.
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-medium text-gray-500">Generating initial playlist...</p>
                <p className="text-xs text-gray-600 mt-1">
                  {recommendationMode === 'local' ? 'Scoring tracks with the local acoustic engine.' : 'This takes a few seconds via OpenAI/Anthropic'}
                </p>
              </>
            )}
          </div>
        ) : (
          upcomingQueue.map((item: QueueItem, idx: number) => (
            <div
              key={item.id}
              onClick={() => !isLoading && playTrack(item)}
              className="group flex flex-col p-3 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] hover:border-indigo-500/20 cursor-pointer transition duration-200"
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3 truncate pr-4">
                  <span className="text-xs font-bold text-gray-600 group-hover:text-indigo-400">
                    {(idx + 1).toString().padStart(2, '0')}
                  </span>
                  <div className="truncate">
                    <h4 className="text-sm font-bold text-gray-200 truncate group-hover:text-white">
                      {item.track.title}
                    </h4>
                    <p className="text-xs font-medium text-gray-500 truncate group-hover:text-gray-400 mt-0.5">
                      {item.track.artist}
                    </p>
                  </div>
                </div>
                {item.track.bpm && (
                  <span className="text-[10px] font-bold text-indigo-400/80 bg-indigo-500/5 px-2 py-0.5 rounded-md border border-indigo-500/10 flex-shrink-0">
                    {item.track.bpm} BPM
                  </span>
                )}
              </div>
              
              {/* Why Queued LLM Sentence */}
              {item.why_queued && (
                <div className="mt-2 text-[11px] leading-relaxed text-indigo-300/70 border-l border-indigo-500/20 pl-2 italic">
                  {item.why_queued}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
