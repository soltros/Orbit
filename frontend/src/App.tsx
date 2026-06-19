import React, { useState } from 'react';
import { AudioPlayerProvider, useAudioPlayer } from './context/AudioPlayerContext';
import { PlayerView } from './components/PlayerView';
import { QueueView } from './components/QueueView';
import { DiscoveryHub } from './components/DiscoveryHub';
import { ArtistBrowser } from './components/ArtistBrowser';
import { LoginView } from './components/LoginView';
import { SetupWizard } from './components/SetupWizard';
import { SettingsModal } from './components/SettingsModal';
import { Radio, AlertTriangle, Users, LogOut, RefreshCw, Settings } from 'lucide-react';

const OrbitApp: React.FC = () => {
  const { error, currentTrack, acousticStats } = useAudioPlayer();
  const [browserOpen, setBrowserOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isSetupNeeded, setIsSetupNeeded] = useState<boolean | null>(null);
  
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncCount, setSyncCount] = useState(0);

  const hasTracks = (acousticStats?.cached_tracks ?? 0) > 0;

  React.useEffect(() => {
    fetch('/api/setup/status')
      .then(res => res.json())
      .then(data => {
        setIsSetupNeeded(data.needs_setup);
      })
      .catch(() => setIsSetupNeeded(false)); // fallback
  }, []);

  React.useEffect(() => {
    if (!isAuthenticated) return;
    
    let interval: NodeJS.Timeout;
    
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
      interval = setInterval(checkSync, 3000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isAuthenticated, isSyncing]);

  if (isSetupNeeded === null) {
    return <div className="min-h-screen bg-[#050508]"></div>;
  }

  if (isSetupNeeded) {
    return <SetupWizard onComplete={() => setIsSetupNeeded(false)} />;
  }

  if (!isAuthenticated) {
    return <LoginView onLoginSuccess={() => setIsAuthenticated(true)} />;
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
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Radio className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <h1 className="text-md font-bold tracking-widest text-white uppercase">Orbit</h1>
            <p className="text-[9px] text-gray-500 tracking-wider">INTELLIGENT JUKEBOX</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Browse Artists button — always visible when tracks are synced */}
          {hasTracks && (
            <button
              onClick={() => setBrowserOpen(true)}
              className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/5 px-3 py-1.5 rounded-lg transition duration-150"
            >
              <Users className="w-3.5 h-3.5" />
              Artists
            </button>
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

          <button
            onClick={() => setSettingsOpen(true)}
            title="Settings"
            className="flex items-center gap-1.5 text-xs font-semibold text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/5 px-3 py-1.5 rounded-lg transition duration-150"
          >
            <Settings className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Settings</span>
          </button>

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
      <main className="flex-grow w-full max-w-5xl mx-auto px-6 py-6 grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
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
