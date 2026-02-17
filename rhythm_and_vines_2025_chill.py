"""
Create Rhythm and Vines 2025/2026 CHILL/LO-FI festival playlist.
Lineup from https://www.rhythmandvines.co.nz/artists

Festival dates: December 28-31, 2025 (New Year's Eve)
Location: Waiohika Estate, Gisborne, New Zealand

This version filters for chill, lo-fi, and mellow tracks for pre-festival vibes,
morning sessions, and wind-down moments.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_agent import SpotifyPlaylistAgent

# Complete Rhythm and Vines 2025/2026 lineup
# Focusing on artists likely to have chill/lo-fi tracks
LINEUP = [
    # Artists with known chill vibes
    "Maribou State",
    "Dope Lemon",
    "Marc Rebillet",
    "Good Neighbours",
    "070 Shake",
    "Sam Gellaitry",
    "Jane Remover",
    "Esha Tewari",

    # Electronic/Downtempo artists
    "Notion",
    "Bl3ss",
    "Lee Mvtthews",
    "Montell2099",

    # NZ Artists (often have chill tracks)
    "L.A.B",
    "Corrella",
    "Hori Shaw",
    "Te Wehi",
    "Coast Arcade",
    "Will Swinton",
    "Lance Savali",
    "Double Parked",
    "Lucy Gray",
    "Le Shiv",
    "Corners",
    "Emerson",
    "Mylen",
    "Elliot & Vincent",
    "Sex Mask",

    # Others that might have mellower tracks
    "Messie",
    "Atarangi",
    "Swimming Paul",
    "Diffrent",
    "Emily Makis",
    "Borderline",
    "Liberty",
    "Ringlets",
    "Ella Monnery",
    "Inmotion",
    "Mikeyy",
    "Zozo",
    "1tbsp",
]


def create_chill_rnv_playlist(tracks_per_artist=2):
    """
    Create Rhythm and Vines 2025/2026 CHILL/LO-FI playlist revised to build energy.

    Args:
        tracks_per_artist: Number of tracks per artist
    """
    agent = SpotifyPlaylistAgent()

    print("\n" + "="*70)
    print("  Rhythm & Vines 2025/2026 - Chill to Energizing Playlist")
    print("="*70)
    print("\nFestival: December 28-31, 2025")
    print("Location: Waiohika Estate, Gisborne, New Zealand")
    print(f"\nFocusing on {len(LINEUP)} artists")
    print(f"Tracks per artist: {tracks_per_artist}")
    print("Arc: Start chill/lo-fi -> Build to energizing (50% mark) -> Maintain high energy\n")

    # Authenticate
    print("[1/5] Checking authentication...")
    if not agent.is_authenticated():
        print("Starting OAuth flow...")
        if not agent.authenticate():
            print("Authentication failed!")
            return None
    print("Authenticated!\n")

    # Get user profile
    print("[2/5] Getting user profile...")
    agent.get_user_profile()
    print(f"User ID: {agent.user_id}\n")

    # Gather tracks
    print(f"[3/5] Gathering tracks from {len(LINEUP)} artists...\n")

    all_tracks = []
    found_count = 0
    not_found = []

    for i, artist in enumerate(LINEUP, 1):
        # Get tracks (using top tracks to ensure quality)
        tracks = agent.get_tracks_for_artist(artist, track_count=tracks_per_artist)

        if tracks:
            found_count += 1
            all_tracks.extend(tracks)
            print(f"  [{i}/{len(LINEUP)}] {artist}: Found {len(tracks)} tracks")
        else:
            not_found.append(artist)
            print(f"  [{i}/{len(LINEUP)}] {artist}: (Not found)")

    if not all_tracks:
        print("\nNo tracks found!")
        return None
    
    print(f"\nFound {len(all_tracks)} total tracks.")

    # Get audio features and sequence
    print(f"\n[4/5] Analyzing audio features and sequencing...")
    
    # Get distinct tracks to avoid dupes
    unique_tracks = {t['id']: t for t in all_tracks}.values()
    unique_track_list = list(unique_tracks)
    
    track_ids = [t['id'] for t in unique_track_list]
    audio_features = agent.get_audio_features(track_ids)
    
    features_map = {}
    for f in audio_features:
        if f:
            features_map[f['id']] = f

    # Sequence using the new 'early_build' arc
    sequenced_tracks = agent.sequence_playlist(unique_track_list, features_map, arc_type='early_build')
    print(f"  Sequenced {len(sequenced_tracks)} tracks with 'early_build' arc.")

    # Create playlist
    print(f"\n[5/5] Creating playlist...")

    playlist_name = "Rhythm & Vines 2025/2026 - Warmup Mix"
    description = (
        "Rhythm & Vines NYE 2025/2026 warmup mix. "
        "Starts chill/lo-fi and builds to festival energy. "
        f"Featuring {found_count} festival artists."
    )

    playlist = agent.create_playlist(playlist_name, description, public=False)
    print(f"  Created playlist: {playlist_name}")

    # Add tracks in batches
    track_uris = [f"spotify:track:{t['id']}" for t in sequenced_tracks]
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
    print(f"Total Tracks: {len(sequenced_tracks)}")
    print(f"URL: {playlist_url}")
    print(f"\nPlaylist ID: {playlist['id']}")
    
    return playlist_url


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  Rhythm & Vines 2025/2026 Chill/Lo-Fi Playlist Generator")
    print("="*70)
    print("\nThis will create a Spotify playlist with chill, lo-fi tracks")
    print("from festival artists for those mellow festival moments.")
    print("\n" + "="*70 + "\n")

    url = create_chill_rnv_playlist(tracks_per_artist=2)

    if url:
        print(f"\n✓ Success! Your chill festival playlist is ready!")
        print(f"\nOpen in Spotify: {url}")
        print("\nPerfect for sunrise sets and beach hangs! 🌅🎶")
