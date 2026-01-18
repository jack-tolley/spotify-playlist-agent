# Duplicate Track Filtering Guide

## Problem

When creating playlists from artist catalogs, Spotify often returns multiple versions of the same song:
- Radio edits vs full versions
- Original vs remixes/remasters
- Different years/releases of the same track

**Example from Faithless:**
- "Insomnia - Radio Edit"
- "Insomnia - Monster Mix"
- "Insomnia - Disclosure's 2025 Edit"

This creates redundant playlists where the same song appears multiple times.

## Solution

The `faithless_synthony_funky_v2.py` script implements intelligent duplicate detection and filtering.

### How It Works

#### 1. Track Name Normalization

```python
def normalize_track_name(name):
    """Remove version info to get base track name"""
```

Removes common version indicators:
- Radio Edit, Album Version, Single Version
- Edit, Mix, Remix, Remaster
- Years in parentheses (2024, etc.)
- Converts to lowercase

**Examples:**
- "Insomnia - Radio Edit" → "insomnia"
- "Praise You (Radio Edit)" → "praise you"
- "Galvanize - Chris Lake Remix" → "galvanize"

#### 2. Fuzzy Matching

```python
def is_duplicate(track1_name, track2_name, threshold=0.85):
    """Check if tracks are duplicates using similarity matching"""
```

Uses `difflib.SequenceMatcher` to catch:
- Minor spelling variations
- Extra whitespace
- Slight differences in formatting

Threshold of 0.85 (85% similarity) balances accuracy vs over-filtering.

#### 3. Best Version Selection

```python
def select_best_version(duplicate_tracks):
    """Select the best version from duplicates"""
```

**Selection criteria (in priority order):**

1. **Original over remixes/edits**
   - Penalizes: "remix" (-20), "mix" (-15), "edit" (-10), "remaster" (-5)

2. **Longer versions (full versions)**
   - Prefers full tracks over radio edits
   - Uses `duration_ms` to score

3. **Popularity**
   - Uses Spotify popularity score
   - Weighted 0.5x to balance with other factors

**Example scoring:**
```
Track: "Insomnia - Radio Edit" (64 popularity, 3:30 duration)
Score: -10 (edit penalty) + 210 (duration) + 32 (popularity) = 232

Track: "Insomnia - Monster Mix" (50 popularity, 8:37 duration)
Score: -15 (mix penalty) + 517 (duration) + 25 (popularity) = 527

→ Winner: "Insomnia - Monster Mix" (longer, more complete)
```

#### 4. Results

**From first test run:**
```
Total tracks before filtering: 120
Duplicates removed: 10
Tracks after filtering: 110

Filtered versions:
✓ Insomnia: Monster Mix > Radio Edit
✓ Where's Your Head At: Original > Radio Edit
✓ Praise You: Full > Radio Edit
✓ Galvanize: Original > Chris Lake Remix
✓ Get Lucky: Full > Radio Edit
✓ Born Slippy: Full > Radio Edit
✓ Hayling: Original > (2 remixes)
```

## Artist Mixing

### Problem

Original script grouped all tracks by artist:
```
1-4: Faithless tracks
5-8: Basement Jaxx tracks
9-12: Fatboy Slim tracks
...
```

This creates monotonous listening - no variety or flow.

### Solution: Round-Robin Distribution

```python
def simple_artist_mix(tracks):
    """Distribute artists evenly throughout playlist"""
```

**Algorithm:**
1. Group tracks by artist
2. Take 1 track from each artist in rotation
3. Repeat until all tracks distributed

**Result:**
```
1. Faithless - Insomnia
2. Basement Jaxx - Where's Your Head At
3. Fatboy Slim - Praise You
4. Groove Armada - Superstylin'
5. Chemical Brothers - Hey Boy Hey Girl
...
25. Faithless - God Is a DJ (2nd Faithless track)
26. Basement Jaxx - Red Alert (2nd BJ track)
```

Artists appear 5-6 tracks apart for good variety!

### Advanced: Energy-Based Sequencing

The script also supports audio features-based sequencing (requires Spotify API permissions):

```python
sequenced_tracks = agent.sequence_playlist(tracks, features_map, arc_type='journey')
```

**Arc types:**
- `balanced`: Consistent energy
- `build`: Low → High
- `journey`: Mid → Peak → Wind down
- `energize`: Start strong, maintain
- `wind_down`: High → Low

Uses tempo, energy, valence, danceability for smooth transitions.

**Note:** Current implementation falls back to artist mixing if audio features unavailable (403 error).

## Usage

### In Your Scripts

```python
from spotify_agent import SpotifyPlaylistAgent

# Collect tracks
all_tracks = []
for artist in LINEUP:
    tracks = agent.get_tracks_for_artist(artist, track_count=6)
    all_tracks.extend(tracks)

# Filter duplicates
filtered = filter_duplicate_tracks(all_tracks, verbose=True)

# Mix artists
mixed = simple_artist_mix(filtered)

# Create playlist
agent.create_playlist(...)
agent.add_tracks_to_playlist(playlist_id, track_uris)
```

### Command Line

```bash
# Create playlist with duplicate filtering and mixing
python3 faithless_synthony_funky_v2.py

# Adjust tracks per artist (before filtering)
# Edit tracks_per_artist parameter in script
```

## Key Parameters

### Duplicate Detection

- **Normalization patterns**: List of regex patterns for version indicators
- **Similarity threshold**: 0.85 (85% match) for fuzzy matching
- **Verbose mode**: Shows duplicate detection details

### Version Selection

- **Remix penalty**: -20 points
- **Mix penalty**: -15 points
- **Edit penalty**: -10 points
- **Remaster penalty**: -5 points
- **Duration weight**: duration_ms / 10000
- **Popularity weight**: 0.5x

### Artist Mixing

- **Distribution**: Round-robin across all artists
- **Spacing**: Automatic based on number of artists

## Benefits

### 1. No Redundancy
- Only one version per song
- Cleaner, more professional playlists
- No listener fatigue from repetition

### 2. Better Flow
- Artists distributed throughout
- Genre/vibe variety
- Maintains listener engagement

### 3. Quality Selection
- Prefers original versions
- Longer, full versions over radio edits
- Balances popularity with completeness

### 4. Scalability
- Works with any number of artists
- Handles large track collections (100+ tracks)
- Efficient O(n²) fuzzy matching

## Future Enhancements

### Potential Improvements

1. **Live vs Studio Detection**
   - Identify live recordings
   - User preference for live/studio

2. **Explicit Content Filtering**
   - Option to filter explicit versions
   - Keep clean versions for certain contexts

3. **Year Preferences**
   - Prefer specific decades
   - Original release vs remaster

4. **Collaborative Artist Handling**
   - Better handling of "feat." tracks
   - Avoid duplicates across collaborations

5. **User Preference Learning**
   - Track which versions users skip
   - Adjust selection algorithm

## Testing

Test with known duplicate-heavy artists:
- Faithless (multiple Insomnia versions)
- Daft Punk (Radio Edit vs Album versions)
- Massive Attack (many remasters)
- The Prodigy (lots of remixes)

Verify:
- [x] Radio edits filtered correctly
- [x] Remixes filtered when original exists
- [x] Popularity considered but not dominant
- [x] Longer versions preferred
- [x] Artist mixing working

## References

- Python `difflib.SequenceMatcher` for fuzzy matching
- Spotify Web API track objects
- Regular expressions for pattern matching

---

**Created:** 2026-01-18
**Version:** 1.0
**Author:** Claude Sonnet 4.5
