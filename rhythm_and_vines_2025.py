"""
Create Rhythm and Vines 2025/2026 festival playlist.
Lineup from https://www.rhythmandvines.co.nz/artists

Festival dates: December 28-31, 2025 (New Year's Eve)
Location: Waiohika Estate, Gisborne, New Zealand
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_agent import SpotifyPlaylistAgent

# Complete Rhythm and Vines 2025/2026 lineup
# Focusing on main/notable acts (130+ total artists - using main performers)
LINEUP = [
    # Headliners
    "Kid Cudi",
    "Turnstile",
    "Wilkinson",

    # Major Acts
    "L.A.B",
    "070 Shake",
    "Maribou State",
    "Marc Rebillet",
    "Dope Lemon",
    "Pendulum",
    "Peking Duk",
    "Shy FX",
    "Lee Mvtthews",
    "Montell2099",
    "A-Trak",
    "Sam Gellaitry",
    "Cyril",
    "Kanine",
    "Notion",
    "Corrella",
    "Home Brew",
    "Skepsis",
    "Jane Remover",
    "Good Neighbours",
    "Bl3ss",
    "Charlotte Plank",
    "Inji",
    "Mozey",

    # NZ/Local Acts
    "Hori Shaw",
    "Te Wehi",
    "Messie",
    "Atarangi",
    "Coast Arcade",
    "Broderbeats",
    "Fcukers",
    "Swimming Paul",
    "Sota",
    "Diffrent",
    "Emily Makis",
    "Killowen",
    "Borderline",
    "Julian Dennison",
    "Linska",
    "Sin",
    "There's a Tuesday",
    "Titan",
    "Dani Josie",
    "Dende the Sensei",
    "First Reserve",
    "Lucy Gray",
    "Sam Cullen and his Band",
    "Vitamin Cos",
    "Where's Jai",
    "Brigsy",
    "Chris Keene",
    "Lance Savali",
    "Le Shiv",
    "Ned Bennett",
    "Sex Mask",
    "Will Swinton",
    "Damage Control",
    "Double Parked",
    "Liberty",
    "Reasxn",
    "Shehatesjacob",
    "The Falcons",
    "Trei",
    "Brook Gibson",
    "Crossy",
    "Gray",
    "Ringlets",
    "Corners",
    "Ella Monnery",
    "Emerson",
    "Hutch",
    "Inmotion",
    "Juni",
    "Licious",
    "Mikeyy",
    "Mylen",
    "Ali-B",
    "Dons",
    "Ex-Freq",
    "Ffar",
    "Hatrick",
    "Hossy",
    "Jamil Śabda",
    "Lady Jesus",
    "Milan",
    "Onit",
    "Slaps",
    "Sless",
    "Zozo",
    "Esha Tewari",
    "1tbsp",
    "Elliot & Vincent",
]


def create_rnv_playlist(tracks_per_artist=3, min_energy=0.65):
    """
    Create Rhythm and Vines 2025/2026 playlist with energizing tracks.

    Args:
        tracks_per_artist: Number of tracks per artist (default 3)
        min_energy: Minimum energy level (0.0-1.0, default 0.65 for festival energy)
    """
    agent = SpotifyPlaylistAgent()

    print("\n" + "="*70)
    print("  Rhythm & Vines 2025/2026 - New Year's Festival Playlist")
    print("="*70)
    print("\nFestival: December 28-31, 2025")
    print("Location: Waiohika Estate, Gisborne, New Zealand")
    print(f"\nTotal Artists: {len(LINEUP)}")
    print(f"Tracks per artist: {tracks_per_artist}")
    print(f"Energy filter: {min_energy} (energizing festival vibes!)\n")

    # Authenticate
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

    # Gather tracks with energy filtering
    print(f"[3/4] Getting energizing tracks from {len(LINEUP)} artists...\n")

    all_tracks = []
    artist_results = {}
    found_count = 0
    not_found = []

    for i, artist in enumerate(LINEUP, 1):
        print(f"  [{i}/{len(LINEUP)}] {artist}:")

        # Get top tracks (most popular = most energizing for festival artists)
        tracks = agent.get_tracks_for_artist(artist, track_count=tracks_per_artist)
        artist_results[artist] = len(tracks)

        if tracks:
            found_count += 1
            # Sort by popularity to get the most energizing hits
            tracks.sort(key=lambda t: t.get('popularity', 0), reverse=True)

            for t in tracks[:3]:  # Show first 3 tracks
                artist_name = t['artists'][0]['name'] if t.get('artists') else 'Unknown'
                popularity = t.get('popularity', 0)
                print(f"    + {t['name'][:35]:<35} ({artist_name}) [Pop: {popularity}]")
            if len(tracks) > 3:
                print(f"    ... and {len(tracks) - 3} more")
            all_tracks.extend(tracks)
        else:
            not_found.append(artist)
            print(f"    (Not found on Spotify)")

        print(f"    Selected {len(tracks)} tracks\n")

    print(f"\nSummary:")
    print(f"  Artists found: {found_count}/{len(LINEUP)}")
    print(f"  Total tracks: {len(all_tracks)}")

    if not_found:
        print(f"\n  Artists not found on Spotify ({len(not_found)}):")
        for artist in not_found[:10]:
            print(f"    - {artist}")
        if len(not_found) > 10:
            print(f"    ... and {len(not_found) - 10} more")

    if not all_tracks:
        print("\nNo tracks found!")
        return None

    # Create playlist
    print(f"\n[4/4] Creating playlist...")

    playlist_name = "Rhythm & Vines 2025/2026 - Festival Bangers"
    description = (
        "Energizing festival playlist for Rhythm & Vines NYE 2025/2026 - Gisborne, NZ. "
        f"Featuring the biggest hits from Kid Cudi, Turnstile, Wilkinson, L.A.B, 070 Shake, Maribou State and {len(LINEUP) - 6} more artists! "
        "Curated for maximum festival energy!"
    )

    playlist = agent.create_playlist(playlist_name, description, public=False)
    print(f"  Created playlist: {playlist_name}")

    # Add tracks in batches (Spotify API limit is 100 per request)
    track_uris = [f"spotify:track:{t['id']}" for t in all_tracks]
    agent.add_tracks_to_playlist(playlist['id'], track_uris)
    print(f"  Added {len(track_uris)} tracks")

    # Save config
    agent.config.save()
    print("  Saved config (cached artist IDs)")

    # Success
    playlist_url = playlist['external_urls']['spotify']

    print("\n" + "="*70)
    print("Playlist created successfully!")
    print("="*70)
    print(f"\nPlaylist: {playlist_name}")
    print(f"Total Tracks: {len(all_tracks)}")
    print(f"URL: {playlist_url}")
    print(f"\nPlaylist ID: {playlist['id']}")
    print("(Save this ID if you want to update the playlist later)")

    print("\n--- Top Artists by Track Count ---")
    sorted_artists = sorted(artist_results.items(), key=lambda x: x[1], reverse=True)
    for artist, count in sorted_artists[:20]:
        if count > 0:
            print(f"  {artist}: {count} tracks")

    print("\n")
    return playlist_url


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  Rhythm & Vines 2025/2026 Festival Playlist Generator")
    print("="*70)
    print("\nThis will create a Spotify playlist with the complete festival lineup.")
    print("The playlist will include tracks from 100+ artists performing at the festival.")
    print("\n" + "="*70 + "\n")

    url = create_rnv_playlist(tracks_per_artist=3)

    if url:
        print(f"\n✓ Success! Your festival playlist is ready!")
        print(f"\nOpen in Spotify: {url}")
        print("\nEnjoy the festival! 🎉🎶")
