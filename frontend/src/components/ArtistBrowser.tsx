import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAudioPlayer } from '../context/AudioPlayerContext';
import {
  X, Search, Music, ChevronRight, ChevronDown, Shuffle, Play, Loader2, Users, Disc
} from 'lucide-react';

interface Artist {
  name: string;
  track_count: number;
}

interface Track {
  id: string;
  title: string;
  artist: string;
  album: string | null;
  duration: number;
  bpm: number | null;
  acoustic_status: string;
}

interface ArtistBrowserProps {
  onClose: () => void;
}

function formatDuration(secs: number): string {
  if (!secs) return '';
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

export const ArtistBrowser: React.FC<ArtistBrowserProps> = ({ onClose }) => {
  const { seedStation, isLoading } = useAudioPlayer();

  const [artists, setArtists] = useState<Artist[]>([]);
  const [filteredArtists, setFilteredArtists] = useState<Artist[]>([]);
  const [search, setSearch] = useState('');
  const [loadingArtists, setLoadingArtists] = useState(true);
  const [expandedArtist, setExpandedArtist] = useState<string | null>(null);
  const [artistTracks, setArtistTracks] = useState<Record<string, Track[]>>({});
  const [loadingTracks, setLoadingTracks] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);

  const searchRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [tab, setTab] = useState<'artists' | 'genres'>('artists');
  const [genres, setGenres] = useState<string[]>([]);
  
  // Load artist list and genres on mount
  useEffect(() => {
    fetchArtists();
    fetchGenres();
    setTimeout(() => searchRef.current?.focus(), 100);
  }, []);

  // Filter as user types
  useEffect(() => {
    const q = search.trim().toLowerCase();
    if (!q) {
      setFilteredArtists(artists);
    } else {
      setFilteredArtists(artists.filter(a => a.name.toLowerCase().includes(q)));
    }
  }, [search, artists]);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const fetchArtists = async () => {
    setLoadingArtists(true);
    try {
      const res = await fetch('/api/library/artists');
      const data = await res.json();
      if (data.status === 'success') {
        setArtists(data.artists);
        setFilteredArtists(data.artists);
      }
    } catch (e) {
      console.error('Failed to load artists:', e);
    } finally {
      setLoadingArtists(false);
    }
  };

  const fetchGenres = async () => {
    try {
      const res = await fetch('/api/library/genres');
      const data = await res.json();
      if (data.status === 'success') {
        setGenres(data.genres);
      }
    } catch (e) {
      console.error('Failed to load genres:', e);
    }
  };

  const toggleArtist = async (artistName: string) => {
    if (expandedArtist === artistName) {
      setExpandedArtist(null);
      return;
    }
    setExpandedArtist(artistName);

    // Only fetch if not cached
    if (!artistTracks[artistName]) {
      setLoadingTracks(artistName);
      try {
        const res = await fetch(`/api/library/artists/${encodeURIComponent(artistName)}/tracks`);
        const data = await res.json();
        if (data.status === 'success') {
          setArtistTracks(prev => ({ ...prev, [artistName]: data.tracks }));
        }
      } catch (e) {
        console.error('Failed to load artist tracks:', e);
      } finally {
        setLoadingTracks(null);
      }
    }
  };

  const handleSeedArtist = async (artistName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSeeding(true);
    await seedStation({ artist: artistName });
    setSeeding(false);
    onClose();
  };

  const handleSeedTrack = async (trackId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSeeding(true);
    await seedStation({ trackId });
    setSeeding(false);
    onClose();
  };

  // Group artists alphabetically
  const grouped = filteredArtists.reduce<Record<string, Artist[]>>((acc, artist) => {
    const letter = artist.name[0]?.toUpperCase().match(/[A-Z]/) ? artist.name[0].toUpperCase() : '#';
    if (!acc[letter]) acc[letter] = [];
    acc[letter].push(artist);
    return acc;
  }, {});
  const letters = Object.keys(grouped).sort();

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        ref={containerRef}
        className="fixed inset-x-0 bottom-0 z-50 flex flex-col bg-[#0a0a12] border-t border-white/10 rounded-t-3xl shadow-2xl"
        style={{ maxHeight: '85vh' }}
      >
        {/* Handle bar */}
        <div className="flex justify-center pt-3 pb-1 flex-shrink-0">
          <div className="w-10 h-1 bg-white/10 rounded-full" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 flex-shrink-0 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center">
              <Disc className="w-3.5 h-3.5 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">Library Browser</h2>
              <p className="text-[10px] text-gray-500">
                Pick an artist or genre to seed the station
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-500 hover:text-gray-200 hover:bg-white/5 rounded-lg transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-white/5 flex-shrink-0">
          <button
            onClick={() => setTab('artists')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              tab === 'artists' ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Artists
          </button>
          <button
            onClick={() => setTab('genres')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              tab === 'genres' ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Genres
          </button>
        </div>

        {tab === 'artists' && (
          <>
            {/* Search bar */}
            <div className="px-4 py-3 flex-shrink-0">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                <input
                  ref={searchRef}
                  type="text"
                  placeholder="Search artists..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="w-full pl-9 pr-4 py-2.5 bg-white/[0.04] border border-white/10 rounded-xl text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 focus:bg-white/[0.06] transition"
                />
                {search && (
                  <button
                    onClick={() => setSearch('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-400"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Artist list */}
            <div className="flex-1 overflow-y-auto px-4 pb-8 space-y-1 no-scrollbar">

              {loadingArtists ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
              <p className="text-sm text-gray-500">Loading library...</p>
            </div>
          ) : filteredArtists.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-2">
              <Music className="w-8 h-8 text-gray-700" />
              <p className="text-sm text-gray-500">No artists found.</p>
              {search && (
                <button onClick={() => setSearch('')} className="text-xs text-indigo-400 hover:text-indigo-300 mt-1">
                  Clear search
                </button>
              )}
            </div>
          ) : (
            letters.map(letter => (
              <div key={letter}>
                {/* Letter divider — only show when not filtering */}
                {!search && (
                  <div className="sticky top-0 bg-[#0a0a12]/90 backdrop-blur-sm py-1 px-1 z-10">
                    <span className="text-[10px] font-bold text-indigo-400/60 uppercase tracking-widest">
                      {letter}
                    </span>
                  </div>
                )}

                {grouped[letter].map(artist => {
                  const isExpanded = expandedArtist === artist.name;
                  const tracks = artistTracks[artist.name] || [];
                  const isLoadingThis = loadingTracks === artist.name;

                  return (
                    <div key={artist.name} className="mb-1">
                      {/* Artist row */}
                      <div
                        onClick={() => toggleArtist(artist.name)}
                        className={`group flex items-center justify-between p-3 rounded-2xl cursor-pointer transition duration-150 ${
                          isExpanded
                            ? 'bg-indigo-500/10 border border-indigo-500/20'
                            : 'bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] hover:border-white/10'
                        }`}
                      >
                        <div className="flex items-center gap-3 truncate">
                          {/* Expand chevron */}
                          <div className={`text-gray-600 group-hover:text-indigo-400 transition ${isExpanded ? 'text-indigo-400' : ''}`}>
                            {isExpanded
                              ? <ChevronDown className="w-4 h-4" />
                              : <ChevronRight className="w-4 h-4" />
                            }
                          </div>

                          {/* Artist name + track count */}
                          <div className="truncate">
                            <span className={`text-sm font-semibold truncate ${isExpanded ? 'text-white' : 'text-gray-200 group-hover:text-white'}`}>
                              {artist.name}
                            </span>
                            <span className="ml-2 text-[10px] text-gray-600">
                              {artist.track_count} {artist.track_count === 1 ? 'track' : 'tracks'}
                            </span>
                          </div>
                        </div>

                        {/* Seed from random track button */}
                        <button
                          onClick={(e) => handleSeedArtist(artist.name, e)}
                          disabled={seeding || isLoading}
                          title={`Seed station with a random ${artist.name} track`}
                          className="ml-3 flex-shrink-0 flex items-center gap-1.5 text-[11px] font-bold text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/25 border border-indigo-500/20 hover:border-indigo-500/40 px-2.5 py-1 rounded-lg disabled:opacity-40 transition"
                        >
                          <Shuffle className="w-3 h-3" />
                          Seed
                        </button>
                      </div>

                      {/* Expandable track list */}
                      {isExpanded && (
                        <div className="ml-7 mt-1 mb-2 rounded-xl overflow-hidden border border-white/[0.04]">
                          {isLoadingThis ? (
                            <div className="flex items-center justify-center py-5 gap-2">
                              <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                              <span className="text-xs text-gray-500">Loading tracks...</span>
                            </div>
                          ) : (
                            <div className="divide-y divide-white/[0.04]">
                              {tracks.map((track, idx) => (
                                <div
                                  key={track.id}
                                  className="group/track flex items-center justify-between px-3 py-2.5 bg-white/[0.015] hover:bg-white/[0.04] transition cursor-pointer"
                                  onClick={(e) => handleSeedTrack(track.id, e)}
                                >
                                  <div className="flex items-center gap-3 truncate min-w-0">
                                    <span className="text-[10px] font-bold text-gray-700 w-4 text-right flex-shrink-0">
                                      {(idx + 1).toString().padStart(2, '0')}
                                    </span>
                                    <div className="truncate min-w-0">
                                      <p className="text-xs font-semibold text-gray-300 truncate group-hover/track:text-white transition">
                                        {track.title}
                                      </p>
                                      {track.album && (
                                        <p className="text-[10px] text-gray-600 truncate">{track.album}</p>
                                      )}
                                    </div>
                                  </div>

                                  <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                                    {track.bpm && (
                                      <span className="text-[9px] font-bold text-indigo-400/60 bg-indigo-500/5 px-1.5 py-0.5 rounded">
                                        {track.bpm} BPM
                                      </span>
                                    )}
                                    {track.duration > 0 && (
                                      <span className="text-[10px] text-gray-600">
                                        {formatDuration(track.duration)}
                                      </span>
                                    )}
                                    <div className="opacity-0 group-hover/track:opacity-100 transition">
                                      <Play className="w-3.5 h-3.5 text-indigo-400" />
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>
        </>
        )}

        {tab === 'genres' && (
          <div className="flex-1 overflow-y-auto px-4 py-4 pb-8 space-y-2 no-scrollbar">
            <div className="grid grid-cols-2 gap-3">
              {genres.map(genre => (
                <button
                  key={genre}
                  onClick={async () => {
                    setSeeding(true);
                    await seedStation({ genre: genre });
                    setSeeding(false);
                    onClose();
                  }}
                  disabled={seeding}
                  className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-indigo-500/10 hover:border-indigo-500/20 hover:text-indigo-300 transition text-sm font-semibold text-gray-300 text-left group disabled:opacity-50"
                >
                  {genre}
                  <Shuffle className="w-4 h-4 text-gray-600 group-hover:text-indigo-400 transition" />
                </button>
              ))}
            </div>
            {genres.length === 0 && (
               <p className="text-center text-sm text-gray-500 py-10">No curated genres found.</p>
            )}
          </div>
        )}
      </div>

        {/* Bottom loading overlay */}
        {seeding && (
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm rounded-t-3xl flex flex-col items-center justify-center gap-3 z-10">
            <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
            <p className="text-sm font-semibold text-white">Seeding station...</p>
            <p className="text-xs text-gray-400">Generating your queue</p>
          </div>
        )}
      </div>
    </div>
  );
};
