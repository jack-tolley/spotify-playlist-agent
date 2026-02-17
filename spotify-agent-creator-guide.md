# Spotify Playlist Creator Agent - Guide

## Overview

This agent creates custom Spotify playlists based on text prompts using the Spotify Web API. It handles authentication, track discovery, curation, and playlist management with intelligent emotional analysis and configurable defaults.

## Quick Reference

### Core Files
- `spotify_agent.py` - Main agent class with all API methods
- `config.yaml` - Configuration file for defaults, artist mappings, and emotional settings
- `example_synthony_playlist.py` - Working example for festival lineups
- `upload_image.py` - Playlist cover image uploader
- `generate_image.py` - Simple playlist cover generator

### Key Commands
```bash
pip3 install -r requirements.txt    # Install dependencies
python3 spotify_agent.py            # Interactive CLI mode
python3 example_synthony_playlist.py # Run example
python3 upload_image.py cover.jpg   # Upload cover image
```

## Prerequisites

### 1. Spotify Developer Account

1. Visit https://developer.spotify.com/dashboard/
2. Create an app with these settings:
   - **Redirect URI**: `https://127.0.0.1:8888/callback` (HTTPS required)
   - **API**: Web API
3. Note your **Client ID** and **Client Secret**

### 2. Environment Setup

Create `.env` file:
```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=https://127.0.0.1:8888/callback
```

### 3. Required Scopes
- `playlist-modify-public` - Create/modify public playlists
- `playlist-modify-private` - Create/modify private playlists
- `user-read-private` - Read user profile
- `user-read-email` - Read user email
- `ugc-image-upload` - Upload playlist images

## Agent Capabilities

### SpotifyPlaylistAgent Methods

**Authentication:**
- `authenticate()` - Start OAuth flow
- `is_authenticated()` - Check auth status
- `ensure_valid_token()` - Auto-refresh if needed

**Artist ID-Based Search (v3.0):**
- `find_artist_id(name)` - Find artist Spotify ID (cached + API fallback)
- `get_artist_top_tracks(artist_id)` - Get artist's top tracks
- `get_tracks_for_artist(name, count)` - High-level: get tracks by artist name

**Search:**
- `search_tracks(query, limit=50)` - Search for tracks
- `get_audio_features(track_ids)` - Get track audio analysis

**Playlist Management:**
- `create_playlist(name, description, public)` - Create new playlist
- `add_tracks_to_playlist(playlist_id, track_uris)` - Add tracks
- `clear_playlist(playlist_id)` - Remove all tracks
- `replace_playlist_tracks(playlist_id, track_uris)` - Replace tracks
- `update_playlist_details(playlist_id, name, description)` - Update metadata
- `get_playlist_tracks(playlist_id)` - Get current tracks

**Analysis:**
- `analyze_prompt(prompt)` - Parse prompt for genres, moods, etc.
- `analyze_emotional_depth(prompt)` - Deep emotional analysis
- `enrich_prompt(prompt)` - Semantic enrichment
- `build_search_queries(analysis)` - Generate search queries
- `curate_tracks(tracks, analysis, target_count)` - Filter and rank tracks
- `curate_tracks_intelligent(tracks, prompt, count)` - Full intelligence pipeline

**Configuration:**
- `config.get_default(key)` - Get config default value
- `config.get_artist_id(name)` - Get cached artist ID
- `config.cache_artist_mapping(name, id)` - Cache artist ID
- `config.save()` - Save config changes

## Configuration System (v3.0)

The agent uses `config.yaml` for customizable defaults:

```yaml
# config.yaml
defaults:
  tracks_per_artist: 5
  target_track_count: 25
  creativity: 0.4
  arc_type: 'journey'
  playlist_public: false
  market: 'US'

emotional_mappings:
  bittersweet:
    valence_range: [0.3, 0.5]
    energy_range: [0.4, 0.6]

artist_mappings:
  "Shapeshifter":
    spotify_id: "3MZsBdqDrRTJihTHQrO6Dq"
    region: "NZ"
```

### Using Config in Scripts

```python
agent = SpotifyPlaylistAgent()  # Loads config.yaml automatically

# Or specify custom config
agent = SpotifyPlaylistAgent(config_path='my_config.yaml')

# Access defaults
creativity = agent.config.get_default('creativity', 0.4)

# Check cached artist
artist_id = agent.config.get_artist_id("Faithless")
```

## Workflow Best Practices

### 1. Use Artist ID-Based Search (Recommended)

The new v3.0 approach eliminates wrong-artist bugs:

```python
# Good - uses Artist ID (auto-cached)
tracks = agent.get_tracks_for_artist("Shapeshifter", track_count=5)

# Uses top tracks API - more reliable than search
# Artist ID is auto-discovered and cached in config.yaml
```

### 2. Always Update Existing Playlists

**Don't** create new playlists for revisions. **Do** update existing ones:

```python
# Good - update existing
agent.replace_playlist_tracks(playlist_id, new_tracks)
agent.update_playlist_details(playlist_id, name="New Name")

# Avoid - creates duplicates
playlist = agent.create_playlist("New Playlist", ...)
```

### 3. Lineup-Based Playlists

For festival/event lineups, use the simple pattern:

```python
LINEUP = ["Faithless", "Peking Duk", "The Black Seeds"]

# Gather tracks (Artist IDs cached automatically)
all_tracks = []
for artist in LINEUP:
    tracks = agent.get_tracks_for_artist(artist, track_count=5)
    all_tracks.extend(tracks)

# Create/update playlist
track_uris = [f"spotify:track:{t['id']}" for t in all_tracks]
agent.replace_playlist_tracks(playlist_id, track_uris)

# Save cached artist IDs
agent.config.save()
```

### 4. Use Creative Playlist Names

Include emojis or special characters to differentiate playlists:
```python
name = "Festival 2026 Warmup Mix"
description = "Artist1, Artist2, Artist3"
```

### 5. Delete Duplicate Playlists

```python
# Spotify uses "unfollow" to delete
agent._api_request('DELETE', f'/playlists/{playlist_id}/followers')
```

## Search Query Syntax

```
artist:"Artist Name"     # Exact artist match
genre:electronic         # Genre filter
year:1990-2000          # Year range
track:"Song Name"       # Track title
```

Combine terms: `artist:"Faithless" year:2000-2010`

## Troubleshooting

### "Invalid redirect URI"
- Spotify now requires HTTPS
- Use `https://127.0.0.1:8888/callback` (not localhost, not http)
- Ensure exact match in Spotify dashboard

### SSL Certificate Warning
- Self-signed cert triggers browser warning
- Click "Advanced" -> "Proceed to 127.0.0.1"
- This is safe for localhost OAuth

### Wrong Artist Results
With v3.0, this is largely solved by Artist ID caching:
1. First run auto-discovers and caches the correct artist ID
2. Subsequent runs use the cached ID
3. For disambiguation, manually add the correct ID to `config.yaml`

### Artist Not Found on Spotify
Some artists may not be on Spotify or use different names:
- Search manually on Spotify to verify
- Try alternate spellings/names
- Check if artist has a Spotify presence

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/me` | GET | User profile |
| `/search` | GET | Track/artist search |
| `/artists/{id}/top-tracks` | GET | Artist top tracks |
| `/artists/{id}/albums` | GET | Artist albums |
| `/users/{id}/playlists` | POST | Create playlist |
| `/playlists/{id}/tracks` | GET/POST/DELETE | Manage tracks |
| `/playlists/{id}` | PUT | Update details |
| `/playlists/{id}/images` | PUT | Upload cover |
| `/playlists/{id}/followers` | DELETE | Delete playlist |
| `/audio-features` | GET | Track analysis |

## Intelligence Features (v3.0)

### Emotional Depth Analysis

The agent analyzes emotional nuance beyond simple keywords:

```python
# Detects intensity modifiers
"deeply melancholic" -> intensity: 0.9
"slightly sad" -> intensity: 0.3

# Supports compound emotions
"bittersweet nostalgia" -> multiple emotion mapping

# Handles negation
"upbeat but not cheesy" -> excludes certain patterns

# Emotional arcs
"build to a peak" -> sequences tracks accordingly
```

**Supported Emotion Vocabulary:**
- Positive: joy, happy, ecstatic, content, peaceful, hopeful, triumphant
- Negative: sad, melancholy, heartbroken, angry, furious, anxious
- Mixed: nostalgic, bittersweet, wistful, longing, rebellious
- Neutral: reflective, introspective, contemplative

### Creative Variability

Control randomness with the `creativity` parameter (0.0-1.0):

```python
result = agent.create_playlist_from_prompt(
    "chill electronic",
    creativity=0.5
)
```

- `0.0` = Deterministic (same prompt = same playlist)
- `0.3` = Default (slight variation, 15% discovery tracks)
- `0.7` = Adventurous (more hidden gems, shuffled tiers)
- `1.0` = Maximum variety

### Playlist Flow & Arc

Tracks are sequenced for optimal listening experience:

```python
agent.sequence_playlist(tracks, features_map, arc_type='journey')
```

**Arc Types:**
| Type | Description | Best For |
|------|-------------|----------|
| `balanced` | Consistent energy | Background listening |
| `build` | Low -> High energy | Workout warmup |
| `early_build` | Low -> High by midpoint, maintain | Festival warmup |
| `journey` | Mid -> Peak -> Wind down | Album-like experience |
| `energize` | Start strong, maintain | Party/workout |
| `wind_down` | High -> Low | Evening relaxation |

### Prompt Enrichment

Understands complex prompt patterns:

```python
agent.enrich_prompt("like The Cure but more modern")
# Returns: comparisons, exclusions, temporal_modifiers
```

**Supported Patterns:**
- "like X but Y" -> reference + modifier
- "similar to X" -> reference artist search
- "but not cheesy" -> exclusion filter
- "vintage remixed for today" -> temporal blending

### Full Intelligence Pipeline

Use the main method for full intelligence:

```python
result = agent.create_playlist_from_prompt(
    prompt="deeply melancholic 90s alternative that builds to catharsis",
    track_count=25,
    creativity=0.4,
    arc_type='journey'
)
```

## Version History

### v3.0.0 (December 2024) - Infrastructure Update
- **Config System**: YAML-based configuration for defaults and mappings
- **Artist ID Search**: Reliable ID-based search with auto-caching
- **get_artist_top_tracks()**: Direct API endpoint for better results
- **Unified Pipeline**: create_playlist_from_prompt() uses full intelligence
- **ConfigManager**: Centralized configuration management

### v2.1.0 (December 2024) - Intelligence Update
- Emotional depth analysis with intensity parsing
- Creative variability with discovery slots
- Playlist sequencing with energy arcs
- Prompt enrichment for complex patterns

### v2.0.0 (December 2024) - Initial Release
- OAuth 2.0 authentication with HTTPS
- Basic prompt analysis
- Track search and curation
- Playlist CRUD operations

---

**Last Updated**: December 2024
**Agent Version**: 3.0.0 (Infrastructure Update)
**Tested With**: Python 3.13, Spotify Web API v1
