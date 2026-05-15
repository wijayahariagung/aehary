from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageOps, ImageChops
import numpy as np

def remove_white_bg(img, threshold=238):
    img = img.convert("RGBA")
    data = np.array(img, dtype=np.float32)
    r, g, b = data[:,:,0], data[:,:,1], data[:,:,2]
    # White mask - pixels close to white
    whiteness = (r + g + b) / 3
    is_white = (r > threshold) & (g > threshold) & (b > threshold)
    # Also catch near-grey background
    saturation = np.max(data[:,:,:3], axis=2) - np.min(data[:,:,:3], axis=2)
    low_sat_bright = (whiteness > 225) & (saturation < 18)
    mask = is_white | low_sat_bright
    result = data.copy()
    result[:,:,3] = np.where(mask, 0, 255)
    # Feather edges
    alpha_img = Image.fromarray(result[:,:,3].astype(np.uint8), 'L')
    alpha_img = alpha_img.filter(ImageFilter.MaxFilter(3))
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(1.2))
    result[:,:,3] = np.array(alpha_img)
    return Image.fromarray(result.astype(np.uint8), 'RGBA')

def make_ground_shadow(char, clinic_brightness=0.65, blur=18, squish=0.22):
    """Realistic elliptical ground shadow."""
    alpha = np.array(char.split()[3])
    # Collapse to bottom strip to simulate ground contact
    shadow_h = max(1, int(char.height * squish))
    shadow_w = int(char.width * 1.1)
    # Project alpha to bottom
    col_alpha = alpha.max(axis=0)
    col_alpha = np.clip(col_alpha.astype(float) * 0.7, 0, 200)
    # Build shadow strip
    shadow = np.zeros((shadow_h, shadow_w, 4), dtype=np.uint8)
    for y in range(shadow_h):
        fade = 1.0 - y / shadow_h
        row_alpha = (col_alpha * fade).astype(np.uint8)
        x_offset = (shadow_w - len(row_alpha)) // 2
        end = min(x_offset + len(row_alpha), shadow_w)
        actual_len = end - x_offset
        shadow[y, x_offset:end, 3] = row_alpha[:actual_len]
    shadow_img = Image.fromarray(shadow, 'RGBA')
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(blur))
    return shadow_img

def color_grade(char, warmth=0.06, brightness=0.97):
    """Tint character to match warm clinic lighting."""
    arr = np.array(char.convert("RGBA"), dtype=np.float32)
    arr[:,:,0] = np.clip(arr[:,:,0] * (1 + warmth), 0, 255)   # warm R
    arr[:,:,1] = np.clip(arr[:,:,1] * (1 + warmth * 0.4), 0, 255)
    arr[:,:,:3] = np.clip(arr[:,:,:3] * brightness, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), 'RGBA')

# ── Load images ──────────────────────────────────────────────────────────────
clinic = Image.open("dental_clinic.png").convert("RGBA")
labubu_grid = Image.open("labubu.jpg").convert("RGBA")

cw, ch = clinic.size
lw, lh = labubu_grid.size

# Upscale clinic 2× for crisp output
clinic = clinic.resize((cw * 2, ch * 2), Image.LANCZOS)
cw, ch = clinic.size

# ── Crop characters from 3×3 grid ────────────────────────────────────────────
cell_w = lw // 3
cell_h = lh // 3

# Picks: (row, col) → colors
picks = [
    (0, 2),  # brown   — furthest back (closest to door)
    (1, 2),  # cream
    (0, 1),  # green
    (1, 0),  # blue/grey
    (0, 0),  # pink    — front of queue (furthest from door)
]

chars = []
for row, col in picks:
    x1 = col * cell_w
    y1 = row * cell_h
    crop = labubu_grid.crop((x1, y1, x1 + cell_w, y1 + cell_h))
    crop = remove_white_bg(crop)
    # ── FLIP to face RIGHT (toward entrance) ──────────────────────────────
    crop = ImageOps.mirror(crop)
    crop = color_grade(crop)
    chars.append(crop)

# ── Layout: linear queue along sidewalk, right = closer to door ─────────────
# Sidewalk baseline (bottom of feet)
baseline_y = int(ch * 0.845)

# Each successive character in queue is slightly further back = smaller + higher
base_h = int(ch * 0.26)      # front character height
depth_step = 0.06            # each character is 6% smaller as they go back

# X positions: queue stretches left from the door (right side ~75%) toward left
door_x = int(cw * 0.70)
char_spacing = int(cw * 0.13)

result = clinic.copy()

# Render front-to-back so back chars go UNDER front chars
for i in range(len(chars)):
    char = chars[i]
    depth = 1.0 - i * depth_step   # front=1.0, back gets smaller

    h = int(base_h * depth)
    w = int(char.width * (h / char.height))
    char_scaled = char.resize((w, h), Image.LANCZOS)

    # Ground shadow
    shadow = make_ground_shadow(char_scaled, blur=int(14 * depth))
    sx = door_x - i * char_spacing - shadow.width // 2 + int(w * 0.05)
    sy = baseline_y - int(shadow.height * 0.15)
    if sx >= 0 and sy >= 0 and sx + shadow.width <= cw and sy + shadow.height <= ch:
        result.alpha_composite(shadow, dest=(sx, sy))

    # Character — feet sit on baseline
    x = door_x - i * char_spacing - w // 2
    y = baseline_y - h
    if x >= 0 and x + w <= cw:
        result.alpha_composite(char_scaled, dest=(x, y))

# ── Final color grade ─────────────────────────────────────────────────────────
final = result.convert("RGB")
final = ImageEnhance.Color(final).enhance(1.06)
final = ImageEnhance.Contrast(final).enhance(1.04)
final = ImageEnhance.Sharpness(final).enhance(1.2)

final.save("dental_labubu_queue.png", "PNG")
print(f"Done! {final.size[0]}x{final.size[1]}px")
