# Spotify Playlist Agent

AI-powered Spotify playlist creator using the Spotify Web API.

## Files

| File | Description |
|------|-------------|
| `spotify_agent.py` | Core agent - handles auth, search, playlist CRUD operations |
| `example_synthony_playlist.py` | Example script - creates festival lineup playlist |
| `rhythm_and_vines_2025.py` | Rhythm & Vines NYE 2025/2026 - High energy festival bangers |
| `rhythm_and_vines_2025_chill.py` | Rhythm & Vines NYE 2025/2026 - Warmup mix (chill to energizing) |
| `faithless_synthony_funky.py` | Faithless Era - Funky electronic music from the 90s/2000s |
| `upload_image.py` | Utility - upload custom playlist cover images |
| `generate_image.py` | Utility - generate AI playlist cover images |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for Spotify credentials |
| `.env` | Your Spotify credentials (create from template) |
| `cert.pem` / `key.pem` | SSL certificates for HTTPS OAuth callback |
| `spotify_tokens.json` | Cached auth tokens (auto-generated) |
| `config.yaml` | Agent configuration and artist ID cache |

## Quick Start

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Set up credentials
cp .env.example .env
# Edit .env with your Spotify Client ID and Secret

# 3. Run example scripts
python3 example_synthony_playlist.py          # Synthony orchestra lineup
python3 rhythm_and_vines_2025.py              # R&V high energy bangers
python3 rhythm_and_vines_2025_chill.py        # R&V warmup mix (chill→energizing)
python3 faithless_synthony_funky.py           # Faithless era funky electronic
```

## Setup

### Spotify Developer App

1. Go to https://developer.spotify.com/dashboard/
2. Create an app
3. Add redirect URI: `https://127.0.0.1:8888/callback`
4. Copy Client ID and Client Secret to `.env`

### First Run

On first run, your browser will open for Spotify authorization. Accept the SSL certificate warning (it's a self-signed cert for localhost).

## Usage

### Using the Agent in Scripts

```python
from spotify_agent import SpotifyPlaylistAgent

agent = SpotifyPlaylistAgent()

# Authenticate (opens browser on first run)
if not agent.is_authenticated():
    agent.authenticate()

# Search for tracks
tracks = agent.search_tracks('artist:"Faithless"', limit=50)

# Create playlist
playlist = agent.create_playlist(
    name="My Playlist",
    description="Created with Spotify Agent",
    public=False
)

# Add tracks
track_uris = [f"spotify:track:{t['id']}" for t in tracks]
agent.add_tracks_to_playlist(playlist['id'], track_uris)

# Update existing playlist
agent.replace_playlist_tracks(playlist_id, new_track_uris)

# Upload cover image
# Use upload_image.py utility
```

### Upload Playlist Cover

```bash
python3 upload_image.py ./cover.jpg [playlist_id]
```

Requirements: JPEG format, max 256KB

## Example Playlists

### Rhythm & Vines 2025/2026 (New Year's Eve Festival)

Two complementary playlists for the Gisborne festival:

**Festival Bangers** (`rhythm_and_vines_2025.py`)
- 256 high-energy tracks from 90+ festival artists
- Sorted by popularity for crowd favorites
- Headliners: Kid Cudi, Turnstile, Wilkinson, L.A.B, 070 Shake, Pendulum
- Perfect for main stage vibes

**Warmup Mix** (`rhythm_and_vines_2025_chill.py`)
- 80 tracks with "early_build" arc: starts chill/lo-fi, builds to festival energy
- 40 curated artists known for mellower vibes
- Features: Maribou State, Dope Lemon, Good Neighbours, Jane Remover
- Perfect for pre-festival hangs, sunrise sessions, and building the vibe

### Synthony Orchestra

See `example_synthony_playlist.py` for classical orchestra lineup example.

### Faithless Era - Funky Electronic (`faithless_synthony_funky.py`)

80-track playlist featuring funky electronic music from the 1990s-2000s:
- 20 legendary artists from the Faithless era
- Genres: Big beat, funky house, trip hop, French touch
- Artists: Faithless, Basement Jaxx, Fatboy Slim, Groove Armada, The Chemical Brothers, Daft Punk, Jamiroquai, Moby, Underworld, Zero 7, and more
- Perfect for Synthony vibes, pre-festival warmup, or nostalgic electronic grooves

## Agent Capabilities

- OAuth 2.0 authentication with automatic token refresh
- Track search with artist/genre/mood filtering
- Audio feature analysis (energy, tempo, danceability, valence)
- Playlist sequencing with energy arcs (build, journey, wind_down, early_build)
- Playlist create/read/update/delete
- Cover image upload
- Rate limit handling
- Artist ID caching for faster lookups
