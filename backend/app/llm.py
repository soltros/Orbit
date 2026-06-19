import os
import json
import random
import time
from flask import current_app
from openai import OpenAI
from anthropic import Anthropic
from app.models import Track, Genre, InteractionHistory

class LLMClient:
    def __init__(self):
        self.provider = current_app.config.get("LLM_PROVIDER", "openai").lower()
        self.openai_key = current_app.config.get("OPENAI_API_KEY")
        self.anthropic_key = current_app.config.get("ANTHROPIC_API_KEY")
        
        self.client = None
        if self.provider == "openai" and self.openai_key:
            self.client = OpenAI(api_key=self.openai_key)
        elif self.provider == "anthropic" and self.anthropic_key:
            self.client = Anthropic(api_key=self.anthropic_key)

    def _call_llm_with_retry(self, system_prompt, user_prompt, max_retries=3, response_format_json=False):
        """Helper to call LLM with simple exponential backoff retry logic."""
        if not self.client:
            raise Exception(f"LLM Client for provider '{self.provider}' is not configured. Missing API key.")
            
        retries = 0
        backoff = 1.5
        
        while retries < max_retries:
            try:
                if self.provider == "openai":
                    # Configure JSON mode if requested
                    extra_args = {}
                    if response_format_json:
                        extra_args["response_format"] = {"type": "json_object"}
                        
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini", # Cost-effective & smart
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        **extra_args
                    )
                    return response.choices[0].message.content
                    
                elif self.provider == "anthropic":
                    # Anthropic uses messages API
                    response = self.client.messages.create(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=2000,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7
                    )
                    return response.content[0].text
                    
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    raise Exception(f"LLM Call failed after {max_retries} attempts: {str(e)}")
                time.sleep(backoff ** retries)

    def generate_profile(self, user_history_summary, library_stats_summary):
        """
        Generates a musical taste profile describing user's mood and preference tendencies.
        """
        system_prompt = (
            "You are a music analytics AI. Your goal is to synthesize a detailed musical taste persona "
            "based on the user's history of liked songs, skipped songs, and general library stats. "
            "Describe their musical identity, preferences (genres, BPM range, mood, energy levels), "
            "and suggest key themes that they enjoy. Respond in plain Markdown format."
        )
        
        user_prompt = f"""
Here is the user's listening history:
{json.dumps(user_history_summary, indent=2)}

Here are some stats about their library:
{json.dumps(library_stats_summary, indent=2)}

Please generate a structured, comprehensive music profile detailing:
1. Primary musical interests and styles.
2. Current listening mood and vibe.
3. Skip patterns (what elements they avoid, e.g. high BPM, specific artists).
4. Audio features they gravitate towards (e.g. tempo/BPM preferences, genres).
"""
        return self._call_llm_with_retry(system_prompt, user_prompt, response_format_json=False)

    def generate_recommendations(self, user_profile, listening_history, candidate_tracks, count=5):
        """
        Given the user profile, history, and a set of candidate tracks, picks 'count' tracks to queue.
        Returns a list of dicts with track_id and why_queued explanation.
        """
        if not candidate_tracks:
            return []
            
        system_prompt = (
            "You are a personalized radio DJ. Your job is to curate a continuous rolling playlist queue "
            "for a user. You will be provided with a user taste profile, recent history (including plays "
            "and skips to avoid duplicates or unwanted tracks), and a strict list of candidate tracks "
            "from their library. You must select the next tracks ONLY from the candidate list provided. "
            "Do NOT hallucinate or recommend tracks not in the candidates list.\n\n"
            "Respond in a strict JSON format:\n"
            "{\n"
            "  \"recommendations\": [\n"
            "    {\n"
            "      \"track_id\": \"id_from_candidates\",\n"
            "      \"why_queued\": \"A short, friendly sentence explaining how this song continues the flow, e.g. 'Matching your energy with an upbeat 120 BPM deep house groove.'\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        
        # Prepare candidates list for LLM context
        candidates_clean = []
        for track in candidate_tracks:
            candidates_clean.append({
                "id": track.id,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "bpm": track.bpm,
                "genres": [g.name for g in track.genres] if hasattr(track, 'genres') else []
            })
            
        user_prompt = f"""
User Profile:
{user_profile}

Recent Listening History (last plays, skips, and likes):
{json.dumps(listening_history, indent=2)}

Candidate Tracks (Select exactly {count} tracks from this list):
{json.dumps(candidates_clean, indent=2)}

Output JSON containing exactly {count} recommended tracks from the Candidates list, along with explanations.
"""
        
        # Add helper instruction for Anthropic to return pure JSON
        if self.provider == "anthropic":
            user_prompt += "\nRespond ONLY with the JSON object. Do not include markdown code block syntax (like ```json) or introductory/concluding text."
            
        response_text = self._call_llm_with_retry(
            system_prompt, 
            user_prompt, 
            response_format_json=(self.provider == "openai")
        )
        
        # Parse JSON response
        try:
            # Clean potential markdown wrappers
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
                
            data = json.loads(cleaned)
            return data.get("recommendations", [])[:count]
        except Exception as e:
            # Fallback parsing or simple selection if LLM returned malformed JSON
            current_app.logger.error(f"Failed to parse LLM recommendations JSON: {str(e)}. Raw response: {response_text}")
            
            # Simple fallback: choose random candidate tracks
            fallback_tracks = random.sample(candidate_tracks, min(count, len(candidate_tracks)))
            return [
                {
                    "track_id": track.id,
                    "why_queued": "Serendipitous choice to keep the music flowing."
                } for track in fallback_tracks
            ]
