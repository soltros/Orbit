import os
import time
import logging
import tempfile
import requests
import librosa
import numpy as np
import concurrent.futures
from app import create_app, db
from app.models import Track
from app.subsonic import SubsonicClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("orbit-worker")

# Initialize Flask app context to access SQLAlchemy models
app = create_app()

# Removed resolve_container_path since we now download directly from the Subsonic server
def extract_acoustic_features(file_path):
    """
    Extracts a 27-dimensional acoustic feature vector from the raw audio file:
    - Tempo/BPM (1 dim)
    - Energy/Flux (1 dim)
    - Chromagram key profile (12 dims)
    - Timbre MFCCs (13 dims)
    Analyzes only the middle 30 seconds of the file to protect CPU resource usage.
    """
    logger.info(f"Loading audio from: {file_path}")
    
    # 1. Fetch duration and load middle 30 seconds
    duration = librosa.get_duration(path=file_path)
    offset = max(0.0, (duration - 30.0) / 2.0)
    
    y, sr = librosa.load(file_path, sr=22050, offset=offset, duration=30.0)
    
    # 2. Extract Tempo / BPM
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0])
    else:
        tempo = float(tempo)
        
    # 3. Extract Chromagram (Key profile)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1) # 12 dimensions
    
    # Estimating Key via profiles (Krumhansl-Schmuckler correlations)
    key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    
    best_key = "Unknown"
    max_corr = -1.0
    
    for i in range(12):
        rolled = np.roll(chroma_mean, -i)
        corr_maj = np.corrcoef(rolled, major_profile)[0, 1]
        corr_min = np.corrcoef(rolled, minor_profile)[0, 1]
        
        if corr_maj > max_corr:
            max_corr = corr_maj
            best_key = f"{key_names[i]} Major"
        if corr_min > max_corr:
            max_corr = corr_min
            best_key = f"{key_names[i]} Minor"
            
    # 4. Extract Spectral Flux (Energy)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    energy = float(np.mean(onset_env))
    normalized_energy = min(1.0, max(0.0, energy / 10.0))
    
    # 5. Extract Timbre (MFCCs)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfccs_mean = np.mean(mfccs, axis=1) # 13 dimensions
    
    # Standardize scales of combined feature vector
    embedding = [
        tempo / 200.0, # Scale bpm
        normalized_energy
    ]
    embedding.extend(chroma_mean.tolist()) # Add chroma key features (0 to 1 scale)
    embedding.extend((mfccs_mean / 100.0).tolist()) # Add scaled MFCC features
    
    return {
        "bpm": int(round(tempo)) if tempo else None,
        "key": best_key,
        "energy": normalized_energy,
        "embedding": embedding
    }

def process_single_track(track_id):
    """Processes a single pending track, saving results to the SQLite database."""
    with app.app_context():
        track = Track.query.get(track_id)
        if not track:
            return False
            
        logger.info(f"Processing track: {track.title} - {track.artist} (ID: {track.id})")
        
        url = app.config.get('SUBSONIC_URL')
        user = app.config.get('SUBSONIC_USER')
        password = app.config.get('SUBSONIC_PASS')
        
        if not url or not user or not password:
            logger.error("Missing Subsonic credentials in settings. Cannot download track.")
            track.acoustic_status = 'failed'
            track.acoustic_error = "Missing Subsonic credentials."
            db.session.commit()
            return False
            
        client = SubsonicClient(base_url=url, username=user, password=password)
        # Request a highly compressed 64kbps version from the server to drastically speed up network transfer and librosa decoding
        stream_url = client.get_stream_url(track.id, max_bit_rate=64)
        
        # Download the track to a temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix=".audio")
        os.close(temp_fd)
    
        try:
            logger.info(f"Downloading track {track.id} from Navidrome...")
            response = requests.get(stream_url, stream=True, timeout=30)
            response.raise_for_status()
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            # Analyze the downloaded file
            features = extract_acoustic_features(temp_path)
            
            # Save updates
            track.acoustic_embedding = features["embedding"]
            track.key = features["key"]
            track.energy = features["energy"]
            # Update BPM if not already set by mutagen tags
            if not track.bpm:
                track.bpm = features["bpm"]
                
            track.acoustic_status = 'completed'
            track.acoustic_error = None
            db.session.commit()
            
            logger.info(f"Successfully analyzed: {track.title} (Key: {track.key}, Energy: {track.energy:.2f})")
            return True
        except Exception as e:
            error_msg = f"Analysis pipeline failed: {str(e)}"
            logger.error(error_msg)
            track.acoustic_status = 'failed'
            track.acoustic_error = error_msg
            db.session.commit()
            return False
        finally:
            # Always clean up the temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_err:
                    logger.error(f"Failed to delete temp file {temp_path}: {cleanup_err}")

def run_worker_loop():
    logger.info("Orbit acoustic analysis worker started successfully with Multi-Threading.")
    
    # Since the container is restricted to 1 CPU core and librosa is highly CPU-bound,
    # multithreading causes massive GIL contention and thrashing. Processing 1 at a time is much faster.
    max_workers = 1
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while True:
            try:
                with app.app_context():
                    # Fetch next pending tracks (up to max_workers)
                    pending_tracks = Track.query.filter_by(acoustic_status='pending').limit(max_workers).all()
                    
                    if not pending_tracks:
                        # No pending tracks, sleep and wait
                        time.sleep(5)
                        continue
                        
                    # Mark all fetched tracks as 'processing' immediately to lock them
                    track_ids = []
                    for track in pending_tracks:
                        track.acoustic_status = 'processing'
                        track_ids.append(track.id)
                    db.session.commit()
                
                # Submit them to the thread pool and wait for the batch to finish
                futures = [executor.submit(process_single_track, tid) for tid in track_ids]
                concurrent.futures.wait(futures)
                
            except Exception as e:
                logger.error(f"Worker loop exception: {str(e)}")
                time.sleep(10)

if __name__ == "__main__":
    run_worker_loop()
