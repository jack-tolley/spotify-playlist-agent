"""
Upload a custom image to a Spotify playlist.

Usage:
    python upload_image.py <image_path> [playlist_id]

Arguments:
    image_path   - Path to image file (JPEG, max 256KB)
    playlist_id  - Optional. Defaults to Synthony 2026 playlist

Example:
    python upload_image.py ./cover.jpg
    python upload_image.py ./cover.jpg YOUR_PLAYLIST_ID
"""

import sys
import base64
import os

# Add parent directory to path if running as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_agent import SpotifyPlaylistAgent

DEFAULT_PLAYLIST_ID = "YOUR_PLAYLIST_ID_HERE"


def upload_playlist_image(image_path, playlist_id=None):
    if not playlist_id:
        playlist_id = DEFAULT_PLAYLIST_ID

    # Validate playlist ID is set
    if playlist_id == "YOUR_PLAYLIST_ID_HERE":
        print("\nError: Playlist ID not configured")
        print("\nPlease provide a playlist ID:")
        print("  python upload_image.py <image_path> <playlist_id>")
        print("\nExample:")
        print("  python upload_image.py cover.jpg 2lCjcqHl8RPjtI9NEY0pyb")
        return False

    # Validate image file
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return False

    # Check file size (max 256KB)
    file_size = os.path.getsize(image_path)
    if file_size > 256 * 1024:
        print(f"Error: Image too large ({file_size / 1024:.1f}KB). Max is 256KB.")
        print("Tip: Resize or compress the image first.")
        return False

    # Read and encode image as base64
    with open(image_path, 'rb') as f:
        image_data = f.read()

    image_base64 = base64.b64encode(image_data).decode('utf-8')

    # Authenticate
    agent = SpotifyPlaylistAgent()

    print(f"\nUploading playlist cover image...")
    print(f"  Image: {image_path}")
    print(f"  Size: {file_size / 1024:.1f}KB")
    print(f"  Playlist: https://open.spotify.com/playlist/{playlist_id}")

    if not agent.is_authenticated():
        if not agent.authenticate():
            print("Authentication failed!")
            return False

    # Upload image via Spotify API
    # Note: This endpoint requires image/jpeg content-type and raw base64 body
    import requests

    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/images"
    headers = {
        'Authorization': f'Bearer {agent.access_token}',
        'Content-Type': 'image/jpeg'
    }

    response = requests.put(url, headers=headers, data=image_base64)

    if response.status_code == 202:
        print("\n✓ Image uploaded successfully!")
        print(f"  View playlist: https://open.spotify.com/playlist/{playlist_id}")
        return True
    else:
        print(f"\nError uploading image: {response.status_code}")
        print(response.text)
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    image_path = sys.argv[1]
    playlist_id = sys.argv[2] if len(sys.argv) > 2 else None

    upload_playlist_image(image_path, playlist_id)


if __name__ == '__main__':
    main()
