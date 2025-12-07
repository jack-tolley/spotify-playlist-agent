# Spotify Playlist Agent

AI-powered Spotify playlist creator using the Spotify Web API.

## Files

| File | Description |
|------|-------------|
| `spotify_agent.py` | Core agent - handles auth, search, playlist CRUD operations |
| `example_synthony_playlist.py` | Example script - creates festival lineup playlist |
| `upload_image.py` | Utility - upload custom playlist cover images |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for Spotify credentials |
| `.env` | Your Spotify credentials (create from template) |
| `cert.pem` / `key.pem` | SSL certificates for HTTPS OAuth callback |
| `spotify_tokens.json` | Cached auth tokens (auto-generated) |

## Quick Start

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Set up credentials
cp .env.example .env
# Edit .env with your Spotify Client ID and Secret

# 3. Run example
python3 example_synthony_playlist.py
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

## Agent Capabilities

- OAuth 2.0 authentication with automatic token refresh
- Track search with artist/genre/mood filtering
- Audio feature analysis (energy, tempo, danceability, valence)
- Playlist create/read/update/delete
- Cover image upload
- Rate limit handling
