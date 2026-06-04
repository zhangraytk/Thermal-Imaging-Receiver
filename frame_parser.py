import struct

FRAME_PREFIX = b"BEGIN"
FRAME_SUFFIX = b"END"

TARGET_WIDTH = 32
TARGET_HEIGHT = 24
TARGET_PIXEL_COUNT = TARGET_WIDTH * TARGET_HEIGHT

LOW_RES_WIDTH = 16
LOW_RES_HEIGHT = 12
LOW_RES_PIXEL_COUNT = LOW_RES_WIDTH * LOW_RES_HEIGHT


class FrameParseError(ValueError):
    """Raised when a serial packet is not a complete thermal frame."""


def upsample_bilinear(src, src_width, src_height, dst_width, dst_height):
    out = []
    for dst_y in range(dst_height):
        src_y = dst_y * (src_height - 1) / (dst_height - 1)
        y0 = int(src_y)
        y1 = min(y0 + 1, src_height - 1)
        wy = src_y - y0
        for dst_x in range(dst_width):
            src_x = dst_x * (src_width - 1) / (dst_width - 1)
            x0 = int(src_x)
            x1 = min(x0 + 1, src_width - 1)
            wx = src_x - x0
            v00 = src[y0 * src_width + x0]
            v01 = src[y0 * src_width + x1]
            v10 = src[y1 * src_width + x0]
            v11 = src[y1 * src_width + x1]
            out.append(
                (1 - wx) * (1 - wy) * v00
                + wx * (1 - wy) * v01
                + (1 - wx) * wy * v10
                + wx * wy * v11
            )
    return out


def parse_frame_packet(packet):
    if not packet.startswith(FRAME_PREFIX) or not packet.endswith(FRAME_SUFFIX):
        raise FrameParseError("packet does not have BEGIN/END markers")

    payload = packet[len(FRAME_PREFIX):-len(FRAME_SUFFIX)]
    if len(payload) < 12 or len(payload) % 4 != 0:
        raise FrameParseError(f"invalid payload length: {len(payload)}")

    num_floats = len(payload) // 4
    try:
        values = struct.unpack(f"<{num_floats}f", payload)
    except struct.error as exc:
        raise FrameParseError(str(exc)) from exc

    header = values[:3]
    pixels = values[3:]
    pixel_count = len(pixels)

    if pixel_count == TARGET_PIXEL_COUNT:
        return tuple(values)

    if pixel_count == LOW_RES_PIXEL_COUNT:
        upsampled = upsample_bilinear(
            pixels,
            LOW_RES_WIDTH,
            LOW_RES_HEIGHT,
            TARGET_WIDTH,
            TARGET_HEIGHT,
        )
        return tuple(header + tuple(upsampled))

    raise FrameParseError(f"unsupported pixel count: {pixel_count}")
