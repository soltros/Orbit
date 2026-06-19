import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

export interface Track {
  id: string;
  title: string;
  artist: string;
  album: string | null;
  duration: number;
  bpm: number | null;
  genres: string[];
  custom_tags: Record<string, any> | null;
}

export interface QueueItem {
  id: number;
  user_id: number;
  track: Track;
  why_queued: string;
  position: number;
  status: string;
}

export interface UserProfile {
  id: number;
  username: string;
  llm_preferences: {
    generated_profile?: string;
    [key: string]: any;
  };
}

interface AudioPlayerContextType {
  currentTrack: QueueItem | null;
  upcomingQueue: QueueItem[];
  isPlaying: boolean;
  progress: number; // in seconds
  duration: number; // in seconds
  volume: number; // 0 to 1
  isMuted: boolean;
  isLoading: boolean;
  userProfile: UserProfile | null;
  error: string | null;
  recommendationMode: 'llm' | 'local';
  acousticStats: {
    cached_tracks: number;
    analyzed_tracks: number;
    pending_tracks: number;
    failed_tracks: number;
  } | null;
  
  togglePlay: () => void;
  playTrack: (item: QueueItem) => Promise<void>;
  skipTrack: () => Promise<void>;
  likeTrack: (trackId: string) => Promise<void>;
  dislikeTrack: (trackId: string) => Promise<void>;
  seek: (time: number) => void;
  setVolume: (vol: number) => void;
  toggleMute: () => void;
  refreshQueue: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  regenerateProfile: () => Promise<void>;
  clearQueue: () => Promise<void>;
  setRecommendationMode: (mode: 'llm' | 'local') => Promise<void>;
  refreshStats: () => Promise<void>;
  startStation: () => Promise<void>;
}

const AudioPlayerContext = createContext<AudioPlayerContextType | undefined>(undefined);

export const AudioPlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentTrack, setCurrentTrack] = useState<QueueItem | null>(null);
  const [upcomingQueue, setUpcomingQueue] = useState<QueueItem[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, _setVolume] = useState<number>(() => {
    return Number(localStorage.getItem('orbit-volume') ?? '0.8');
  });
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recommendationMode, setRecommendationModeState] = useState<'llm' | 'local'>('llm');
  const [acousticStats, setAcousticStats] = useState<any | null>(null);
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const nextAudioRef = useRef<HTMLAudioElement | null>(null); // For pre-fetching
  const isGeneratingRef = useRef(false);
  const hasPrefetchedRef = useRef(false);

  // Initialize HTML5 Audio
  useEffect(() => {
    const audio = new Audio();
    audioRef.current = audio;
    audio.volume = volume;

    // Handle audio events
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onTimeUpdate = () => {
      setProgress(audio.currentTime);
      
      // Trigger pre-fetching at 80% mark of the song
      if (audio.duration && (audio.currentTime / audio.duration) >= 0.8) {
        triggerPrefetch();
      }
    };
    const onDurationChange = () => setDuration(audio.duration);
    const onEnded = () => {
      // Auto play next song
      handleSongEnded();
    };
    const onError = (e: any) => {
      console.error("Audio error: ", e);
      setError("Audio streaming failed. Re-connecting...");
      setIsLoading(false);
    };
    const onWaiting = () => setIsLoading(true);
    const onCanPlay = () => setIsLoading(false);

    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('durationchange', onDurationChange);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('error', onError);
    audio.addEventListener('waiting', onWaiting);
    audio.addEventListener('canplay', onCanPlay);

    // Initial load
    refreshMode();
    refreshStats();
    refreshQueue();
    refreshProfile();

    return () => {
      audio.pause();
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('durationchange', onDurationChange);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('error', onError);
      audio.removeEventListener('waiting', onWaiting);
      audio.removeEventListener('canplay', onCanPlay);
    };
  }, []);

  // Update Media Session controls
  useEffect(() => {
    if (!currentTrack || !('mediaSession' in navigator)) return;

    navigator.mediaSession.metadata = new MediaMetadata({
      title: currentTrack.track.title,
      artist: currentTrack.track.artist,
      album: currentTrack.track.album || 'Orbit Radio',
      artwork: [
        { src: '/icon.svg', sizes: '512x512', type: 'image/svg+xml' }
      ]
    });

    navigator.mediaSession.setActionHandler('play', () => audioRef.current?.play());
    navigator.mediaSession.setActionHandler('pause', () => audioRef.current?.pause());
    navigator.mediaSession.setActionHandler('nexttrack', () => skipTrack());
    // Seek action handlers
    navigator.mediaSession.setActionHandler('seekto', (details) => {
      if (details.seekTime !== undefined && audioRef.current) {
        audioRef.current.currentTime = details.seekTime;
      }
    });

  }, [currentTrack]);

  // Synchronize queue size:
  // - If queue is empty but tracks exist in DB → auto-generate and play
  // - If queue is running low (< 3) → top it up silently
  useEffect(() => {
    const cachedTracks = acousticStats?.cached_tracks ?? 0;
    if (upcomingQueue.length === 0 && !currentTrack && cachedTracks > 0 && !isGeneratingRef.current) {
      // Initial boot: library is synced but nothing is playing yet
      triggerQueueGeneration(true);
    } else if (upcomingQueue.length > 0 && upcomingQueue.length < 3 && !isGeneratingRef.current) {
      triggerQueueGeneration(false);
    }
  }, [upcomingQueue, acousticStats]);

  // Volume persistent store
  const setVolume = (vol: number) => {
    _setVolume(vol);
    localStorage.setItem('orbit-volume', String(vol));
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : vol;
    }
  };

  const toggleMute = () => {
    setIsMuted(prev => {
      const next = !prev;
      if (audioRef.current) {
        audioRef.current.volume = next ? 0 : volume;
      }
      return next;
    });
  };

  const seek = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setProgress(time);
    }
  };

  const triggerQueueGeneration = async (autoPlay = false) => {
    if (isGeneratingRef.current) return;
    isGeneratingRef.current = true;
    setIsLoading(true);
    try {
      const res = await fetch('/api/queue/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: 5 })
      });
      const data = await res.json();
      if (data.status === 'success') {
        await refreshQueue();
        // Auto-play first track on initial station boot
        if (autoPlay && data.recommendations && data.recommendations.length > 0) {
          await playTrack(data.recommendations[0]);
        }
      }
    } catch (err) {
      console.error("Queue replenishment failed: ", err);
    } finally {
      isGeneratingRef.current = false;
      setIsLoading(false);
    }
  };

  // Manual "Start Station" trigger — called by the UI button
  const startStation = async () => {
    await triggerQueueGeneration(true);
  };

  const triggerPrefetch = () => {
    if (hasPrefetchedRef.current || upcomingQueue.length === 0) return;
    hasPrefetchedRef.current = true;
    
    const nextTrack = upcomingQueue[0];
    const prefetchUrl = `/api/subsonic/stream/${nextTrack.track.id}`;
    
    console.log(`Silently pre-fetching next song: ${nextTrack.track.title}`);
    const nextAudio = new Audio();
    nextAudio.src = prefetchUrl;
    nextAudio.preload = "auto";
    nextAudio.load();
    nextAudioRef.current = nextAudio;
  };

  const refreshQueue = async () => {
    try {
      const res = await fetch('/api/queue/');
      const data = await res.json();
      if (data.status === 'success') {
        setUpcomingQueue(data.queue.upcoming);
        // Sync currently playing track state if changed
        if (data.queue.current) {
          const isSame = currentTrack?.id === data.queue.current.id;
          if (!isSame) {
            setCurrentTrack(data.queue.current);
            if (audioRef.current && audioRef.current.src !== `/api/subsonic/stream/${data.queue.current.track.id}`) {
              audioRef.current.src = `/api/subsonic/stream/${data.queue.current.track.id}`;
              setProgress(0);
              hasPrefetchedRef.current = false;
            }
          }
        } else if (data.queue.upcoming.length > 0 && !currentTrack) {
          // If queue loaded but nothing is playing, play first song
          playTrack(data.queue.upcoming[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load queue:", err);
      setError("Failed to reach Orbit backend.");
    }
  };

  const refreshProfile = async () => {
    try {
      const res = await fetch('/api/profile/');
      const data = await res.json();
      if (data.status === 'success') {
        setUserProfile(data.profile);
      }
    } catch (err) {
      console.error("Profile load failed:", err);
    }
  };

  const regenerateProfile = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/profile/regenerate', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setUserProfile(data.profile);
      }
    } catch (err) {
      console.error("Profile regenerate failed:", err);
      setError("Failed to regenerate LLM profile.");
    } finally {
      setIsLoading(false);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current || !currentTrack) return;
    
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(e => {
        console.error("Playback failed:", e);
      });
    }
  };

  const playTrack = async (item: QueueItem) => {
    if (!audioRef.current) return;
    setIsLoading(true);
    setError(null);
    hasPrefetchedRef.current = false;

    try {
      // Notify backend
      const res = await fetch(`/api/queue/play/${item.id}`, { method: 'POST' });
      const data = await res.json();
      
      if (data.status === 'success') {
        setCurrentTrack(item);
        
        // Check if we have preloaded this exact audio
        if (nextAudioRef.current && nextAudioRef.current.src.endsWith(`/api/subsonic/stream/${item.track.id}`)) {
          // Swap audio objects
          audioRef.current.pause();
          audioRef.current = nextAudioRef.current;
          audioRef.current.volume = isMuted ? 0 : volume;
          
          // Re-bind listeners
          bindAudioListeners(audioRef.current);
          nextAudioRef.current = null;
        } else {
          audioRef.current.src = `/api/subsonic/stream/${item.track.id}`;
        }
        
        setProgress(0);
        audioRef.current.play().catch(e => console.error("Play failed:", e));
        
        // Refresh local queue list
        await refreshQueue();
      }
    } catch (err) {
      console.error("Failed to play track:", err);
      setError("Failed to connect to backend for streaming.");
      setIsLoading(false);
    }
  };

  const bindAudioListeners = (audio: HTMLAudioElement) => {
    // Re-bind listeners when swapping audio objects
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onTimeUpdate = () => {
      setProgress(audio.currentTime);
      if (audio.duration && (audio.currentTime / audio.duration) >= 0.8) {
        triggerPrefetch();
      }
    };
    const onDurationChange = () => setDuration(audio.duration);
    const onEnded = () => handleSongEnded();
    const onError = () => {
      setError("Streaming interrupted. Retrying...");
      setIsLoading(false);
    };
    const onWaiting = () => setIsLoading(true);
    const onCanPlay = () => setIsLoading(false);

    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('durationchange', onDurationChange);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('error', onError);
    audio.addEventListener('waiting', onWaiting);
    audio.addEventListener('canplay', onCanPlay);
  };

  const handleSongEnded = () => {
    // Current song ended, trigger next track
    skipTrack();
  };

  const skipTrack = async () => {
    if (!currentTrack) return;
    setIsLoading(true);
    try {
      const res = await fetch(`/api/queue/skip/${currentTrack.id}`, { method: 'POST' });
      const data = await res.json();
      
      if (data.status === 'success') {
        setProgress(0);
        // Backend clear the queue and triggered course correction. Let's load the new queue.
        await refreshQueue();
        
        // Check if there's any song in the newly fetched upcoming queue, and play it
        if (data.recommendations && data.recommendations.length > 0) {
          const nextItem = data.recommendations[0];
          await playTrack(nextItem);
        } else {
          // Fallback refresh
          const queueRes = await fetch('/api/queue/');
          const queueData = await queueRes.json();
          if (queueData.status === 'success' && queueData.queue.upcoming.length > 0) {
            await playTrack(queueData.queue.upcoming[0]);
          } else {
            setCurrentTrack(null);
            setIsPlaying(false);
          }
        }
      }
    } catch (err) {
      console.error("Skip track failed:", err);
      setError("Skip action failed.");
      setIsLoading(false);
    }
  };

  const likeTrack = async (trackId: string) => {
    try {
      await fetch(`/api/queue/like/${trackId}`, { method: 'POST' });
      await refreshProfile(); // Refresh taste profile representation
    } catch (err) {
      console.error("Like track failed:", err);
    }
  };

  const dislikeTrack = async (trackId: string) => {
    try {
      await fetch(`/api/queue/dislike/${trackId}`, { method: 'POST' });
      await refreshQueue(); // Refresh upcoming queue in case it got cleared
      await refreshProfile();
      
      // If the current track was disliked, skip it immediately!
      if (currentTrack?.track.id === trackId) {
        await skipTrack();
      }
    } catch (err) {
      console.error("Dislike track failed:", err);
    }
  };

  const refreshMode = async () => {
    try {
      const res = await fetch('/api/queue/mode');
      const data = await res.json();
      if (data.status === 'success') {
        setRecommendationModeState(data.mode);
      }
    } catch (err) {
      console.error("Failed to load recommendation mode:", err);
    }
  };

  const refreshStats = async () => {
    try {
      const res = await fetch('/api/subsonic/stats');
      const data = await res.json();
      if (data.status === 'success' || data.status === 'partial_success') {
        setAcousticStats(data.stats);
      }
    } catch (err) {
      console.error("Failed to fetch acoustic/subsonic stats:", err);
    }
  };

  const setRecommendationMode = async (mode: 'llm' | 'local') => {
    try {
      const res = await fetch('/api/queue/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setRecommendationModeState(mode);
        setCurrentTrack(null);
        setUpcomingQueue([]);
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.src = '';
        }
        setProgress(0);
        setIsPlaying(false);
        await refreshQueue();
        await refreshStats();
      }
    } catch (err) {
      console.error("Failed to update recommendation mode:", err);
    }
  };

  const clearQueue = async () => {
    try {
      await fetch('/api/queue/clear', { method: 'POST' });
      setCurrentTrack(null);
      setIsPlaying(false);
      setUpcomingQueue([]);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }
    } catch (err) {
      console.error("Failed to clear queue:", err);
    }
  };

  return (
    <AudioPlayerContext.Provider value={{
      currentTrack,
      upcomingQueue,
      isPlaying,
      progress,
      duration,
      volume,
      isMuted,
      isLoading,
      userProfile,
      error,
      recommendationMode,
      acousticStats,
      togglePlay,
      playTrack,
      skipTrack,
      likeTrack,
      dislikeTrack,
      seek,
      setVolume,
      toggleMute,
      refreshQueue,
      refreshProfile,
      regenerateProfile,
      clearQueue,
      setRecommendationMode,
      refreshStats,
      startStation
    }}>
      {children}
    </AudioPlayerContext.Provider>
  );
};

export const useAudioPlayer = () => {
  const context = useContext(AudioPlayerContext);
  if (context === undefined) {
    throw new Error('useAudioPlayer must be used within an AudioPlayerProvider');
  }
  return context;
};
