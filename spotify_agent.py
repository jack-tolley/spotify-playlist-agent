"""
Spotify Playlist Creator Agent
Creates custom Spotify playlists based on text prompts using the Spotify Web API.
"""

import os
import json
import time
import base64
import random
import re
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import urlencode
from threading import Thread

import requests
import yaml
from flask import Flask, request, redirect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
SCOPES = 'playlist-modify-public playlist-modify-private user-read-private user-read-email ugc-image-upload'
TOKEN_FILE = 'spotify_tokens.json'

# API endpoints
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE = 'https://api.spotify.com/v1'

# Flask app for OAuth callback
app = Flask(__name__)
auth_code = None

# Default config path
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')


class ConfigManager:
    """Manages configuration for the Spotify Playlist Agent."""

    def __init__(self, config_path=None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._config = self._load_config()
        self._modified = False

    def _load_config(self):
        """Load configuration from YAML file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except (yaml.YAMLError, IOError) as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
        return self._get_default_config()

    def _get_default_config(self):
        """Return default configuration if no config file exists."""
        return {
            'defaults': {
                'tracks_per_artist': 5,
                'target_track_count': 25,
                'creativity': 0.4,
                'arc_type': 'journey',
                'playlist_public': False,
                'max_tracks_per_artist': 3,
                'market': 'US',
            },
            'emotional_mappings': {},
            'artist_mappings': {},
            'context_search_terms': {},
            'arc_types': {},
        }

    def save(self):
        """Save configuration back to YAML file."""
        if self._modified:
            try:
                with open(self.config_path, 'w') as f:
                    yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
                self._modified = False
                return True
            except IOError as e:
                print(f"Warning: Could not save config to {self.config_path}: {e}")
                return False
        return True

    @property
    def defaults(self):
        """Get defaults section."""
        return self._config.get('defaults', {})

    @property
    def emotional_mappings(self):
        """Get emotional mappings."""
        return self._config.get('emotional_mappings', {})

    @property
    def artist_mappings(self):
        """Get artist mappings."""
        return self._config.get('artist_mappings', {})

    @property
    def context_search_terms(self):
        """Get context search terms."""
        return self._config.get('context_search_terms', {})

    def get_default(self, key, fallback=None):
        """Get a default value by key."""
        return self.defaults.get(key, fallback)

    def get_artist_id(self, artist_name):
        """Get cached Spotify ID for an artist."""
        mapping = self.artist_mappings.get(artist_name)
        if mapping:
            return mapping.get('spotify_id')
        return None

    def get_artist_exclude_ids(self, artist_name):
        """Get excluded artist IDs for disambiguation."""
        mapping = self.artist_mappings.get(artist_name)
        if mapping:
            return mapping.get('exclude_ids', [])
        return []

    def cache_artist_mapping(self, artist_name, spotify_id, region=None):
        """Cache an artist mapping for future use."""
        if 'artist_mappings' not in self._config:
            self._config['artist_mappings'] = {}

        self._config['artist_mappings'][artist_name] = {
            'spotify_id': spotify_id,
        }
        if region:
            self._config['artist_mappings'][artist_name]['region'] = region

        self._modified = True
        return True

    def get_emotional_mapping(self, emotion):
        """Get audio feature ranges for an emotion."""
        return self.emotional_mappings.get(emotion)

    def get_context_search_term(self, context):
        """Get search term for a context."""
        return self.context_search_terms.get(context)


class SpotifyPlaylistAgent:
    """Agent for creating Spotify playlists from text prompts."""

    def __init__(self, config_path=None):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.user_id = None
        self.config = ConfigManager(config_path)
        self._load_tokens()

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def _load_tokens(self):
        """Load tokens from file if they exist."""
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    expires_at_str = data.get('expires_at')
                    if expires_at_str:
                        self.expires_at = datetime.fromisoformat(expires_at_str)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_tokens(self):
        """Save tokens to file."""
        data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
        with open(TOKEN_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def _get_auth_header(self):
        """Get base64 encoded authorization header."""
        credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
        return base64.b64encode(credentials.encode()).decode()

    def get_authorization_url(self):
        """Generate the Spotify authorization URL."""
        params = {
            'response_type': 'code',
            'client_id': CLIENT_ID,
            'scope': SCOPES,
            'redirect_uri': REDIRECT_URI,
        }
        return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code):
        """Exchange authorization code for access and refresh tokens."""
        headers = {
            'Authorization': f'Basic {self._get_auth_header()}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }

        response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.refresh_token = token_data.get('refresh_token', self.refresh_token)
            expires_in = token_data.get('expires_in', 3600)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)
            self._save_tokens()
            return True
        else:
            print(f"Error exchanging code: {response.status_code} - {response.text}")
            return False

    def refresh_access_token(self):
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            return False

        headers = {
            'Authorization': f'Basic {self._get_auth_header()}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }

        response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            if 'refresh_token' in token_data:
                self.refresh_token = token_data['refresh_token']
            expires_in = token_data.get('expires_in', 3600)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)
            self._save_tokens()
            return True
        else:
            print(f"Error refreshing token: {response.status_code} - {response.text}")
            return False

    def ensure_valid_token(self):
        """Ensure we have a valid access token, refreshing if necessary."""
        if not self.access_token:
            return False

        if self.expires_at and datetime.now() >= self.expires_at - timedelta(minutes=5):
            return self.refresh_access_token()

        return True

    def is_authenticated(self):
        """Check if the agent is authenticated."""
        return self.access_token is not None and self.ensure_valid_token()

    def authenticate(self):
        """Start the OAuth authentication flow."""
        global auth_code
        auth_code = None

        if not CLIENT_ID or not CLIENT_SECRET:
            print("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env file")
            return False

        # Start Flask server in background with SSL
        import ssl
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cert_file = os.path.join(script_dir, 'cert.pem')
        key_file = os.path.join(script_dir, 'key.pem')

        def run_server():
            app.run(host='127.0.0.1', port=8888, debug=False, use_reloader=False,
                   ssl_context=(cert_file, key_file))

        server_thread = Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # Open browser for authorization
        auth_url = self.get_authorization_url()
        print(f"\nOpening browser for Spotify authorization...")
        print(f"If browser doesn't open, visit: {auth_url}\n")
        webbrowser.open(auth_url)

        # Wait for callback
        print("Waiting for authorization...")
        timeout = 120
        start_time = time.time()
        while auth_code is None and (time.time() - start_time) < timeout:
            time.sleep(0.5)

        if auth_code:
            if self.exchange_code_for_tokens(auth_code):
                print("Authentication successful!")
                return True
            else:
                print("Failed to exchange authorization code for tokens.")
                return False
        else:
            print("Authorization timed out.")
            return False

    # -------------------------------------------------------------------------
    # API Requests
    # -------------------------------------------------------------------------

    def _api_request(self, method, endpoint, data=None, params=None):
        """Make an authenticated API request with error handling."""
        if not self.ensure_valid_token():
            raise Exception("Not authenticated. Call authenticate() first.")

        url = f"{SPOTIFY_API_BASE}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params
        )

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 1))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return self._api_request(method, endpoint, data, params)

        if response.status_code >= 400:
            raise Exception(f"API Error {response.status_code}: {response.text}")

        if response.content:
            return response.json()
        return None

    def get_user_profile(self):
        """Get the current user's profile."""
        profile = self._api_request('GET', '/me')
        self.user_id = profile['id']
        return profile

    # -------------------------------------------------------------------------
    # Artist Search (ID-based)
    # -------------------------------------------------------------------------

    def find_artist_id(self, artist_name, auto_cache=True):
        """
        Find Spotify artist ID by name.

        Checks config cache first, then searches Spotify API.
        Optionally caches new mappings for future use.

        Args:
            artist_name: Artist name to search for
            auto_cache: Whether to cache newly found artist IDs

        Returns:
            Spotify artist ID string or None if not found
        """
        # Check config cache first
        cached_id = self.config.get_artist_id(artist_name)
        if cached_id:
            return cached_id

        # Search Spotify artist endpoint
        try:
            result = self._api_request('GET', '/search',
                                       params={'q': f'artist:"{artist_name}"',
                                               'type': 'artist',
                                               'limit': 5})
            artists = result.get('artists', {}).get('items', [])

            if not artists:
                return None

            # Find best match (exact name match preferred)
            best_match = None
            for artist in artists:
                if artist['name'].lower() == artist_name.lower():
                    best_match = artist
                    break

            # Fall back to first result if no exact match
            if not best_match:
                best_match = artists[0]

            artist_id = best_match['id']

            # Auto-cache for future use
            if auto_cache:
                self.config.cache_artist_mapping(artist_name, artist_id)
                self.config.save()

            return artist_id

        except Exception as e:
            print(f"Error searching for artist '{artist_name}': {e}")
            return None

    def get_artist_top_tracks(self, artist_id, market=None):
        """
        Get an artist's top tracks.

        Args:
            artist_id: Spotify artist ID
            market: ISO 3166-1 alpha-2 country code (defaults to config)

        Returns:
            List of track objects
        """
        market = market or self.config.get_default('market', 'US')

        try:
            result = self._api_request('GET', f'/artists/{artist_id}/top-tracks',
                                       params={'market': market})
            return result.get('tracks', [])
        except Exception as e:
            print(f"Error getting top tracks for artist {artist_id}: {e}")
            return []

    def get_artist_albums(self, artist_id, include_groups='album,single', limit=20):
        """
        Get an artist's albums.

        Args:
            artist_id: Spotify artist ID
            include_groups: Types to include (album, single, appears_on, compilation)
            limit: Maximum number of albums to return

        Returns:
            List of album objects
        """
        try:
            result = self._api_request('GET', f'/artists/{artist_id}/albums',
                                       params={'include_groups': include_groups,
                                               'limit': limit})
            return result.get('items', [])
        except Exception as e:
            print(f"Error getting albums for artist {artist_id}: {e}")
            return []

    def get_tracks_for_artist(self, artist_name, track_count=None, use_top_tracks=True):
        """
        Get tracks for an artist using ID-based search.

        This is the recommended method for lineup-based playlists.

        Args:
            artist_name: Artist name to search for
            track_count: Number of tracks to return (defaults to config)
            use_top_tracks: Whether to use top tracks endpoint (more reliable)

        Returns:
            List of track objects
        """
        track_count = track_count or self.config.get_default('tracks_per_artist', 5)

        # Find artist ID
        artist_id = self.find_artist_id(artist_name)
        if not artist_id:
            print(f"  Could not find artist: {artist_name}")
            return []

        if use_top_tracks:
            # Get top tracks (more reliable, pre-sorted by popularity)
            tracks = self.get_artist_top_tracks(artist_id)

            # If no tracks returned (e.g., invalid cached ID), try search fallback
            if not tracks:
                print(f"  No top tracks found for cached ID, trying search...")
                tracks = self.search_tracks(f'artist:"{artist_name}"', limit=50)
                # Filter to current artist and sort by popularity
                if tracks:
                    filtered = []
                    for t in tracks:
                        # Accept tracks where artist name matches (case-insensitive)
                        for a in t.get('artists', []):
                            if a['name'].lower() == artist_name.lower():
                                filtered.append(t)
                                break
                    filtered.sort(key=lambda t: t.get('popularity', 0), reverse=True)
                    tracks = filtered

            return tracks[:track_count]
        else:
            # Fallback: search for tracks by artist
            tracks = self.search_tracks(f'artist:"{artist_name}"', limit=50)
            # Filter to ensure we have the right artist
            filtered = [t for t in tracks
                        if any(a['id'] == artist_id for a in t.get('artists', []))]
            # Sort by popularity
            filtered.sort(key=lambda t: t.get('popularity', 0), reverse=True)
            return filtered[:track_count]

    # -------------------------------------------------------------------------
    # Prompt Analysis
    # -------------------------------------------------------------------------

    def analyze_prompt(self, prompt):
        """
        Analyze a text prompt to extract musical criteria.
        Returns a dictionary with genres, moods, artists, decades, and context.
        """
        prompt_lower = prompt.lower()

        # Genre mappings
        genres = []
        genre_keywords = {
            'rock': ['rock', 'alternative', 'grunge', 'punk'],
            'pop': ['pop', 'top 40', 'mainstream'],
            'jazz': ['jazz', 'bebop', 'swing'],
            'classical': ['classical', 'orchestra', 'symphony', 'piano'],
            'electronic': ['electronic', 'edm', 'techno', 'house', 'trance', 'dubstep'],
            'hip-hop': ['hip hop', 'hip-hop', 'rap', 'trap'],
            'r-n-b': ['r&b', 'rnb', 'soul', 'neo-soul'],
            'country': ['country', 'bluegrass', 'folk'],
            'indie': ['indie', 'independent', 'alt'],
            'metal': ['metal', 'heavy metal', 'death metal', 'black metal'],
            'blues': ['blues', 'delta blues'],
            'reggae': ['reggae', 'ska', 'dub'],
            'latin': ['latin', 'salsa', 'bachata', 'reggaeton'],
            'ambient': ['ambient', 'atmospheric', 'drone'],
            'funk': ['funk', 'funky', 'groove'],
        }

        for genre, keywords in genre_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                genres.append(genre)

        # Mood detection
        moods = []
        mood_keywords = {
            'happy': ['happy', 'upbeat', 'cheerful', 'joyful', 'fun'],
            'sad': ['sad', 'melancholic', 'depressing', 'heartbreak', 'emotional'],
            'energetic': ['energetic', 'intense', 'powerful', 'pumped', 'hype'],
            'chill': ['chill', 'relaxing', 'calm', 'mellow', 'peaceful', 'laid back'],
            'romantic': ['romantic', 'love', 'sensual', 'intimate'],
            'angry': ['angry', 'aggressive', 'rage', 'intense'],
            'focus': ['focus', 'concentration', 'study', 'work', 'productive'],
            'party': ['party', 'dance', 'club', 'celebration'],
        }

        for mood, keywords in mood_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                moods.append(mood)

        # Decade detection
        decades = []
        decade_patterns = {
            '1960s': ['60s', '1960', 'sixties'],
            '1970s': ['70s', '1970', 'seventies'],
            '1980s': ['80s', '1980', 'eighties'],
            '1990s': ['90s', '1990', 'nineties'],
            '2000s': ['2000s', '2000', 'y2k'],
            '2010s': ['2010s', '2010'],
            '2020s': ['2020s', '2020', 'recent', 'new', 'modern', 'current'],
        }

        for decade, patterns in decade_patterns.items():
            if any(p in prompt_lower for p in patterns):
                decades.append(decade)

        # Context detection
        contexts = []
        context_keywords = {
            'workout': ['workout', 'exercise', 'gym', 'running', 'training'],
            'study': ['study', 'studying', 'homework', 'reading', 'concentration'],
            'sleep': ['sleep', 'sleeping', 'bedtime', 'lullaby'],
            'party': ['party', 'parties', 'celebration', 'dance'],
            'road_trip': ['road trip', 'driving', 'car', 'travel'],
            'dinner': ['dinner', 'dining', 'restaurant', 'cooking'],
            'coffee_shop': ['coffee', 'cafe', 'coffeehouse'],
            'morning': ['morning', 'wake up', 'sunrise'],
        }

        for context, keywords in context_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                contexts.append(context)

        # Extract artist mentions (basic pattern matching)
        artists = []
        artist_indicators = ['by ', 'like ', 'similar to ', 'artist:', 'artists:']
        for indicator in artist_indicators:
            if indicator in prompt_lower:
                idx = prompt_lower.index(indicator) + len(indicator)
                remaining = prompt[idx:].strip()
                # Take the next few words as potential artist name
                artist_words = remaining.split()[:3]
                if artist_words:
                    artists.append(' '.join(artist_words).rstrip(',').rstrip('.'))

        # Determine audio feature targets based on mood/context
        audio_features = self._get_target_audio_features(moods, contexts)

        return {
            'genres': genres or ['pop'],  # Default to pop if no genre detected
            'moods': moods,
            'decades': decades,
            'contexts': contexts,
            'artists': artists,
            'audio_features': audio_features,
            'original_prompt': prompt
        }

    def _get_target_audio_features(self, moods, contexts):
        """Determine target audio features based on moods and contexts."""
        features = {
            'min_energy': 0.0,
            'max_energy': 1.0,
            'min_valence': 0.0,
            'max_valence': 1.0,
            'min_tempo': 0,
            'max_tempo': 250,
            'min_danceability': 0.0,
            'max_danceability': 1.0,
        }

        # Adjust based on moods
        if 'happy' in moods:
            features['min_valence'] = 0.5
        if 'sad' in moods:
            features['max_valence'] = 0.4
        if 'energetic' in moods:
            features['min_energy'] = 0.7
            features['min_tempo'] = 120
        if 'chill' in moods:
            features['max_energy'] = 0.5
            features['max_tempo'] = 110
        if 'party' in moods:
            features['min_danceability'] = 0.6
            features['min_energy'] = 0.6

        # Adjust based on contexts
        if 'workout' in contexts:
            features['min_energy'] = 0.7
            features['min_tempo'] = 120
        if 'study' in contexts or 'focus' in moods:
            features['max_energy'] = 0.5
            features['min_tempo'] = 60
            features['max_tempo'] = 120
        if 'sleep' in contexts:
            features['max_energy'] = 0.3
            features['max_tempo'] = 80
        if 'coffee_shop' in contexts:
            features['max_energy'] = 0.6
            features['min_valence'] = 0.3

        return features

    # -------------------------------------------------------------------------
    # Emotional Intelligence
    # -------------------------------------------------------------------------

    def analyze_emotional_depth(self, prompt):
        """
        Analyze emotional nuance, intensity, and compound emotions.
        Returns rich emotional analysis beyond simple keyword matching.
        """
        prompt_lower = prompt.lower()

        # Intensity modifiers
        high_intensity = ['extremely', 'deeply', 'intensely', 'very', 'incredibly',
                          'overwhelmingly', 'devastated', 'ecstatic', 'furious',
                          'heartbroken', 'euphoric', 'desperate']
        low_intensity = ['slightly', 'a bit', 'somewhat', 'gently', 'mildly',
                         'quietly', 'softly', 'subtly', 'hint of']

        intensity = 0.5  # Default medium
        for word in high_intensity:
            if word in prompt_lower:
                intensity = min(1.0, intensity + 0.2)
        for word in low_intensity:
            if word in prompt_lower:
                intensity = max(0.0, intensity - 0.2)

        # Emotion vocabulary with valence and energy mappings
        emotion_map = {
            # Primary emotions
            'joy': {'valence': 0.9, 'energy': 0.7, 'category': 'positive'},
            'happy': {'valence': 0.8, 'energy': 0.6, 'category': 'positive'},
            'ecstatic': {'valence': 1.0, 'energy': 0.9, 'category': 'positive'},
            'content': {'valence': 0.7, 'energy': 0.4, 'category': 'positive'},
            'peaceful': {'valence': 0.6, 'energy': 0.2, 'category': 'positive'},
            'hopeful': {'valence': 0.7, 'energy': 0.5, 'category': 'positive'},
            'triumphant': {'valence': 0.9, 'energy': 0.9, 'category': 'positive'},

            'sad': {'valence': 0.2, 'energy': 0.3, 'category': 'negative'},
            'melancholy': {'valence': 0.3, 'energy': 0.3, 'category': 'negative'},
            'melancholic': {'valence': 0.3, 'energy': 0.3, 'category': 'negative'},
            'heartbroken': {'valence': 0.1, 'energy': 0.4, 'category': 'negative'},
            'devastated': {'valence': 0.0, 'energy': 0.5, 'category': 'negative'},
            'lonely': {'valence': 0.2, 'energy': 0.2, 'category': 'negative'},
            'nostalgic': {'valence': 0.4, 'energy': 0.3, 'category': 'mixed'},
            'bittersweet': {'valence': 0.4, 'energy': 0.4, 'category': 'mixed'},
            'wistful': {'valence': 0.4, 'energy': 0.3, 'category': 'mixed'},

            'angry': {'valence': 0.2, 'energy': 0.9, 'category': 'negative'},
            'furious': {'valence': 0.1, 'energy': 1.0, 'category': 'negative'},
            'frustrated': {'valence': 0.3, 'energy': 0.7, 'category': 'negative'},
            'rage': {'valence': 0.1, 'energy': 1.0, 'category': 'negative'},

            'anxious': {'valence': 0.3, 'energy': 0.6, 'category': 'negative'},
            'tense': {'valence': 0.3, 'energy': 0.7, 'category': 'negative'},
            'restless': {'valence': 0.4, 'energy': 0.7, 'category': 'mixed'},

            'calm': {'valence': 0.6, 'energy': 0.2, 'category': 'positive'},
            'relaxed': {'valence': 0.6, 'energy': 0.2, 'category': 'positive'},
            'serene': {'valence': 0.7, 'energy': 0.1, 'category': 'positive'},
            'dreamy': {'valence': 0.6, 'energy': 0.3, 'category': 'positive'},

            'romantic': {'valence': 0.7, 'energy': 0.4, 'category': 'positive'},
            'sensual': {'valence': 0.6, 'energy': 0.5, 'category': 'positive'},
            'passionate': {'valence': 0.7, 'energy': 0.7, 'category': 'positive'},
            'longing': {'valence': 0.4, 'energy': 0.4, 'category': 'mixed'},

            'empowered': {'valence': 0.8, 'energy': 0.8, 'category': 'positive'},
            'confident': {'valence': 0.8, 'energy': 0.7, 'category': 'positive'},
            'rebellious': {'valence': 0.5, 'energy': 0.8, 'category': 'mixed'},
            'defiant': {'valence': 0.5, 'energy': 0.8, 'category': 'mixed'},

            'reflective': {'valence': 0.5, 'energy': 0.3, 'category': 'neutral'},
            'introspective': {'valence': 0.5, 'energy': 0.2, 'category': 'neutral'},
            'contemplative': {'valence': 0.5, 'energy': 0.2, 'category': 'neutral'},
            'thoughtful': {'valence': 0.5, 'energy': 0.3, 'category': 'neutral'},
        }

        # Detect emotions
        detected_emotions = []
        for emotion, attrs in emotion_map.items():
            if emotion in prompt_lower:
                detected_emotions.append({
                    'emotion': emotion,
                    **attrs,
                    'intensity': intensity
                })

        # Detect negation ("not sad", "without melancholy")
        negation_patterns = [
            r"not\s+(\w+)", r"without\s+(\w+)", r"no\s+(\w+)",
            r"never\s+(\w+)", r"anything but\s+(\w+)"
        ]
        excluded_emotions = []
        for pattern in negation_patterns:
            matches = re.findall(pattern, prompt_lower)
            excluded_emotions.extend(matches)

        # Detect emotional arc ("start slow, build to peak")
        arc_patterns = {
            'build': r"(build|crescendo|rise|grow|escalate)",
            'fade': r"(fade|wind down|slow down|decrease|calm)",
            'peak': r"(peak|climax|apex|high point)",
            'journey': r"(journey|arc|progression|evolve)",
        }
        emotional_arc = None
        for arc_type, pattern in arc_patterns.items():
            if re.search(pattern, prompt_lower):
                emotional_arc = arc_type

        # Calculate weighted valence and energy targets
        if detected_emotions:
            avg_valence = sum(e['valence'] * e['intensity'] for e in detected_emotions) / len(detected_emotions)
            avg_energy = sum(e['energy'] * e['intensity'] for e in detected_emotions) / len(detected_emotions)
        else:
            avg_valence = 0.5
            avg_energy = 0.5

        return {
            'emotions': detected_emotions,
            'primary_emotion': detected_emotions[0] if detected_emotions else None,
            'intensity': intensity,
            'excluded_emotions': excluded_emotions,
            'emotional_arc': emotional_arc,
            'target_valence': avg_valence,
            'target_energy': avg_energy,
        }

    def enrich_prompt(self, prompt):
        """
        Pre-process and enrich prompt with semantic understanding.
        Handles comparisons, negations, and complex requests.
        """
        enriched = {
            'original': prompt,
            'comparisons': [],
            'exclusions': [],
            'temporal_modifiers': [],
            'reference_artists': [],
        }

        prompt_lower = prompt.lower()

        # Detect "like X but Y" patterns
        like_but_pattern = r"like\s+([^,]+?)\s+but\s+(\w+)"
        matches = re.findall(like_but_pattern, prompt_lower)
        for artist, modifier in matches:
            enriched['comparisons'].append({
                'reference': artist.strip(),
                'modifier': modifier.strip()
            })

        # Detect "similar to X" patterns
        similar_pattern = r"similar to\s+([^,\.]+)"
        matches = re.findall(similar_pattern, prompt_lower)
        enriched['reference_artists'].extend([m.strip() for m in matches])

        # Detect exclusions ("but not X", "no X", "without X")
        exclusion_patterns = [
            r"but not\s+([^,\.]+)",
            r"without\s+([^,\.]+)",
            r"no\s+(cheesy|generic|mainstream|overplayed|popular)"
        ]
        for pattern in exclusion_patterns:
            matches = re.findall(pattern, prompt_lower)
            enriched['exclusions'].extend([m.strip() for m in matches])

        # Detect temporal modifiers
        temporal_patterns = {
            'vintage_modern': r"(vintage|classic|old).*(modern|new|contemporary|remixed)",
            'nostalgic': r"nostalgi",
            'timeless': r"timeless",
            'fresh': r"(fresh|new|current|latest)",
        }
        for modifier, pattern in temporal_patterns.items():
            if re.search(pattern, prompt_lower):
                enriched['temporal_modifiers'].append(modifier)

        return enriched

    # -------------------------------------------------------------------------
    # Creative Variability
    # -------------------------------------------------------------------------

    def add_creative_variability(self, scored_tracks, creativity=0.3, discovery_ratio=0.15):
        """
        Add controlled randomness to track selection.

        Args:
            scored_tracks: List of (track, score) tuples
            creativity: 0.0 = deterministic, 1.0 = very random
            discovery_ratio: Proportion of lesser-known tracks to include
        """
        if not scored_tracks:
            return scored_tracks

        # Separate into tiers
        sorted_tracks = sorted(scored_tracks, key=lambda x: x[1], reverse=True)
        total = len(sorted_tracks)

        top_tier = sorted_tracks[:int(total * 0.3)]      # Top 30%
        mid_tier = sorted_tracks[int(total * 0.3):int(total * 0.7)]  # Middle 40%
        discovery_tier = sorted_tracks[int(total * 0.7):]  # Bottom 30% (hidden gems)

        # Shuffle within tiers based on creativity
        if creativity > 0:
            random.shuffle(top_tier)
            random.shuffle(mid_tier)
            random.shuffle(discovery_tier)

        # Apply score jitter based on creativity
        jittered = []
        for track, score in sorted_tracks:
            jitter = random.uniform(-creativity * 0.3, creativity * 0.3)
            jittered.append((track, score + jitter))

        # Mix in discovery tracks
        discovery_count = int(len(scored_tracks) * discovery_ratio)
        discovery_picks = discovery_tier[:discovery_count] if discovery_tier else []

        return jittered, discovery_picks

    # -------------------------------------------------------------------------
    # Playlist Flow & Arc
    # -------------------------------------------------------------------------

    def sequence_playlist(self, tracks, features_map, arc_type='balanced'):
        """
        Sequence tracks for optimal flow and energy arc.

        Arc types:
            - 'balanced': Smooth energy throughout
            - 'build': Start low, peak in middle, maintain
            - 'early_build': Start low, build to high by midpoint, maintain high
            - 'journey': Start mid, build to peak, wind down
            - 'energize': Start strong, maintain high energy
            - 'wind_down': Start high, gradually decrease
        """
        if len(tracks) < 3:
            return tracks

        # Get features for each track
        track_data = []
        for track in tracks:
            features = features_map.get(track['id'], {})
            track_data.append({
                'track': track,
                'energy': features.get('energy', 0.5),
                'tempo': features.get('tempo', 120),
                'valence': features.get('valence', 0.5),
                'danceability': features.get('danceability', 0.5),
            })

        n = len(track_data)

        # Define target energy curve based on arc type
        if arc_type == 'build':
            target_curve = [0.3 + (0.7 * i / n) for i in range(n)]
        elif arc_type == 'early_build':
            # 0-50%: Build 0.3 -> 0.8
            # 50-100%: Maintain 0.8 -> 0.9
            target_curve = []
            mid_point = int(n / 2)
            for i in range(n):
                if i < mid_point:
                    # Ramp up
                    progress = i / mid_point if mid_point > 0 else 0
                    target_curve.append(0.3 + (0.5 * progress))
                else:
                    # Maintain high
                    progress = (i - mid_point) / (n - mid_point) if (n - mid_point) > 0 else 0
                    target_curve.append(0.8 + (0.1 * progress))
        elif arc_type == 'journey':
            # Bell curve: start mid, peak at 60%, wind down
            target_curve = []
            for i in range(n):
                pos = i / n
                if pos < 0.6:
                    target_curve.append(0.4 + (0.6 * pos / 0.6))
                else:
                    target_curve.append(1.0 - (0.5 * (pos - 0.6) / 0.4))
        elif arc_type == 'energize':
            target_curve = [0.7 + (0.3 * min(i / 3, 1)) for i in range(n)]
        elif arc_type == 'wind_down':
            target_curve = [0.8 - (0.5 * i / n) for i in range(n)]
        else:  # balanced
            target_curve = [0.5] * n

        # Sort tracks to match target curve using greedy assignment
        sequenced = []
        remaining = track_data.copy()

        for target_energy in target_curve:
            if not remaining:
                break

            # Find track closest to target energy
            best_match = min(remaining, key=lambda t: abs(t['energy'] - target_energy))
            sequenced.append(best_match['track'])
            remaining.remove(best_match)

        # Add any remaining tracks
        sequenced.extend([t['track'] for t in remaining])

        # Post-process: avoid same artist back-to-back
        sequenced = self._space_artists(sequenced)

        return sequenced

    def _space_artists(self, tracks):
        """Ensure same artist doesn't appear back-to-back."""
        if len(tracks) < 3:
            return tracks

        result = [tracks[0]]
        remaining = tracks[1:]

        while remaining:
            last_artist = result[-1]['artists'][0]['id'] if result[-1].get('artists') else None

            # Find next track with different artist
            next_track = None
            for i, track in enumerate(remaining):
                track_artist = track['artists'][0]['id'] if track.get('artists') else None
                if track_artist != last_artist:
                    next_track = remaining.pop(i)
                    break

            if next_track is None:
                # No different artist available, just take first
                next_track = remaining.pop(0)

            result.append(next_track)

        return result

    # -------------------------------------------------------------------------
    # Track Search and Curation
    # -------------------------------------------------------------------------

    def build_search_queries(self, analysis):
        """Build Spotify search queries from prompt analysis."""
        queries = []

        # Genre-based queries
        for genre in analysis['genres'][:3]:  # Limit to top 3 genres
            query = f'genre:{genre}'

            # Add decade filter if specified
            if analysis['decades']:
                decade = analysis['decades'][0]
                year_start = int(decade[:4])
                year_end = year_start + 9
                query += f' year:{year_start}-{year_end}'

            queries.append(query)

        # Artist-based queries
        for artist in analysis['artists']:
            queries.append(f'artist:{artist}')

        # Mood-based queries (use mood as search term)
        for mood in analysis['moods'][:2]:
            queries.append(mood)

        # Context-based queries
        context_terms = {
            'workout': 'workout energy',
            'study': 'focus instrumental',
            'sleep': 'sleep ambient',
            'party': 'party dance hits',
            'road_trip': 'road trip classics',
            'dinner': 'dinner jazz',
            'coffee_shop': 'acoustic chill',
            'morning': 'morning feel good',
        }
        for context in analysis['contexts']:
            if context in context_terms:
                queries.append(context_terms[context])

        # If no specific queries, use original prompt keywords
        if not queries:
            queries.append(analysis['original_prompt'])

        return queries

    def search_tracks(self, query, limit=50):
        """Search for tracks using a query string."""
        params = {
            'q': query,
            'type': 'track',
            'limit': min(limit, 50)
        }

        result = self._api_request('GET', '/search', params=params)
        return result.get('tracks', {}).get('items', [])

    def get_audio_features(self, track_ids):
        """Get audio features for a list of track IDs."""
        if not track_ids:
            return []

        # API allows max 100 IDs per request
        all_features = []
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i+100]
            ids_param = ','.join(batch)
            result = self._api_request('GET', f'/audio-features?ids={ids_param}')
            if result and 'audio_features' in result:
                all_features.extend(result['audio_features'])

        return all_features

    def curate_tracks(self, tracks, analysis, target_count=25, creativity=0.3,
                       arc_type=None, use_emotional_analysis=True):
        """
        Curate and filter tracks based on analysis criteria with enhanced intelligence.

        Args:
            tracks: List of track objects from search
            analysis: Dict from analyze_prompt()
            target_count: Number of tracks to select
            creativity: 0.0-1.0, controls randomness and discovery
            arc_type: Playlist flow type ('build', 'journey', 'wind_down', etc.)
            use_emotional_analysis: Whether to use deep emotional scoring

        Returns:
            List of curated and sequenced tracks
        """
        if not tracks:
            return []

        # Remove duplicates by track ID
        seen_ids = set()
        unique_tracks = []
        for track in tracks:
            if track and track['id'] not in seen_ids:
                seen_ids.add(track['id'])
                unique_tracks.append(track)

        # Get audio features for filtering
        track_ids = [t['id'] for t in unique_tracks]
        audio_features = self.get_audio_features(track_ids)

        # Create a mapping of track ID to features
        features_map = {}
        for features in audio_features:
            if features:
                features_map[features['id']] = features

        # Get emotional analysis if available
        emotional_analysis = analysis.get('emotional_analysis', {})
        target_valence = emotional_analysis.get('target_valence', 0.5)
        target_energy = emotional_analysis.get('target_energy', 0.5)
        emotional_intensity = emotional_analysis.get('intensity', 0.5)

        # Score and filter tracks
        scored_tracks = []
        target_features = analysis['audio_features']

        for track in unique_tracks:
            score = 0
            features = features_map.get(track['id'])

            # Base score from popularity (0-100 -> 0-1)
            # Weight popularity less for high creativity
            popularity_weight = 0.3 * (1 - creativity * 0.5)
            score += track.get('popularity', 50) / 100 * popularity_weight

            if features:
                energy = features.get('energy', 0.5)
                valence = features.get('valence', 0.5)
                tempo = features.get('tempo', 120)
                dance = features.get('danceability', 0.5)

                # Standard range scoring
                if target_features['min_energy'] <= energy <= target_features['max_energy']:
                    score += 0.15

                if target_features['min_valence'] <= valence <= target_features['max_valence']:
                    score += 0.15

                if target_features['min_tempo'] <= tempo <= target_features['max_tempo']:
                    score += 0.1

                if target_features['min_danceability'] <= dance <= target_features['max_danceability']:
                    score += 0.1

                # Enhanced emotional scoring (proximity to target)
                if use_emotional_analysis and emotional_analysis:
                    # Score based on closeness to emotional targets
                    valence_diff = 1 - abs(valence - target_valence)
                    energy_diff = 1 - abs(energy - target_energy)

                    # Weight by intensity - high intensity = stricter matching
                    emotional_score = (valence_diff + energy_diff) / 2
                    score += emotional_score * 0.25 * emotional_intensity

            scored_tracks.append((track, score, features))

        # Apply creative variability
        if creativity > 0:
            jittered_tracks, discovery_picks = self.add_creative_variability(
                [(t, s) for t, s, f in scored_tracks],
                creativity=creativity,
                discovery_ratio=0.15 * creativity
            )
            scored_tracks = [(t, s, features_map.get(t['id'], {})) for t, s in jittered_tracks]

        # Sort by score
        scored_tracks.sort(key=lambda x: x[1], reverse=True)

        # Add diversity by limiting tracks per artist
        final_tracks = []
        artist_counts = {}
        max_per_artist = 3

        for track, score, features in scored_tracks:
            if len(final_tracks) >= target_count:
                break

            # Get primary artist
            artist_id = track['artists'][0]['id'] if track.get('artists') else None

            if artist_id:
                if artist_counts.get(artist_id, 0) >= max_per_artist:
                    continue
                artist_counts[artist_id] = artist_counts.get(artist_id, 0) + 1

            final_tracks.append(track)

        # Determine arc type from emotional analysis if not specified
        if arc_type is None:
            arc_type = emotional_analysis.get('emotional_arc', 'balanced')
            # Map emotional arcs to playlist arcs
            arc_mapping = {
                'build': 'build',
                'fade': 'wind_down',
                'peak': 'journey',
                'journey': 'journey',
            }
            arc_type = arc_mapping.get(arc_type, 'balanced')

        # Sequence playlist for optimal flow
        if len(final_tracks) >= 3:
            final_tracks = self.sequence_playlist(final_tracks, features_map, arc_type)

        return final_tracks

    def curate_tracks_intelligent(self, tracks, prompt, target_count=25, creativity=0.3):
        """
        High-level intelligent curation combining all analysis methods.

        Args:
            tracks: List of track objects
            prompt: Original user prompt string
            target_count: Number of tracks to select
            creativity: 0.0-1.0 creativity level

        Returns:
            Dict with curated tracks and analysis metadata
        """
        # Full analysis pipeline
        basic_analysis = self.analyze_prompt(prompt)
        emotional_analysis = self.analyze_emotional_depth(prompt)
        enriched_prompt = self.enrich_prompt(prompt)

        # Merge analyses
        full_analysis = {
            **basic_analysis,
            'emotional_analysis': emotional_analysis,
            'enriched_prompt': enriched_prompt,
        }

        # Curate with all intelligence
        curated = self.curate_tracks(
            tracks,
            full_analysis,
            target_count=target_count,
            creativity=creativity,
            arc_type=emotional_analysis.get('emotional_arc'),
            use_emotional_analysis=True
        )

        return {
            'tracks': curated,
            'analysis': full_analysis,
            'creativity_level': creativity,
            'track_count': len(curated),
        }

    # -------------------------------------------------------------------------
    # Playlist Creation
    # -------------------------------------------------------------------------

    def create_playlist(self, name, description='', public=False):
        """Create a new playlist."""
        if not self.user_id:
            self.get_user_profile()

        data = {
            'name': name,
            'description': description,
            'public': public
        }

        result = self._api_request('POST', f'/users/{self.user_id}/playlists', data=data)
        return result

    def add_tracks_to_playlist(self, playlist_id, track_uris):
        """Add tracks to a playlist."""
        # API allows max 100 tracks per request
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            data = {'uris': batch}
            self._api_request('POST', f'/playlists/{playlist_id}/tracks', data=data)

    def get_playlist_tracks(self, playlist_id):
        """Get all tracks from a playlist."""
        tracks = []
        offset = 0
        limit = 100

        while True:
            result = self._api_request('GET', f'/playlists/{playlist_id}/tracks',
                                       params={'offset': offset, 'limit': limit})
            items = result.get('items', [])
            if not items:
                break
            tracks.extend(items)
            if len(items) < limit:
                break
            offset += limit

        return tracks

    def clear_playlist(self, playlist_id):
        """Remove all tracks from a playlist."""
        tracks = self.get_playlist_tracks(playlist_id)
        if not tracks:
            return

        # Build list of track URIs to remove
        track_uris = []
        for item in tracks:
            if item.get('track') and item['track'].get('uri'):
                track_uris.append({'uri': item['track']['uri']})

        # API allows max 100 tracks per request
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            data = {'tracks': batch}
            self._api_request('DELETE', f'/playlists/{playlist_id}/tracks', data=data)

    def update_playlist_details(self, playlist_id, name=None, description=None, public=None):
        """Update playlist name, description, or public status."""
        data = {}
        if name is not None:
            data['name'] = name
        if description is not None:
            data['description'] = description
        if public is not None:
            data['public'] = public

        if data:
            self._api_request('PUT', f'/playlists/{playlist_id}', data=data)

    def replace_playlist_tracks(self, playlist_id, track_uris, name=None, description=None):
        """Replace all tracks in a playlist with new tracks."""
        # Clear existing tracks
        self.clear_playlist(playlist_id)

        # Add new tracks
        self.add_tracks_to_playlist(playlist_id, track_uris)

        # Update details if provided
        if name or description:
            self.update_playlist_details(playlist_id, name=name, description=description)

    def generate_playlist_name(self, analysis):
        """Generate a descriptive playlist name from analysis."""
        parts = []

        if analysis['moods']:
            parts.append(analysis['moods'][0].title())

        if analysis['genres']:
            parts.append(analysis['genres'][0].title())

        if analysis['contexts']:
            context_names = {
                'workout': 'Workout',
                'study': 'Study Session',
                'sleep': 'Sleep',
                'party': 'Party',
                'road_trip': 'Road Trip',
                'dinner': 'Dinner',
                'coffee_shop': 'Coffee Shop',
                'morning': 'Morning',
            }
            parts.append(context_names.get(analysis['contexts'][0], analysis['contexts'][0].title()))

        if analysis['decades']:
            parts.append(analysis['decades'][0])

        if not parts:
            parts = ['Custom', 'Mix']

        return ' '.join(parts[:3]) + ' Mix'

    # -------------------------------------------------------------------------
    # Main Workflow
    # -------------------------------------------------------------------------

    def create_playlist_from_prompt(self, prompt, track_count=None, public=None,
                                      creativity=None, arc_type=None):
        """
        Main method: Create a playlist from a text prompt.

        Uses the full intelligence pipeline with config-driven defaults.

        Args:
            prompt: Text description of desired playlist
            track_count: Number of tracks to include (defaults to config)
            public: Whether playlist should be public (defaults to config)
            creativity: 0.0-1.0 creativity level (defaults to config)
            arc_type: Playlist flow type (defaults to config or emotional analysis)

        Returns:
            Dictionary with playlist info and URL
        """
        # Load defaults from config
        track_count = track_count or self.config.get_default('target_track_count', 25)
        public = public if public is not None else self.config.get_default('playlist_public', False)
        creativity = creativity if creativity is not None else self.config.get_default('creativity', 0.4)
        arc_type = arc_type or self.config.get_default('arc_type', 'journey')

        print(f"\n{'='*60}")
        print("Spotify Playlist Creator Agent (v3.0)")
        print(f"{'='*60}\n")

        # Step 1: Check authentication
        print("[1/6] Checking authentication...")
        if not self.is_authenticated():
            print("Not authenticated. Starting OAuth flow...")
            if not self.authenticate():
                return {'error': 'Authentication failed'}
        print("Authenticated!")

        # Step 2: Full intelligence analysis
        print(f"\n[2/6] Analyzing prompt: \"{prompt}\"")
        basic_analysis = self.analyze_prompt(prompt)
        emotional_analysis = self.analyze_emotional_depth(prompt)
        enriched = self.enrich_prompt(prompt)

        # Merge into full analysis
        analysis = {
            **basic_analysis,
            'emotional_analysis': emotional_analysis,
            'enriched_prompt': enriched,
        }

        print(f"  Genres: {analysis['genres']}")
        print(f"  Moods: {analysis['moods']}")
        print(f"  Decades: {analysis['decades']}")
        print(f"  Contexts: {analysis['contexts']}")
        if emotional_analysis.get('emotions'):
            emotions = [e['emotion'] for e in emotional_analysis['emotions'][:3]]
            print(f"  Emotions: {emotions}")
        if emotional_analysis.get('emotional_arc'):
            print(f"  Arc: {emotional_analysis['emotional_arc']}")
        print(f"  Creativity: {creativity}")

        # Step 3: Search for tracks
        print(f"\n[3/6] Searching for tracks...")
        queries = self.build_search_queries(analysis)
        print(f"  Using {len(queries)} search queries")

        all_tracks = []
        for query in queries:
            print(f"  Searching: {query}")
            tracks = self.search_tracks(query, limit=50)
            all_tracks.extend(tracks)
            print(f"    Found {len(tracks)} tracks")

        print(f"  Total tracks found: {len(all_tracks)}")

        # Step 4: Intelligent curation with emotional analysis
        print(f"\n[4/6] Curating tracks with intelligence pipeline...")

        # Determine arc from emotional analysis if detected
        detected_arc = emotional_analysis.get('emotional_arc')
        final_arc = detected_arc if detected_arc else arc_type

        curated_tracks = self.curate_tracks(
            all_tracks,
            analysis,
            target_count=track_count,
            creativity=creativity,
            arc_type=final_arc,
            use_emotional_analysis=True
        )
        print(f"  Selected {len(curated_tracks)} tracks (arc: {final_arc})")

        if not curated_tracks:
            return {'error': 'No suitable tracks found for this prompt'}

        # Step 5: Create playlist
        print(f"\n[5/6] Creating playlist...")
        playlist_name = self.generate_playlist_name(analysis)
        description = f"AI-generated playlist from: \"{prompt}\""

        playlist = self.create_playlist(playlist_name, description, public)
        print(f"  Created: {playlist_name}")

        # Step 6: Add tracks
        print(f"\n[6/6] Adding tracks to playlist...")
        track_uris = [f"spotify:track:{t['id']}" for t in curated_tracks]
        self.add_tracks_to_playlist(playlist['id'], track_uris)
        print(f"  Added {len(track_uris)} tracks")

        # Success!
        playlist_url = playlist['external_urls']['spotify']
        print(f"\n{'='*60}")
        print("Playlist created successfully!")
        print(f"{'='*60}")
        print(f"\nPlaylist: {playlist_name}")
        print(f"Tracks: {len(curated_tracks)}")
        print(f"URL: {playlist_url}\n")

        # Return track list for reference
        track_list = [
            {
                'name': t['name'],
                'artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown',
                'album': t['album']['name'] if t.get('album') else 'Unknown'
            }
            for t in curated_tracks
        ]

        return {
            'success': True,
            'playlist_name': playlist_name,
            'playlist_id': playlist['id'],
            'playlist_url': playlist_url,
            'track_count': len(curated_tracks),
            'tracks': track_list,
            'analysis': analysis,
            'creativity': creativity,
            'arc_type': final_arc,
        }


# Flask callback route
@app.route('/callback')
def callback():
    global auth_code
    auth_code = request.args.get('code')
    error = request.args.get('error')

    if error:
        return f"Authorization failed: {error}"

    if auth_code:
        return """
        <html>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
            </body>
        </html>
        """

    return "No authorization code received."


def main():
    """Interactive CLI for the Spotify Playlist Agent."""
    agent = SpotifyPlaylistAgent()

    print("\n" + "="*60)
    print("  Spotify Playlist Creator Agent")
    print("="*60)
    print("\nThis agent creates custom Spotify playlists from text prompts.")
    print("Type 'quit' to exit.\n")

    # Check if already authenticated
    if agent.is_authenticated():
        print("Already authenticated with Spotify.\n")
    else:
        print("Not authenticated. You'll be prompted to log in on first playlist creation.\n")

    while True:
        try:
            prompt = input("Enter playlist prompt (or 'quit'): ").strip()

            if prompt.lower() == 'quit':
                print("Goodbye!")
                break

            if not prompt:
                print("Please enter a prompt describing the playlist you want.\n")
                continue

            # Ask for track count
            count_input = input("Number of tracks (default 25): ").strip()
            track_count = int(count_input) if count_input.isdigit() else 25
            track_count = max(1, min(100, track_count))  # Limit between 1-100

            # Create the playlist
            result = agent.create_playlist_from_prompt(prompt, track_count=track_count)

            if result.get('error'):
                print(f"\nError: {result['error']}\n")
            else:
                print("\nTrack list:")
                for i, track in enumerate(result['tracks'][:10], 1):
                    print(f"  {i}. {track['name']} - {track['artist']}")
                if len(result['tracks']) > 10:
                    print(f"  ... and {len(result['tracks']) - 10} more tracks")
                print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == '__main__':
    main()
