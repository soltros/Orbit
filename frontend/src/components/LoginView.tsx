import React, { useState, useEffect } from 'react';
import { LogIn, Server, User, KeyRound, Loader2 } from 'lucide-react';

interface LoginViewProps {
  onLoginSuccess: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess }) => {
  const [url, setUrl] = useState(() => localStorage.getItem('orbit_login_url') || '');
  const [username, setUsername] = useState(() => localStorage.getItem('orbit_login_username') || '');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(() => !!localStorage.getItem('orbit_login_username'));
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if we are already logged in or have a fallback config
  useEffect(() => {
    fetch('/api/auth/me')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          onLoginSuccess();
        } else {
          setIsLoading(false);
        }
      })
      .catch(() => {
        setIsLoading(false);
      });
  }, [onLoginSuccess]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, username, password })
      });
      const data = await res.json();

      if (data.status === 'success') {
        if (rememberMe) {
          localStorage.setItem('orbit_login_url', url);
          localStorage.setItem('orbit_login_username', username);
        } else {
          localStorage.removeItem('orbit_login_url');
          localStorage.removeItem('orbit_login_username');
        }
        onLoginSuccess();
      } else {
        setError(data.message || 'Login failed. Check your credentials and server URL.');
      }
    } catch (err) {
      setError('A network error occurred. Ensure the server is reachable.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 p-10 bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl shadow-2xl">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-gradient-to-tr from-indigo-500 to-violet-600 rounded-full flex items-center justify-center shadow-lg shadow-indigo-500/30 mb-6">
            <LogIn className="h-8 w-8 text-white" />
          </div>
          <h2 className="mt-2 text-3xl font-extrabold text-white tracking-tight">Connect to Orbit</h2>
          <p className="mt-2 text-sm text-gray-400">
            Log in with your Subsonic or Navidrome server credentials.
          </p>
          <p className="mt-4 text-xs text-indigo-400/80 bg-indigo-500/10 py-2 px-3 rounded-lg inline-block border border-indigo-500/20">
            <strong>First time setup?</strong> Log in as <code className="text-white">admin</code> / <code className="text-white">admin123</code> with any URL to configure.
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleLogin}>
          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
              {error}
            </div>
          )}
          
          <div className="space-y-4 rounded-md shadow-sm">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Server className="h-5 w-5 text-gray-500" />
              </div>
              <input
                type="url"
                required
                className="appearance-none rounded-xl relative block w-full px-3 py-3 pl-10 border border-white/10 bg-slate-950/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-200"
                placeholder="Server URL (e.g., https://music.example.com)"
                value={url}
                onChange={e => setUrl(e.target.value)}
              />
            </div>
            
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-5 w-5 text-gray-500" />
              </div>
              <input
                type="text"
                required
                className="appearance-none rounded-xl relative block w-full px-3 py-3 pl-10 border border-white/10 bg-slate-950/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-200"
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
                className="appearance-none rounded-xl relative block w-full px-3 py-3 pl-10 border border-white/10 bg-slate-950/50 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-200"
                placeholder="Password"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 text-indigo-500 focus:ring-indigo-500 border-gray-600 rounded bg-slate-900/50"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-400 cursor-pointer select-none">
                Remember me
              </label>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-bold rounded-xl text-white bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 focus:ring-offset-slate-900 shadow-lg shadow-indigo-500/25 disabled:opacity-50 transition duration-200"
            >
              {isSubmitting ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'Connect'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
