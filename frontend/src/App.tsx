import React, { useState } from 'react';
import { AudioPlayerProvider, useAudioPlayer } from './context/AudioPlayerContext';
import { PlayerView } from './components/PlayerView';
import { QueueView } from './components/QueueView';
import { DiscoveryHub } from './components/DiscoveryHub';
import { ArtistBrowser } from './components/ArtistBrowser';
import { LoginView } from './components/LoginView';
import { SetupWizard } from './components/SetupWizard';
import { SettingsModal } from './components/SettingsModal';
import { FavoritesModal } from './components/FavoritesModal';
import { Radio, AlertTriangle, Users, LogOut, RefreshCw, Settings, Heart } from 'lucide-react';

const OrbitApp: React.FC = () => {
  const { error, acousticStats, clearQueue } = useAudioPlayer();
  const [browserOpen, setBrowserOpen] = useState(false);
  const [favoritesOpen, setFavoritesOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isSetupNeeded, setIsSetupNeeded] = useState<boolean | null>(null);
  
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncCount, setSyncCount] = useState(0);

  const hasTracks = (acousticStats?.cached_tracks ?? 0) > 0;

  React.useEffect(() => {
    (async () => {
      try {
        const statusRes = await fetch('/api/setup/status');
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (statusData.needs_setup) {
            setIsSetupNeeded(true);
            return;
          }
        }
        
        const res = await fetch('/api/auth/me');
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'success') {
            setIsAuthenticated(true);
            setIsAdmin(data.is_admin === true);
          }
        }
      } catch (err) {
        console.error('Failed to verify auth:', err);
      }
      setIsSetupNeeded(false);
    })();
  }, []);

  React.useEffect(() => {
    if (!isAuthenticated) return;
    
    let interval: ReturnType<typeof setInterval>;
    
    const checkSync = async () => {
      try {
        const res = await fetch('/api/subsonic/sync/status');
        const data = await res.json();
        setIsSyncing(data.is_syncing);
        setSyncCount(data.track_count);
      } catch (err) {}
    };

    // Always check once to see if a background sync is happening
    if (!isSyncing) {
        checkSync();
    }

    if (isSyncing) {
      clearQueue();
      interval = setInterval(checkSync, 3000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isAuthenticated, isSyncing, clearQueue]);

  if (isSetupNeeded === null) {
    return <div className="min-h-screen bg-[#050508]"></div>;
  }

  if (isSetupNeeded) {
    return <SetupWizard onComplete={() => setIsSetupNeeded(false)} />;
  }

  if (!isAuthenticated) {
    return <LoginView onLoginSuccess={() => {
      setIsAuthenticated(true);
      // Re-fetch me to get admin status
      fetch('/api/auth/me')
        .then(res => res.json())
        .then(data => setIsAdmin(data.is_admin === true));
    }} />;
  }

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      setIsAuthenticated(false);
    } catch (err) {
      console.error('Logout failed', err);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#050508] text-gray-100 pb-12">
      {/* Background visual decoration */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-900/10 rounded-full blur-[100px] pointer-events-none animate-pulse-slow"></div>
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-900/10 rounded-full blur-[100px] pointer-events-none animate-pulse-slow"></div>

      {/* Header */}
      <header className="w-full max-w-5xl mx-auto px-6 py-5 flex items-center justify-between border-b border-white/5 backdrop-blur-md sticky top-0 z-30">
        <div className="flex items-center gap-2.5">
          <img src="/icon.svg" className="w-8 h-8" alt="Orbit Logo" />
          <div>
            <h1 className="text-md font-bold tracking-widest text-white uppercase">Orbit</h1>
            <p className="text-[9px] text-gray-500 tracking-wider">INTELLIGENT JUKEBOX</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Browse Artists button — always visible when tracks are synced */}
          {hasTracks && !isSyncing && (
            <>
              <button
                onClick={() => setFavoritesOpen(true)}
                title="View Orbit Favorites"
                className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 px-3 py-1.5 rounded-lg transition duration-150"
              >
                <Heart className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Favorites</span>
              </button>

              <button
                onClick={() => setBrowserOpen(true)}
                className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/5 px-3 py-1.5 rounded-lg transition duration-150"
              >
                <Users className="w-3.5 h-3.5" />
                Artists
              </button>
            </>
          )}

          <button
            onClick={async () => {
              if (isSyncing) return;
              try {
                setIsSyncing(true);
                await fetch('/api/subsonic/sync', { method: 'POST' });
              } catch (err) {
                console.error(err);
                setIsSyncing(false);
              }
            }}
            title="Sync Subsonic Database"
            disabled={isSyncing}
            className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition duration-150 ${
              isSyncing 
                ? 'text-indigo-300 bg-indigo-500/20 border-indigo-500/20 cursor-not-allowed'
                : 'text-indigo-400 hover:text-indigo-300 bg-indigo-500/5 hover:bg-indigo-500/10 border border-indigo-500/10'
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? `Syncing... (${syncCount})` : 'Sync'}
          </button>

          {isAdmin && (
            <button
              onClick={() => setSettingsOpen(true)}
              title="Settings"
              className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/5 px-3 py-1.5 rounded-lg transition duration-150"
            >
              <Settings className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Settings</span>
            </button>
          )}

          <button
            onClick={handleLogout}
            title="Log out"
            className="flex items-center gap-1.5 text-xs font-semibold text-red-400 hover:text-red-300 bg-red-500/5 hover:bg-red-500/10 border border-red-500/10 px-3 py-1.5 rounded-lg transition duration-150"
          >
            <LogOut className="w-3.5 h-3.5" />
            Logout
          </button>

          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
            <span className="text-[10px] font-bold tracking-wide text-gray-400 uppercase">Live Connection</span>
          </div>
        </div>
      </header>

      {/* Error Alert Bar */}
      {error && (
        <div className="w-full max-w-md mx-auto mt-4 px-4">
          <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-2xl text-xs text-amber-400 font-medium">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        </div>
      )}

      {/* Main Grid Layout */}
      <main className="flex-grow w-full max-w-5xl mx-auto px-6 py-6 flex flex-col justify-center items-center">
        {isSyncing ? (
          <div className="flex flex-col items-center justify-center gap-6 p-12 bg-indigo-900/10 border border-indigo-500/20 rounded-3xl backdrop-blur-sm w-full max-w-2xl text-center shadow-2xl">
            <div className="relative my-4">
               <div className="absolute inset-0 border-4 border-indigo-500/20 rounded-full animate-ping"></div>
               <RefreshCw className="w-16 h-16 text-indigo-400 animate-spin relative z-10" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Syncing your Universe</h2>
              <p className="text-indigo-200/60 max-w-md mx-auto leading-relaxed">
                Orbit is downloading and analyzing your Subsonic library. We can't safely generate a station until the catalog is fully ingested. Please wait...
              </p>
            </div>
            <div className="bg-indigo-950/50 border border-indigo-500/30 px-6 py-3 rounded-full flex items-center gap-3 mt-4 shadow-inner">
               <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
               <span className="text-sm font-mono text-indigo-300 font-bold tracking-wider">{syncCount.toLocaleString()} TRACKS INDEXED</span>
            </div>
          </div>
        ) : (
          <div className="w-full grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
            {/* Left Side: Discovery & Stats */}
            <div className="md:col-span-4 order-3 md:order-1 flex flex-col gap-6">
              <DiscoveryHub onOpenBrowser={() => setBrowserOpen(true)} />
            </div>

            {/* Center: Audio Player */}
            <div className="md:col-span-4 order-1 md:order-2 flex flex-col items-center">
              <PlayerView onOpenBrowser={() => setBrowserOpen(true)} />
            </div>

            {/* Right Side: Rolling Queue */}
            <div className="md:col-span-4 order-2 md:order-3 flex flex-col gap-6">
              <QueueView />
            </div>
          </div>
        )}
      </main>

      {/* Artist Browser Drawer — rendered at root so it overlays everything */}
      {browserOpen && (
        <ArtistBrowser onClose={() => setBrowserOpen(false)} />
      )}

      {/* Settings Modal — rendered at root so it overlays everything */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />

      <FavoritesModal
        isOpen={favoritesOpen}
        onClose={() => setFavoritesOpen(false)}
        onSeed={async (trackId) => {
          // Send request to seed by track
          try {
            await fetch('/api/library/seed', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ type: 'track', id: trackId })
            });
            await fetch('/api/queue/clear', { method: 'POST' });
            window.location.reload();
          } catch (err) {
            console.error('Failed to seed from favorite', err);
          }
        }}
      />
    </div>
  );
};

function App() {
  return (
    <AudioPlayerProvider>
      <OrbitApp />
    </AudioPlayerProvider>
  );
}

export default App;
