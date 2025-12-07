from PIL import Image, ImageDraw, ImageFont

def generate_playlist_cover(text, output_path="playlist_cover.jpg", width=600, height=600, bg_color=(70, 130, 180), text_color=(255, 255, 255)):
    """
    Generates a simple image with text for a playlist cover.

    Args:
        text (str): The text to display on the cover.
        output_path (str): The path to save the generated image.
        width (int): The width of the image.
        height (int): The height of the image.
        bg_color (tuple): RGB tuple for the background color.
        text_color (tuple): RGB tuple for the text color.
    """
    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)

    try:
        # Try to use a default system font if available, otherwise use a generic sans-serif
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
        print("Could not load arial.ttf, using default font.")

    # Calculate text size and position to center it
    bbox = d.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) / 2
    y = (height - text_height) / 2 - 10 # Adjust slightly upwards

    d.text((x, y), text, fill=text_color, font=font)
    img.save(output_path)
    print(f"Generated playlist cover saved to {output_path}")

if __name__ == "__main__":
    playlist_name = input("Enter playlist name for the cover (e.g., 'My Awesome Playlist'): ")
    if not playlist_name:
        playlist_name = "Synthwave Vibes" # Default if nothing is entered

    generate_playlist_cover(playlist_name)
