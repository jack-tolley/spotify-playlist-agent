"""
Update existing Synthony 2026 playlist using Artist ID-based search.
Example script for updating festival playlists.

This script demonstrates the v3.0 approach:
- Uses Artist IDs from config (or auto-discovers and caches them)
- Uses get_artist_top_tracks() for reliable results
- No more verify/exclude patterns needed
"""

import sys
import os

# Add parent directory to path if running as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_agent import SpotifyPlaylistAgent

# Existing playlist to update (replace with your playlist ID)
PLAYLIST_ID = "YOUR_PLAYLIST_ID_HERE"

# Synthony 2026 lineup - verified from https://synthony.com/shows/new-zealand/synthony-festival/
# Artist IDs are cached in config.yaml for reliability
LINEUP = [
    "Faithless",
    "Peking Duk",
    "The Black Seeds",
    "The Exponents",
    "Shapeshifter",  # NZ Shapeshifter - ID cached in config.yaml
    "Kaylee Bell",
    # Note: "Made You Look" may not have a Spotify presence
]


def update_synthony_playlist(tracks_per_artist=5):
    """
    Update the Synthony 2026 playlist using the improved agent.

    Args:
        tracks_per_artist: Number of tracks to include per artist
    """
    # Validate playlist ID is set
    if PLAYLIST_ID == "YOUR_PLAYLIST_ID_HERE":
        print("\n" + "="*60)
        print("  ERROR: Playlist ID not configured")
        print("="*60)
        print("\nPlease update the PLAYLIST_ID variable with your actual playlist ID.")
        print("\nTo get a playlist ID:")
        print("  1. Open Spotify and navigate to your playlist")
        print("  2. Click '...' -> Share -> Copy link to playlist")
        print("  3. Extract the ID from the URL:")
        print("     https://open.spotify.com/playlist/YOUR_ID_HERE")
        print("\nOr use create_lineup_playlist() to create a new playlist.")
        return None

    # Initialize agent (loads config automatically)
    agent = SpotifyPlaylistAgent()

    print("\n" + "="*60)
    print("  Updating Synthony 2026 Festival Playlist (v3.0)")
    print("="*60)
    print(f"\nPlaylist ID: {PLAYLIST_ID}")
    print(f"URL: https://open.spotify.com/playlist/{PLAYLIST_ID}\n")

    print("Lineup:")
    for artist in LINEUP:
        # Show if artist ID is cached
        cached_id = agent.config.get_artist_id(artist)
        status = f"(cached: {cached_id[:8]}...)" if cached_id else "(will lookup)"
        print(f"  - {artist} {status}")
    print()

    # Check authentication
    print("[1/5] Checking authentication...")
    if not agent.is_authenticated():
        print("Starting OAuth flow...")
        if not agent.authenticate():
            print("Authentication failed!")
            return
    print("Authenticated!\n")

    # Get user profile
    print("[2/5] Getting user profile...")
    agent.get_user_profile()
    print(f"User ID: {agent.user_id}\n")

    # Search for tracks from each artist using ID-based search
    print(f"[3/5] Getting tracks ({tracks_per_artist} per artist)...\n")

    final_tracks = []
    artist_results = {}

    for artist_name in LINEUP:
        print(f"  {artist_name}:")

        # Use the new ID-based method
        tracks = agent.get_tracks_for_artist(artist_name, track_count=tracks_per_artist)

        artist_results[artist_name] = len(tracks)

        if tracks:
            for t in tracks:
                artist = t['artists'][0]['name'] if t.get('artists') else 'Unknown'
                print(f"    + {t['name'][:35]:<35} ({artist})")
            final_tracks.extend(tracks)
        else:
            print(f"    (No tracks found - artist may not be on Spotify)")

        print(f"    Selected {len(tracks)} tracks\n")

    print(f"Total tracks selected: {len(final_tracks)}\n")

    if not final_tracks:
        print("No tracks found!")
        return

    # Update existing playlist
    print("[4/5] Clearing existing playlist...")
    agent.clear_playlist(PLAYLIST_ID)
    print("  Cleared existing tracks")

    print("\n[5/5] Adding new tracks...")
    track_uris = [f"spotify:track:{t['id']}" for t in final_tracks]
    agent.add_tracks_to_playlist(PLAYLIST_ID, track_uris)
    print(f"  Added {len(track_uris)} tracks")

    # Update playlist details
    artist_names = ", ".join(LINEUP[:5])
    if len(LINEUP) > 5:
        artist_names += f" +{len(LINEUP) - 5} more"
    description = f"Synthony Festival 2026 lineup: {artist_names}"
    agent.update_playlist_details(PLAYLIST_ID,
                                   name="Synthony 2026 - Festival Mix",
                                   description=description)
    print("  Updated playlist details")

    # Save config (to persist any newly discovered artist IDs)
    agent.config.save()
    print("  Saved config (cached any new artist IDs)")

    # Success
    playlist_url = f"https://open.spotify.com/playlist/{PLAYLIST_ID}"

    print("\n" + "="*60)
    print("Playlist updated successfully!")
    print("="*60)
    print(f"\nPlaylist: Synthony 2026 - Festival Mix")
    print(f"Total Tracks: {len(final_tracks)}")
    print(f"URL: {playlist_url}")

    print("\n--- Artist Breakdown ---")
    for artist_name in LINEUP:
        count = artist_results.get(artist_name, 0)
        print(f"  {artist_name}: {count} tracks")

    print("\n--- Full Track List ---")
    for i, track in enumerate(final_tracks, 1):
        artist = track['artists'][0]['name'] if track.get('artists') else 'Unknown'
        print(f"{i:2}. {track['name'][:42]:<42} - {artist}")

    print("\n")
    return playlist_url


def create_lineup_playlist(lineup, playlist_name, description=None,
                           tracks_per_artist=5, playlist_id=None):
    """
    Generic function to create/update a lineup-based playlist.

    This is the recommended pattern for festival/event playlists.

    Args:
        lineup: List of artist names
        playlist_name: Name for the playlist
        description: Optional description
        tracks_per_artist: Tracks per artist (default 5)
        playlist_id: Existing playlist ID to update (None = create new)

    Returns:
        Playlist URL
    """
    agent = SpotifyPlaylistAgent()

    if not agent.is_authenticated():
        if not agent.authenticate():
            print("Authentication failed!")
            return None

    agent.get_user_profile()

    # Gather tracks
    all_tracks = []
    for artist in lineup:
        tracks = agent.get_tracks_for_artist(artist, track_count=tracks_per_artist)
        all_tracks.extend(tracks)

    if not all_tracks:
        print("No tracks found!")
        return None

    track_uris = [f"spotify:track:{t['id']}" for t in all_tracks]

    # Create or update playlist
    if playlist_id:
        agent.replace_playlist_tracks(playlist_id, track_uris,
                                       name=playlist_name, description=description)
        url = f"https://open.spotify.com/playlist/{playlist_id}"
    else:
        playlist = agent.create_playlist(playlist_name, description or "", public=False)
        agent.add_tracks_to_playlist(playlist['id'], track_uris)
        url = playlist['external_urls']['spotify']

    # Save any cached artist IDs
    agent.config.save()

    print(f"\nPlaylist ready: {url}")
    print(f"Total tracks: {len(all_tracks)}")

    return url


if __name__ == '__main__':
    import sys

    print("\n" + "="*60)
    print("  Spotify Festival Playlist Example")
    print("="*60)
    print("\nThis script demonstrates creating festival lineup playlists.")
    print("\nUsage options:")
    print("  1. Update existing playlist (requires PLAYLIST_ID configuration)")
    print("  2. Create new playlist using create_lineup_playlist()")
    print("\n" + "="*60 + "\n")

    if PLAYLIST_ID == "YOUR_PLAYLIST_ID_HERE":
        print("Creating a NEW playlist (no PLAYLIST_ID configured)...\n")

        # Example: Create new playlist
        url = create_lineup_playlist(
            lineup=LINEUP,
            playlist_name="Synthony 2026 Festival Mix",
            description="Festival lineup featuring " + ", ".join(LINEUP[:3]) + " and more",
            tracks_per_artist=5,
            playlist_id=None  # None = create new
        )

        if url:
            print(f"\n✓ Success! New playlist created: {url}")
            print("\nTo update this playlist in the future:")
            print(f"  1. Extract the playlist ID from the URL")
            print(f"  2. Set PLAYLIST_ID = '<your_id>' at the top of this file")
    else:
        print("Updating EXISTING playlist...\n")
        update_synthony_playlist()
