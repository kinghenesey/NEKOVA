import struct
import zlib

def create_png(width, height, color):
    def chunk(name, data):
        c = zlib.crc32(name + data) & 0xffffffff
        return (struct.pack('>I', len(data)) + name +
                data + struct.pack('>I', c))

    ihdr = struct.pack('>IIBBBBB',
                       width, height, 8, 2, 0, 0, 0)
    r, g, b = color
    raw = b''

    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            cx   = x - width // 2
            cy   = y - height // 2
            dist = (cx * cx + cy * cy) ** 0.5

            if dist < width // 2 - 4:
                # Cyan circle
                raw += bytes([r, g, b])
            else:
                # Dark background
                raw += bytes([13, 13, 26])

    compressed = zlib.compress(raw)
    png  = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', ihdr)
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    return png

with open('icon.png', 'wb') as f:
    f.write(create_png(128, 128, (0, 212, 255)))

print('Icon created successfully!')