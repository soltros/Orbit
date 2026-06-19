import React, { useState, useEffect } from 'react';
import { X, Heart, Play, Loader2, Music } from 'lucide-react';

interface FavoritesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSeed: (trackId: string) => void;
}

export const FavoritesModal: React.FC<FavoritesModalProps> = ({ isOpen, onClose, onSeed }) => {
  const [favorites, setFavorites] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      setError(null);
      fetch('/api/profile/favorites')
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            setFavorites(data.favorites);
          } else {
            setError(data.message || 'Failed to load favorites.');
          }
          setIsLoading(false);
        })
        .catch(() => {
          setError('Network error loading favorites.');
          setIsLoading(false);
        });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose}></div>
      <div className="relative w-full max-w-2xl bg-slate-900 border border-white/10 rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Heart className="w-5 h-5 text-emerald-400" /> Orbit Favorites
          </h2>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto no-scrollbar">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mb-4" />
              <p className="text-sm text-gray-400">Loading your favorites...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
              {error}
            </div>
          ) : favorites.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
                <Heart className="w-8 h-8 text-gray-600" />
              </div>
              <h3 className="text-lg font-bold text-gray-300 mb-2">No Favorites Yet</h3>
              <p className="text-sm text-gray-500 max-w-sm">
                Like songs while listening to Orbit to save them here. This list only tracks songs you've favorited directly through Orbit.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {favorites.map((track) => (
                <div 
                  key={track.id} 
                  className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 transition group"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <img 
                      src={`/api/subsonic/cover/${track.id}`} 
                      alt="Cover" 
                      className="w-10 h-10 rounded-md object-cover bg-slate-800"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = '/icon.svg';
                      }}
                    />
                    <div className="truncate">
                      <p className="text-sm font-bold text-gray-200 truncate">{track.title}</p>
                      <p className="text-xs text-gray-400 truncate">{track.artist}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      onSeed(track.id);
                      onClose();
                    }}
                    title="Seed a new station from this track"
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-wider rounded-lg border border-emerald-500/20 transition opacity-0 group-hover:opacity-100"
                  >
                    <Play className="w-3.5 h-3.5" />
                    Seed Station
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
