"""
Faithless + Synthony Era - Funky Electronic Playlist
Featuring DJs from the same era as Faithless (1990s-2000s) with funky grooves.

Artists include big beat, trip hop, funky house, and electronic artists
who defined the late 90s/early 2000s electronic music scene.
"""

import sys
import os

# Add parent directory to path if running as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_agent import SpotifyPlaylistAgent

# Faithless-era lineup - funky electronic music from the 90s/2000s
# Focused on artists with groove, funk, and that classic big beat/house sound
LINEUP = [
    "Faithless",           # The main act - Sister Bliss, Maxi Jazz, Rollo
    "Basement Jaxx",       # Funky house legends
    "Fatboy Slim",         # Big beat funk master
    "Groove Armada",       # Downtempo/house with serious groove
    "The Chemical Brothers",  # Big beat with funky breakbeats
    "Daft Punk",           # French touch funk
    "Jamiroquai",          # Acid jazz/funk meets electronic
    "Moby",                # Electronic with soul/funk samples
    "Underworld",          # Progressive house with groove
    "Zero 7",              # Downtempo funk and soul
    "Röyksopp",            # Norwegian funky electronica
    "Leftfield",           # Progressive house/big beat
    "Orbital",             # Techno with groove and soul
    "Air",                 # French electronic, smooth and funky
    "Propellerheads",      # Big beat funk
    "The Prodigy",         # Electronic punk with breakbeat funk
    "Massive Attack",      # Trip hop with deep grooves
    "DJ Shadow",           # Hip hop/electronic with funky samples
    "Morcheeba",           # Trip hop with funky downtempo
    "FC Kahuna",           # Breakbeat house
]


def create_faithless_funky_playlist(tracks_per_artist=4):
    """
    Create a funky Faithless-era electronic playlist.

    Args:
        tracks_per_artist: Number of tracks to include per artist (default 4)
    """
    agent = SpotifyPlaylistAgent()

    print("\n" + "="*70)
    print("  Faithless + Synthony Era - Funky Electronic Playlist")
    print("="*70)
    print("\nCurating tracks from the golden era of electronic music (1995-2005)")
    print("Focused on funky, groovy, big beat, and house vibes\n")

    print("Lineup (20 legendary acts):")
    for i, artist in enumerate(LINEUP, 1):
        print(f"  {i:2}. {artist}")
    print()

    # Authentication
    print("[1/4] Checking authentication...")
    if not agent.is_authenticated():
        print("Starting OAuth flow...")
        if not agent.authenticate():
            print("Authentication failed!")
            return None
    print("Authenticated!\n")

    # Get user profile
    print("[2/4] Getting user profile...")
    agent.get_user_profile()
    print(f"User ID: {agent.user_id}\n")

    # Gather tracks
    print(f"[3/4] Collecting funky tracks ({tracks_per_artist} per artist)...\n")

    all_tracks = []
    artist_results = {}

    for artist_name in LINEUP:
        print(f"  {artist_name}:")

        tracks = agent.get_tracks_for_artist(artist_name, track_count=tracks_per_artist)
        artist_results[artist_name] = len(tracks)

        if tracks:
            for t in tracks:
                artist = t['artists'][0]['name'] if t.get('artists') else 'Unknown'
                print(f"    + {t['name'][:40]:<40} ({artist})")
            all_tracks.extend(tracks)
        else:
            print(f"    (No tracks found - artist may not be on Spotify)")

        print(f"    Selected {len(tracks)} tracks\n")

    if not all_tracks:
        print("No tracks found!")
        return None

    print(f"Total tracks collected: {len(all_tracks)}\n")

    # Create playlist
    print("[4/4] Creating playlist on Spotify...")

    playlist_name = "Faithless Era - Funky Electronic"
    description = (
        "Funky electronic vibes from the Faithless era (90s-2000s). "
        f"Featuring {', '.join(LINEUP[:4])}, and {len(LINEUP)-4} more legends. "
        "Big beat, funky house, trip hop, and electronic grooves. "
        "Perfect for Synthony vibes! "
        "🎧 Generated with Claude Code"
    )

    playlist = agent.create_playlist(playlist_name, description, public=False)
    print(f"  Created playlist: {playlist_name}")

    # Add tracks
    track_uris = [f"spotify:track:{t['id']}" for t in all_tracks]
    agent.add_tracks_to_playlist(playlist['id'], track_uris)
    print(f"  Added {len(track_uris)} tracks")

    # Save config (cache any new artist IDs)
    agent.config.save()
    print("  Saved config")

    # Success!
    playlist_url = playlist['external_urls']['spotify']

    print("\n" + "="*70)
    print("  Playlist Created Successfully!")
    print("="*70)
    print(f"\nPlaylist: {playlist_name}")
    print(f"Total Tracks: {len(all_tracks)}")
    print(f"URL: {playlist_url}")

    print("\n--- Artist Breakdown ---")
    for artist_name in LINEUP:
        count = artist_results.get(artist_name, 0)
        print(f"  {artist_name}: {count} tracks")

    print("\n--- Track Preview (first 20) ---")
    for i, track in enumerate(all_tracks[:20], 1):
        artist = track['artists'][0]['name'] if track.get('artists') else 'Unknown'
        print(f"{i:2}. {track['name'][:45]:<45} - {artist}")

    if len(all_tracks) > 20:
        print(f"... and {len(all_tracks) - 20} more tracks!")

    print("\n")
    return playlist_url


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  Faithless + Synthony - Funky Electronic Playlist Generator")
    print("="*70)
    print("\nThis script creates a playlist featuring funky electronic music")
    print("from the Faithless era (1990s-2000s).")
    print("\nGenre mix: Big beat, funky house, trip hop, French touch")
    print("Perfect for: Synthony vibes, pre-drinks, festival warmup")
    print("\n" + "="*70 + "\n")

    # Create the playlist (4 tracks per artist = ~80 tracks total)
    url = create_faithless_funky_playlist(tracks_per_artist=4)

    if url:
        print(f"\n✓ Success! Your funky playlist is ready: {url}")
        print("\nEnjoy the grooves! 🎵🎧")
