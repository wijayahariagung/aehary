#!/usr/bin/env python3
"""
Composite Labubu characters queuing in front of dental clinic.
Usage: python3 composite.py
Requires: dental_clinic.jpg, labubu.png in same directory
"""

from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import os
import sys

CLINIC_PATH = "dental_clinic.jpg"
LABUBU_PATH = "labubu.png"
OUTPUT_PATH = "dental_labubu_queue.png"

# Labubu positions in the source image (row, col) 0-indexed in 3x3 grid
# We'll crop individual characters from the grid
GRID_ROWS = 3
GRID_COLS = 3


def crop_labubu_characters(labubu_img):
    """Extract individual Labubu characters from the grid image."""
    w, h = labubu_img.size
    cell_w = w // GRID_COLS
    cell_h = h // GRID_ROWS

    characters = []
    # Pick specific characters for the queue (varied colors look nice)
    picks = [
        (0, 0),  # pink
        (0, 1),  # green
        (1, 0),  # blue/grey
        (2, 2),  # grey
        (0, 2),  # brown
    ]

    for row, col in picks:
        x = col * cell_w
        y = row * cell_h
        char = labubu_img.crop((x, y, x + cell_w, y + cell_h))
        # Remove white background
        char = remove_white_background(char)
        characters.append(char)

    return characters


def remove_white_background(img, threshold=230):
    """Convert near-white pixels to transparent."""
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r > threshold and g > threshold and b > threshold:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def add_shadow(char_img, offset=(8, 12), blur_radius=10, opacity=120):
    """Add a drop shadow beneath a character."""
    shadow_layer = Image.new("RGBA", char_img.size, (0, 0, 0, 0))
    alpha = char_img.split()[3]

    # Create shadow from alpha
    shadow = Image.new("RGBA", char_img.size, (0, 0, 0, 0))
    for x in range(char_img.width):
        for y in range(char_img.height):
            a = alpha.getpixel((x, y))
            if a > 50:
                shadow.putpixel((x, y), (30, 30, 30, int(a * opacity / 255)))

    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
    return shadow


def composite_scene(clinic_path, labubu_path, output_path):
    clinic = Image.open(clinic_path).convert("RGBA")
    labubu_src = Image.open(labubu_path).convert("RGBA")

    clinic_w, clinic_h = clinic.size

    # Extract characters
    characters = crop_labubu_characters(labubu_src)

    # Scale characters to look like they're standing on the sidewalk
    # The sidewalk starts roughly at 80% of clinic height
    sidewalk_y = int(clinic_h * 0.80)
    char_target_h = int(clinic_h * 0.22)  # characters ~22% of clinic height

    # Queue layout: spread characters across the front of the clinic
    num_chars = len(characters)
    # Center the queue on the clinic front door area (roughly 35%-65% width)
    queue_start_x = int(clinic_w * 0.25)
    queue_end_x = int(clinic_w * 0.75)
    spacing = (queue_end_x - queue_start_x) // (num_chars - 1) if num_chars > 1 else 0

    result = clinic.copy()

    # Place characters from back to front (right to left = further back)
    # Characters closer to center are slightly larger (forced perspective)
    for i, char in enumerate(reversed(characters)):
        # Scale with slight perspective: front chars bigger
        depth_scale = 0.85 + (i / (num_chars - 1)) * 0.20
        h = int(char_target_h * depth_scale)
        ratio = h / char.height
        w = int(char.width * ratio)
        char_resized = char.resize((w, h), Image.LANCZOS)

        x = queue_start_x + i * spacing - w // 2
        # Bottom of character sits on sidewalk line, adjusted by depth
        y_offset = int((1 - depth_scale) * 20)
        y = sidewalk_y - h + y_offset

        # Add shadow
        shadow = add_shadow(char_resized)
        shadow_x = x + 6
        shadow_y = y + 10

        # Paste shadow first
        result.alpha_composite(shadow, dest=(shadow_x, shadow_y))
        # Then paste character
        result.alpha_composite(char_resized, dest=(x, y))

    # Convert to RGB for JPEG-quality output, keep PNG for transparency
    result_rgb = Image.new("RGB", result.size, (255, 255, 255))
    result_rgb.paste(result, mask=result.split()[3])

    # Enhance final image
    result_rgb = ImageEnhance.Sharpness(result_rgb).enhance(1.1)
    result_rgb = ImageEnhance.Color(result_rgb).enhance(1.05)

    result_rgb.save(output_path, "PNG", optimize=True)
    print(f"Saved: {output_path} ({result_rgb.size[0]}x{result_rgb.size[1]}px)")
    return output_path


if __name__ == "__main__":
    missing = [f for f in [CLINIC_PATH, LABUBU_PATH] if not os.path.exists(f)]
    if missing:
        print(f"Missing files: {missing}")
        sys.exit(1)

    out = composite_scene(CLINIC_PATH, LABUBU_PATH, OUTPUT_PATH)
    print(f"Done! Output: {out}")
