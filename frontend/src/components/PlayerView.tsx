import React from 'react';
import { useAudioPlayer } from '../context/AudioPlayerContext';
import { Play, Pause, SkipForward, Volume2, VolumeX, Heart, ThumbsDown, Users, Download } from 'lucide-react';

interface PlayerViewProps {
  onOpenBrowser: () => void;
}

export const PlayerView: React.FC<PlayerViewProps> = ({ onOpenBrowser }) => {
  const {
    currentTrack,
    isPlaying,
    progress,
    duration,
    volume,
    isMuted,
    isLoading,
    togglePlay,
    skipTrack,
    likeTrack,
    dislikeTrack,
    seek,
    setVolume,
    toggleMute,
    acousticStats,
    likedTracks,
  } = useAudioPlayer();

  const formatTime = (secs: number) => {
    if (isNaN(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    seek(Number(e.target.value));
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setVolume(Number(e.target.value));
  };

  const hasTrack = !!currentTrack;
  const hasSyncedTracks = (acousticStats?.cached_tracks ?? 0) > 0;

  return (
    <div className="flex flex-col items-center justify-between w-full max-w-md mx-auto p-6 bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl shadow-2xl">
      {/* Dynamic Animated Orbit Art */}
      <div className="relative w-64 h-64 flex items-center justify-center my-6">
        {/* Glowing backdrop */}
        <div className="absolute inset-0 bg-indigo-500/10 rounded-full blur-3xl animate-pulse-slow"></div>
        
        {/* Orbit ring 1 */}
        <div className={`absolute w-56 h-56 border border-indigo-500/20 rounded-full ${isPlaying ? 'animate-[spin_20s_linear_infinite]' : ''}`}>
          <div className="absolute top-4 left-1/2 w-4 h-4 -ml-2 bg-indigo-400 rounded-full shadow-lg shadow-indigo-500/50"></div>
        </div>
        
        {/* Orbit ring 2 */}
        <div className={`absolute w-44 h-44 border border-violet-500/15 rounded-full ${isPlaying ? 'animate-[spin_12s_linear_infinite_reverse]' : ''}`}>
          <div className="absolute bottom-2 left-8 w-3 h-3 bg-violet-400 rounded-full shadow-lg shadow-violet-500/50"></div>
        </div>
        
        {/* Orbit ring 3 */}
        <div className={`absolute w-32 h-32 border border-purple-500/10 rounded-full ${isPlaying ? 'animate-[spin_8s_linear_infinite]' : ''}`}>
          <div className="absolute top-1/2 right-1 w-2.5 h-2.5 bg-purple-400 rounded-full shadow-lg shadow-purple-500/50"></div>
        </div>

        {/* Center Vinyl/Planet */}
        <div className={`relative w-24 h-24 bg-gradient-to-tr from-slate-950 to-indigo-950 rounded-full flex items-center justify-center border-2 border-indigo-500/40 shadow-inner ${isPlaying ? 'animate-[spin_6s_linear_infinite]' : ''}`}>
          <div className="w-8 h-8 bg-slate-900 border-2 border-indigo-400/20 rounded-full flex items-center justify-center">
            <div className="w-2.5 h-2.5 bg-indigo-400 rounded-full"></div>
          </div>
        </div>
        
        {/* Spinning state ring */}
        {isLoading && (
          <div className="absolute w-28 h-28 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
        )}
      </div>

      {/* Metadata */}
      <div className="text-center w-full min-h-[5.5rem] flex flex-col justify-center px-4">
        {hasTrack ? (
          <>
            <h2 className="text-xl font-bold text-gray-100 truncate">{currentTrack.track.title}</h2>
            <p className="text-sm font-medium text-indigo-400 mt-1 truncate">{currentTrack.track.artist}</p>
            <div className="flex items-center justify-center gap-3 mt-1.5">
              <p className="text-xs text-gray-500 truncate max-w-[150px]">{currentTrack.track.album || 'No Album'}</p>
              <button
                onClick={onOpenBrowser}
                title="Abandon station and start a new one"
                className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-indigo-300 hover:text-white bg-indigo-500/10 hover:bg-indigo-500/30 border border-indigo-500/20 px-2 py-0.5 rounded-full transition duration-150"
              >
                <Users className="w-3 h-3" />
                New Station
              </button>
            </div>
          </>
        ) : hasSyncedTracks ? (
          /* Library is synced — show Browse Artists CTA */
          <>
            <h2 className="text-xl font-bold text-gray-200">Ready to Play</h2>
            <p className="text-sm text-gray-500 mt-1">{acousticStats!.cached_tracks} tracks in library</p>
            <button
              onClick={onOpenBrowser}
              disabled={isLoading}
              className="mt-3 mx-auto flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white text-sm font-bold rounded-full shadow-lg shadow-indigo-500/30 transition duration-200 disabled:opacity-50"
            >
              <Users className="w-4 h-4" />
              {isLoading ? 'Starting...' : 'Browse Artists'}
            </button>
          </>
        ) : (
          /* Nothing synced yet */
          <>
            <h2 className="text-xl font-bold text-gray-400">Station Offline</h2>
            <p className="text-sm text-gray-500 mt-1">Run <code className="text-indigo-400 text-xs">flask sync-subsonic</code> to load your library.</p>
          </>
        )}
      </div>

      {/* Progress Bar */}
      <div className="w-full mt-6 px-2">
        <input
          type="range"
          min="0"
          max={duration || 100}
          value={progress}
          onChange={handleProgressChange}
          disabled={!hasTrack}
          className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-indigo-500 hover:accent-indigo-400 focus:outline-none"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-2 font-medium">
          <span>{formatTime(progress)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Media Feedback & Core Controls */}
      <div className="flex items-center justify-between w-full mt-6 px-4">
        {/* Dislike */}
        <button
          onClick={() => hasTrack && dislikeTrack(currentTrack.track.id)}
          disabled={!hasTrack}
          className="p-3 text-gray-400 hover:text-red-400 disabled:opacity-30 transition duration-200"
          title="Dislike / Ban Song"
        >
          <ThumbsDown className="w-5 h-5" />
        </button>

        {/* Play/Pause */}
        <button
          onClick={togglePlay}
          disabled={!hasTrack}
          className="p-5 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white rounded-full shadow-lg shadow-indigo-500/20 transform active:scale-95 disabled:opacity-50 transition duration-200"
        >
          {isPlaying ? <Pause className="w-6 h-6 fill-white" /> : <Play className="w-6 h-6 fill-white" />}
        </button>

        {/* Like */}
        <button
          onClick={() => {
            if (!hasTrack) return;
            const isLiked = likedTracks.has(currentTrack.track.id);
            if (isLiked) dislikeTrack(currentTrack.track.id);
            else likeTrack(currentTrack.track.id);
          }}
          disabled={!hasTrack}
          className={`p-3 transition duration-200 disabled:opacity-30 ${
            hasTrack && likedTracks.has(currentTrack.track.id)
              ? 'text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.5)]'
              : 'text-gray-400 hover:text-emerald-400'
          }`}
          title="Like / Star Song"
        >
          <Heart className={`w-5 h-5 ${hasTrack && likedTracks.has(currentTrack.track.id) ? 'fill-emerald-400' : ''}`} />
        </button>

        {/* Skip */}
        <button
          onClick={skipTrack}
          disabled={!hasTrack}
          className="p-3 text-gray-400 hover:text-indigo-400 disabled:opacity-30 transition duration-200"
          title="Skip Song"
        >
          <SkipForward className="w-5 h-5" />
        </button>

        {/* Download */}
        <button
          onClick={() => {
            if (!hasTrack) return;
            const url = `/api/subsonic/stream/${currentTrack.track.id}`;
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentTrack.track.artist} - ${currentTrack.track.title}.flac`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
          }}
          disabled={!hasTrack}
          className="p-3 text-gray-400 hover:text-indigo-400 disabled:opacity-30 transition duration-200"
          title="Download Song"
        >
          <Download className="w-5 h-5" />
        </button>
      </div>

      {/* Volume Bar */}
      <div className="flex items-center w-full mt-6 px-4 text-gray-500">
        <button onClick={toggleMute} disabled={!hasTrack} className="hover:text-gray-300">
          {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
        </button>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={isMuted ? 0 : volume}
          onChange={handleVolumeChange}
          disabled={!hasTrack}
          className="w-full h-1 ml-3 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-indigo-500/50 hover:accent-indigo-400/80 focus:outline-none"
        />
      </div>
    </div>
  );
};
