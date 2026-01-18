"""
Faithless + Synthony Era - Funky Electronic Playlist (Version 2)
Featuring DJs from the same era as Faithless (1990s-2000s) with funky grooves.

Version 2 Improvements:
- Filters duplicate track versions (radio edits, remixes, etc.) - keeps best version only
- Smart sequencing based on audio features for better flow
- Avoids same artist back-to-back for better mixing
"""

import sys
import os
import re
from difflib import SequenceMatcher

# Add parent directory to path if running as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_agent import SpotifyPlaylistAgent

# Faithless-era lineup - funky electronic music from the 90s/2000s
LINEUP = [
    "Faithless",           # The main act
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


def normalize_track_name(name):
    """
    Normalize track name for duplicate detection.

    Removes version info like:
    - Radio Edit, Album Version, etc.
    - Remix, Mix, Remaster info
    - Year info
    - Parentheses and brackets with version info

    Returns lowercase normalized name for comparison.
    """
    # Convert to lowercase
    normalized = name.lower()

    # Remove common version indicators in parentheses/brackets
    version_patterns = [
        r'\s*[\(\[].*?radio.*?edit.*?[\)\]]',
        r'\s*[\(\[].*?album.*?version.*?[\)\]]',
        r'\s*[\(\[].*?single.*?version.*?[\)\]]',
        r'\s*[\(\[].*?edit.*?[\)\]]',
        r'\s*[\(\[].*?mix.*?[\)\]]',
        r'\s*[\(\[].*?remix.*?[\)\]]',
        r'\s*[\(\[].*?remaster.*?[\)\]]',
        r'\s*[\(\[].*?remastered.*?[\)\]]',
        r'\s*[\(\[].*?\d{4}.*?[\)\]]',  # Years
        r'\s*[\(\[].*?feat\..*?[\)\]]',  # Featuring (keep the same)
        r'\s*-\s*radio.*?edit',
        r'\s*-\s*.*?mix',
        r'\s*-\s*.*?remix',
        r'\s*-\s*remaster.*',
    ]

    for pattern in version_patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

    # Remove extra whitespace
    normalized = ' '.join(normalized.split())

    return normalized.strip()


def is_duplicate(track1_name, track2_name, threshold=0.85):
    """
    Check if two track names are duplicates using fuzzy matching.

    Args:
        track1_name: First track name
        track2_name: Second track name
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        True if tracks are likely duplicates
    """
    norm1 = normalize_track_name(track1_name)
    norm2 = normalize_track_name(track2_name)

    # Exact match after normalization
    if norm1 == norm2:
        return True

    # Fuzzy match for minor variations
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    return similarity >= threshold


def select_best_version(duplicate_tracks):
    """
    Select the best version from a group of duplicate tracks.

    Priority:
    1. Prefer original versions over remixes/edits
    2. Prefer longer versions (full versions over radio edits)
    3. Prefer more popular tracks

    Args:
        duplicate_tracks: List of track objects that are duplicates

    Returns:
        Single best track from the group
    """
    if len(duplicate_tracks) == 1:
        return duplicate_tracks[0]

    # Score each track
    scored = []
    for track in duplicate_tracks:
        score = 0
        name_lower = track['name'].lower()

        # Penalize remixes, edits, versions
        if 'remix' in name_lower:
            score -= 20
        elif 'mix' in name_lower and 'remix' not in name_lower:
            score -= 15
        elif 'edit' in name_lower:
            score -= 10
        elif 'remaster' in name_lower:
            score -= 5

        # Prefer longer tracks (full versions)
        duration_ms = track.get('duration_ms', 0)
        score += duration_ms / 10000  # Convert to reasonable score range

        # Add popularity
        score += track.get('popularity', 0) * 0.5

        scored.append((track, score))

    # Return highest scoring track
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


def filter_duplicate_tracks(tracks, verbose=False):
    """
    Filter out duplicate track versions, keeping only the best version of each song.

    Args:
        tracks: List of track objects
        verbose: Print duplicate detection info

    Returns:
        Filtered list with one version per unique song
    """
    if not tracks:
        return []

    # Group tracks by normalized name
    track_groups = {}

    for track in tracks:
        track_name = track['name']
        normalized = normalize_track_name(track_name)

        # Check if this track matches any existing group
        found_group = False
        for existing_norm in list(track_groups.keys()):
            if is_duplicate(track_name, existing_norm):
                # Add to existing group
                track_groups[existing_norm].append(track)
                found_group = True
                break

        if not found_group:
            # Create new group
            track_groups[normalized] = [track]

    # Select best version from each group
    filtered_tracks = []
    duplicates_removed = 0

    for normalized_name, group in track_groups.items():
        if len(group) > 1:
            duplicates_removed += len(group) - 1
            if verbose:
                print(f"\n  Found {len(group)} versions of '{group[0]['name']}':")
                for t in group:
                    print(f"    - {t['name']} (pop: {t.get('popularity', 0)})")

        best = select_best_version(group)
        filtered_tracks.append(best)

        if len(group) > 1 and verbose:
            print(f"    → Keeping: {best['name']}")

    if verbose and duplicates_removed > 0:
        print(f"\n  Removed {duplicates_removed} duplicate versions")

    return filtered_tracks


def simple_artist_mix(tracks):
    """
    Simple artist mixing without audio features.
    Ensures artists are distributed throughout the playlist.

    Args:
        tracks: List of track objects

    Returns:
        Reordered list with artists mixed
    """
    if len(tracks) < 3:
        return tracks

    # Group tracks by artist
    artist_groups = {}
    for track in tracks:
        artist_id = track['artists'][0]['id'] if track.get('artists') else 'unknown'
        if artist_id not in artist_groups:
            artist_groups[artist_id] = []
        artist_groups[artist_id].append(track)

    # Distribute tracks round-robin style
    mixed = []
    artist_lists = list(artist_groups.values())
    max_length = max(len(group) for group in artist_lists)

    for i in range(max_length):
        for artist_tracks in artist_lists:
            if i < len(artist_tracks):
                mixed.append(artist_tracks[i])

    return mixed


def create_faithless_funky_playlist_v2(tracks_per_artist=6, arc_type='journey'):
    """
    Create a funky Faithless-era electronic playlist with smart filtering and sequencing.

    Args:
        tracks_per_artist: Number of tracks to fetch per artist (before filtering)
        arc_type: Playlist energy arc ('balanced', 'build', 'journey', 'energize')
    """
    agent = SpotifyPlaylistAgent()

    print("\n" + "="*70)
    print("  Faithless + Synthony Era - Funky Electronic Playlist v2")
    print("="*70)
    print("\nNew features:")
    print("  - Filters duplicate versions (keeps best version only)")
    print("  - Smart sequencing for better flow")
    print("  - Artists mixed throughout playlist\n")

    print(f"Arc type: {arc_type}")
    print(f"Lineup ({len(LINEUP)} artists):\n")
    for i, artist in enumerate(LINEUP, 1):
        print(f"  {i:2}. {artist}")
    print()

    # Authentication
    print("[1/6] Checking authentication...")
    if not agent.is_authenticated():
        print("Starting OAuth flow...")
        if not agent.authenticate():
            print("Authentication failed!")
            return None
    print("Authenticated!\n")

    # Get user profile
    print("[2/6] Getting user profile...")
    agent.get_user_profile()
    print(f"User ID: {agent.user_id}\n")

    # Gather tracks
    print(f"[3/6] Collecting tracks ({tracks_per_artist} per artist)...\n")

    all_tracks = []
    artist_track_counts = {}

    for artist_name in LINEUP:
        print(f"  {artist_name}:")
        tracks = agent.get_tracks_for_artist(artist_name, track_count=tracks_per_artist)

        if tracks:
            print(f"    Found {len(tracks)} tracks")
            all_tracks.extend(tracks)
            artist_track_counts[artist_name] = len(tracks)
        else:
            print(f"    (No tracks found)")
            artist_track_counts[artist_name] = 0

    if not all_tracks:
        print("No tracks found!")
        return None

    print(f"\n  Total tracks before filtering: {len(all_tracks)}")

    # Filter duplicates
    print(f"\n[4/6] Filtering duplicate track versions...\n")
    filtered_tracks = filter_duplicate_tracks(all_tracks, verbose=True)
    print(f"\n  Tracks after duplicate filtering: {len(filtered_tracks)}")

    # Get audio features for sequencing
    print(f"\n[5/6] Analyzing audio features for smart sequencing...")
    track_ids = [t['id'] for t in filtered_tracks]

    features_map = {}
    try:
        audio_features = agent.get_audio_features(track_ids)
        # Create features map
        for features in audio_features:
            if features:
                features_map[features['id']] = features
        print(f"  Retrieved features for {len(features_map)} tracks")
    except Exception as e:
        print(f"  Warning: Could not get audio features: {e}")
        print(f"  Will use basic artist mixing without energy arc")

    # Sequence playlist for optimal flow
    if features_map:
        print(f"  Sequencing with '{arc_type}' arc...")
        sequenced_tracks = agent.sequence_playlist(filtered_tracks, features_map, arc_type=arc_type)
        print(f"  Sequenced {len(sequenced_tracks)} tracks")
    else:
        print(f"  Using basic artist mixing (no audio features available)...")
        sequenced_tracks = simple_artist_mix(filtered_tracks)
        print(f"  Mixed {len(sequenced_tracks)} tracks")

    print()

    # Create playlist
    print("[6/6] Creating playlist on Spotify...")

    playlist_name = "Faithless Era - Funky Electronic v2"
    description = (
        f"Funky electronic from the 90s-2000s ({arc_type} arc). "
        f"Featuring {', '.join(LINEUP[:4])}, and more. "
        "Duplicate versions filtered, smart sequencing for optimal flow. "
        "Generated with Claude Code"
    )

    playlist = agent.create_playlist(playlist_name, description, public=False)
    print(f"  Created playlist: {playlist_name}")

    # Add tracks
    track_uris = [f"spotify:track:{t['id']}" for t in sequenced_tracks]
    agent.add_tracks_to_playlist(playlist['id'], track_uris)
    print(f"  Added {len(track_uris)} tracks")

    # Save config
    agent.config.save()
    print("  Saved config")

    # Success!
    playlist_url = playlist['external_urls']['spotify']

    print("\n" + "="*70)
    print("  Playlist Created Successfully!")
    print("="*70)
    print(f"\nPlaylist: {playlist_name}")
    print(f"Total Tracks: {len(sequenced_tracks)}")
    print(f"Arc Type: {arc_type}")
    print(f"URL: {playlist_url}")

    # Show sequencing preview
    print("\n--- Sequenced Track List (first 25) ---")
    for i, track in enumerate(sequenced_tracks[:25], 1):
        artist = track['artists'][0]['name'] if track.get('artists') else 'Unknown'
        features = features_map.get(track['id'], {})
        energy = features.get('energy', 0) if features else 0
        tempo = features.get('tempo', 0) if features else 0

        print(f"{i:2}. {track['name'][:40]:<40} - {artist[:20]:<20} "
              f"[E:{energy:.2f} T:{tempo:3.0f}]")

    if len(sequenced_tracks) > 25:
        print(f"... and {len(sequenced_tracks) - 25} more tracks!")

    print("\n")
    return playlist_url


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  Faithless + Synthony - Funky Electronic Playlist Generator v2")
    print("="*70)
    print("\nVersion 2 features:")
    print("  - Duplicate filtering (one version per song)")
    print("  - Smart sequencing based on audio features")
    print("  - Artist mixing throughout playlist")
    print("\n" + "="*70 + "\n")

    # Create the playlist
    # Fetch 6 tracks per artist, then filter duplicates
    # Use 'journey' arc for mid -> peak -> wind down flow
    url = create_faithless_funky_playlist_v2(tracks_per_artist=6, arc_type='journey')

    if url:
        print(f"\n✓ Success! Your improved funky playlist is ready: {url}")
        print("\nEnjoy the seamless flow! 🎵")
