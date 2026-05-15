from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import numpy as np

def remove_white_bg(img, threshold=240):
    img = img.convert("RGBA")
    data = np.array(img)
    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
    white_mask = (r > threshold) & (g > threshold) & (b > threshold)
    data[:,:,3] = np.where(white_mask, 0, 255)
    # Soften edges
    result = Image.fromarray(data, 'RGBA')
    return result

def add_drop_shadow(char, blur=12, offset=(10, 16), opacity=0.55):
    shadow = Image.new("RGBA", (char.width + abs(offset[0])*3, char.height + abs(offset[1])*3), (0,0,0,0))
    alpha = char.split()[3]
    shadow_body = Image.new("RGBA", char.size, (0,0,0,0))
    shadow_data = np.zeros((char.height, char.width, 4), dtype=np.uint8)
    alpha_arr = np.array(alpha)
    shadow_data[:,:,3] = (alpha_arr * opacity).astype(np.uint8)
    shadow_body = Image.fromarray(shadow_data, 'RGBA')
    shadow_body = shadow_body.filter(ImageFilter.GaussianBlur(blur))
    result = Image.new("RGBA", shadow.size, (0,0,0,0))
    result.paste(shadow_body, (abs(offset[0]) + offset[0], abs(offset[1]) + offset[1]), shadow_body)
    result.paste(char, (abs(offset[0]), abs(offset[1])), char)
    return result

# Load images
clinic = Image.open("dental_clinic.png").convert("RGBA")
labubu_grid = Image.open("labubu.jpg").convert("RGBA")

cw, ch = clinic.size
lw, lh = labubu_grid.size

# Upscale clinic for better quality output
scale = 2
clinic = clinic.resize((cw * scale, ch * scale), Image.LANCZOS)
cw, ch = clinic.size

# Crop Labubu characters from the 3x3 grid
# Grid: 3 cols x 3 rows
cell_w = lw // 3
cell_h = lh // 3

# Pick 5 characters: row0col0 (pink), row0col1 (green), row1col0 (blue),
# row1col2 (cream), row0col2 (brown)
picks = [
    (0, 0),  # pink - most front
    (0, 1),  # green
    (1, 0),  # blue/grey
    (1, 2),  # cream
    (0, 2),  # brown - furthest back
]

chars = []
for row, col in picks:
    x1 = col * cell_w
    y1 = row * cell_h
    crop = labubu_grid.crop((x1, y1, x1 + cell_w, y1 + cell_h))
    # Remove white background
    crop = remove_white_bg(crop, threshold=235)
    chars.append(crop)

# Place characters in a queue in front of the clinic
# Sidewalk starts around 78% down the clinic height
sidewalk_baseline = int(ch * 0.82)

# Characters heights relative to clinic (with scale)
base_char_h = int(ch * 0.24)

# Queue positions: spread along the lower portion, slight arc to simulate depth
# Characters in the middle are slightly in front
num = len(chars)
# x positions: spread across 20% to 80% of clinic width
xs = [int(cw * (0.20 + i * 0.145)) for i in range(num)]
# Depth effect: middle chars slightly lower and larger
depths = [0.82, 0.88, 1.0, 0.90, 0.84]

result = clinic.copy()

# Draw in reverse order (back to front)
for i in reversed(range(num)):
    char = chars[i]
    depth = depths[i]
    h = int(base_char_h * depth)
    ratio = h / char.height
    w = int(char.width * ratio)
    char_scaled = char.resize((w, h), Image.LANCZOS)

    # Add shadow
    char_with_shadow = add_drop_shadow(char_scaled, blur=int(8 * depth), offset=(int(6*depth), int(10*depth)))

    # Bottom of character on sidewalk baseline
    shadow_offset_y = int(8 * depth)
    shadow_offset_x = int(6 * depth)
    x = xs[i] - char_with_shadow.width // 2 + shadow_offset_x
    y = sidewalk_baseline - char_with_shadow.height + shadow_offset_y + int((1-depth) * 30)

    result.alpha_composite(char_with_shadow, dest=(max(0, x), max(0, y)))

# Add slight vignette
vignette = Image.new("RGBA", result.size, (0,0,0,0))
draw = ImageDraw.Draw(vignette)
for r in range(80, 0, -1):
    alpha = int((80 - r) * 1.2)
    draw.ellipse([
        -cw//4 + r*cw//160, -ch//4 + r*ch//160,
        cw + cw//4 - r*cw//160, ch + ch//4 - r*ch//160
    ], outline=(0,0,0,0))

# Final enhancement
final = result.convert("RGB")
final = ImageEnhance.Color(final).enhance(1.08)
final = ImageEnhance.Contrast(final).enhance(1.05)
final = ImageEnhance.Sharpness(final).enhance(1.15)

final.save("dental_labubu_queue.png", "PNG", optimize=False)
print(f"Done! dental_labubu_queue.png — {final.size[0]}x{final.size[1]}px")
