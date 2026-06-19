# Orbit — Dev Testing Guide

This directory contains everything you need to run and test Orbit **without** a real Navidrome server.

---

## How It Works

```
dev/music/        ← Drop your test audio files here
dev/data/         ← SQLite database lands here (auto-created)
dev/mock_subsonic.py ← Fake Navidrome server (auto-started by Docker)
```

The dev stack spins up 4 containers:

| Container | Port | Purpose |
|---|---|---|
| `orbit-mock-subsonic` | 4533 | Fake Navidrome — reads dev/music/ |
| `orbit-backend-dev` | 5000 | Flask API with debug mode & live reload |
| `orbit-worker-dev` | — | Acoustic analysis (Librosa) |
| `orbit-frontend-dev` | 5173 | Vite HMR dev server |

---

## Quick Start

### Step 1 — Add music files

Drop audio files into `dev/music/`. Subdirectories work great:

```
dev/music/
  Artist Name/
    Album Title/
      01 - Track One.mp3
      02 - Track Two.flac
  Some Artist - Song.ogg
```

Any common format works: `.mp3` `.flac` `.ogg` `.opus` `.m4a` `.wav` `.aac`

The mock server reads ID3/Vorbis tags automatically. If your files have no tags, it falls back to folder/filename parsing.

---

### Step 2 — Start the dev stack

```bash
docker compose -f docker-compose.dev.yml --env-file .env.dev up --build
```

First build takes a few minutes (downloading Python + Node images, installing librosa). Subsequent starts are fast.

---

### Step 3 — Open Orbit

- **Frontend UI:** http://localhost:5173
- **Backend API:** http://localhost:5000
- **Mock Subsonic:** http://localhost:4533

---

## What to Verify

### ✅ Backend health
```bash
curl http://localhost:5000/health
# Expected: {"status": "healthy", "database": "connected"}
```

### ✅ Mock Subsonic is indexed
```bash
curl http://localhost:4533/list-tracks
# Expected: JSON list of your audio files
```

### ✅ Backend can talk to mock Subsonic
```bash
curl http://localhost:5000/api/subsonic/ping
# Expected: {"status": "success", "message": "Successfully connected to Subsonic/Navidrome server."}
```

### ✅ Sync tracks into Orbit's database
```bash
docker exec -it orbit-backend-dev flask sync-subsonic
# Expected: "Sync complete. Total tracks in database: N"
```

### ✅ Check stats (cached tracks, analysis progress)
```bash
curl http://localhost:5000/api/subsonic/stats
```

### ✅ Check acoustic worker progress
```bash
docker logs -f orbit-worker-dev
# Should show: "[INFO] Processing track: Artist — Title"
```

### ✅ Generate a queue (local mode — no LLM key needed)
```bash
curl -X POST http://localhost:5000/api/queue/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 5}'
```

### ✅ Get the current queue
```bash
curl http://localhost:5000/api/queue/
```

---

## Testing the LLM Mode

If you want to test the AI-powered recommendations:

1. Add your API key to `.env.dev`:
   ```
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-...
   RECOMMENDATION_MODE=llm
   ```

2. Restart the backend:
   ```bash
   docker compose -f docker-compose.dev.yml --env-file .env.dev restart backend
   ```

3. Switch to LLM mode in the UI (top-left mode toggle) or via API:
   ```bash
   curl -X POST http://localhost:5000/api/queue/mode \
     -H "Content-Type: application/json" \
     -d '{"mode": "llm"}'
   ```

---

## Useful Docker Commands

```bash
# View all container logs at once
docker compose -f docker-compose.dev.yml logs -f

# Restart just the backend after a code change
docker compose -f docker-compose.dev.yml restart backend

# Get a shell inside the backend container
docker exec -it orbit-backend-dev /bin/bash

# Run the Subsonic sync manually
docker exec -it orbit-backend-dev flask sync-subsonic

# Force the mock server to rescan music directory (after adding files)
curl http://localhost:4533/refresh-index

# Tear down everything (keeps dev/data/ intact)
docker compose -f docker-compose.dev.yml down

# Tear down and wipe the database too
docker compose -f docker-compose.dev.yml down && rm -rf dev/data/
```

---

## Database Inspection

The SQLite database lives at `dev/data/orbit_dev.db` on your host.
Open it with any SQLite client (DB Browser for SQLite, DBeaver, etc.) to inspect tracks, queue items, and interaction history.

```bash
# Quick CLI check
sqlite3 dev/data/orbit_dev.db "SELECT id, title, artist, acoustic_status FROM tracks LIMIT 20;"
```

---

## Seeding Without Docker (Optional)

If you want to seed the database from the host without running the full stack:

```bash
cd /path/to/Orbit
pip install flask flask-sqlalchemy mutagen python-dotenv
python dev/seed_db.py
```

This directly inserts tracks from `dev/music/` into `dev/data/orbit_dev.db`.

---

## Troubleshooting

**Backend can't connect to mock Subsonic:**
- Check mock server is running: `docker logs orbit-mock-subsonic`
- Verify `SUBSONIC_URL=http://orbit-mock-subsonic:4533` in `.env.dev`

**No tracks showing up after sync:**
- Confirm files are in `dev/music/` with a supported extension
- Hit `http://localhost:4533/list-tracks` to check the mock index
- If you added files after startup, hit `http://localhost:4533/refresh-index`

**Worker is not analyzing tracks:**
- Check it's running: `docker logs orbit-worker-dev`
- Tracks must be in the DB first (run `flask sync-subsonic` then watch worker logs)
- The worker resolves paths inside `/music` — confirm your files are actually there

**Frontend shows "Failed to reach Orbit backend":**
- The Vite proxy points to `orbit-backend-dev:5000`
- Confirm backend container is healthy: `curl http://localhost:5000/health`

**Acoustic analysis is slow:**
- The worker analyzes the middle 30 seconds of each file using librosa
- This takes 5–30 seconds per track depending on your CPU
- Watch progress with `docker logs -f orbit-worker-dev`
