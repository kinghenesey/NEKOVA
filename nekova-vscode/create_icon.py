import struct
import zlib
import math


def create_png(width, height, pixels):
    def chunk(name, data):
        c = zlib.crc32(name + data) & 0xffffffff
        return (struct.pack('>I', len(data)) + name +
                data + struct.pack('>I', c))

    ihdr = struct.pack('>IIBBBBB',
                       width, height, 8, 2, 0, 0, 0)
    raw = b''
    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            r, g, b = pixels[y][x]
            raw += bytes([r, g, b])

    compressed = zlib.compress(raw)
    png  = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', ihdr)
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    return png


def make_icon(size=128):
    pixels = []

    cx = size // 2
    cy = size // 2
    r  = size // 2 - 2

    for y in range(size):
        row = []
        for x in range(size):
            dx   = x - cx
            dy   = y - cy
            dist = math.sqrt(dx * dx + dy * dy)

            # Background
            bg = (13, 13, 26)

            # Outer glow ring
            if r - 3 <= dist <= r:
                t = 1 - abs(dist - (r - 1.5)) / 1.5
                t = max(0, min(1, t))
                row.append((
                    int(0   * t + bg[0] * (1-t)),
                    int(212 * t + bg[1] * (1-t)),
                    int(255 * t + bg[2] * (1-t)),
                ))
                continue

            # Inner circle fill
            if dist < r - 3:
                # Dark blue inner
                inner = (16, 16, 40)

                # Draw letter A
                # Left diagonal of A
                angle = math.atan2(dy, dx)
                norm_x = dx / r
                norm_y = dy / r

                # A letter shape
                in_a = False

                # Left leg of A
                if (-0.45 <= norm_x <= -0.15 and
                        -0.5 <= norm_y <= 0.5):
                    # diagonal line
                    expected_x = norm_y * 0.3 - 0.35
                    if abs(norm_x - expected_x) < 0.08:
                        in_a = True

                # Right leg of A
                if (0.15 <= norm_x <= 0.45 and
                        -0.5 <= norm_y <= 0.5):
                    expected_x = -norm_y * 0.3 + 0.35
                    if abs(norm_x - expected_x) < 0.08:
                        in_a = True

                # Crossbar of A
                if (-0.2 <= norm_x <= 0.2 and
                        0.0 <= norm_y <= 0.15):
                    in_a = True

                if in_a:
                    # Bright cyan for letter
                    row.append((0, 212, 255))
                else:
                    # Subtle gradient background
                    grad = int(16 + dist / r * 10)
                    row.append((grad, grad, grad + 20))
                continue

            row.append(bg)
        pixels.append(row)

    return pixels


# Generate 128x128 icon
pixels = make_icon(128)
png    = create_png(128, 128, pixels)

with open('icon.png', 'wb') as f:
    f.write(png)

print('✓ NEKOVA icon created! (128x128)')

# Also generate smaller sizes
for size in [64, 32]:
    pixels = make_icon(size)
    png    = create_png(size, size, pixels)
    with open(f'icon_{size}.png', 'wb') as f:
        f.write(png)
    print(f'✓ icon_{size}.png created!')