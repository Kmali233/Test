#!/usr/bin/env python3
"""Generate a 16-second anime programmer daily-life AVI video.

The generator intentionally uses only Python's standard library so it can run in
minimal environments without Pillow, ffmpeg, or network access.  It renders a
small vector-style storyboard and writes an uncompressed 24-bit AVI file.
"""

from __future__ import annotations

import math
import os
import struct
from pathlib import Path

WIDTH = 320
HEIGHT = 180
FPS = 8
DURATION_SECONDS = 16
TOTAL_FRAMES = FPS * DURATION_SECONDS
OUTPUT = Path("media/anime_programmer_daily_life.avi")

RGB = tuple[int, int, int]


FONT: dict[str, list[str]] = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    " ": ["000", "000", "000", "000", "000", "000", "000"],
    ".": ["0", "0", "0", "0", "0", "0", "1"],
    ":": ["0", "1", "0", "0", "0", "1", "0"],
    "-": ["000", "000", "000", "111", "000", "000", "000"],
    ">": ["100", "010", "001", "010", "100", "000", "000"],
}


class Canvas:
    def __init__(self, w: int, h: int, bg: RGB) -> None:
        self.w = w
        self.h = h
        self.data = bytearray(bg * (w * h))

    def set_pixel(self, x: int, y: int, color: RGB, alpha: float = 1.0) -> None:
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        i = (y * self.w + x) * 3
        if alpha >= 1:
            self.data[i : i + 3] = bytes(color)
        else:
            inv = 1 - alpha
            self.data[i] = int(self.data[i] * inv + color[0] * alpha)
            self.data[i + 1] = int(self.data[i + 1] * inv + color[1] * alpha)
            self.data[i + 2] = int(self.data[i + 2] * inv + color[2] * alpha)

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: RGB, alpha: float = 1.0) -> None:
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.set_pixel(x, y, color, alpha)

    def ellipse(self, cx: int, cy: int, rx: int, ry: int, color: RGB, alpha: float = 1.0) -> None:
        if rx <= 0 or ry <= 0:
            return
        for y in range(cy - ry, cy + ry + 1):
            yy = ((y - cy) / ry) ** 2
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + yy <= 1:
                    self.set_pixel(x, y, color, alpha)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: RGB, width: int = 1, alpha: float = 1.0) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            t = s / steps
            x = round(x0 + (x1 - x0) * t)
            y = round(y0 + (y1 - y0) * t)
            self.ellipse(x, y, width, width, color, alpha)

    def polygon(self, pts: list[tuple[int, int]], color: RGB, alpha: float = 1.0) -> None:
        min_y = max(0, min(y for _, y in pts))
        max_y = min(self.h - 1, max(y for _, y in pts))
        for y in range(min_y, max_y + 1):
            xs: list[float] = []
            for i, (x1, y1) in enumerate(pts):
                x2, y2 = pts[(i + 1) % len(pts)]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for a, b in zip(xs[0::2], xs[1::2]):
                for x in range(max(0, int(math.ceil(a))), min(self.w, int(math.floor(b)) + 1)):
                    self.set_pixel(x, y, color, alpha)

    def text(self, x: int, y: int, text: str, color: RGB, scale: int = 1) -> None:
        cx = x
        for ch in text.upper():
            glyph = FONT.get(ch, FONT[" "])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        self.rect(cx + gx * scale, y + gy * scale, cx + (gx + 1) * scale, y + (gy + 1) * scale, color)
            cx += (len(glyph[0]) + 1) * scale

    def gradient_sky(self, top: RGB, bottom: RGB) -> None:
        for y in range(self.h):
            t = y / max(1, self.h - 1)
            col = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
            self.rect(0, y, self.w, y + 1, col)


def draw_flower(c: Canvas, x: int, y: int, s: int) -> None:
    for a in range(0, 360, 72):
        c.ellipse(x + int(math.cos(math.radians(a)) * s), y + int(math.sin(math.radians(a)) * s), s, max(1, s // 2), (248, 242, 255), 0.9)
    c.ellipse(x, y, max(1, s // 2), max(1, s // 2), (225, 196, 109))


def draw_girl(c: Canvas, x: int, y: int, scale: float, pose: float = 0.0, book: bool = True) -> None:
    s = scale
    # coat and body
    c.polygon([(int(x - 22*s), int(y + 32*s)), (int(x + 22*s), int(y + 32*s)), (int(x + 32*s), int(y + 92*s)), (int(x - 32*s), int(y + 92*s))], (248, 246, 255), 0.96)
    c.polygon([(int(x - 15*s), int(y + 43*s)), (int(x + 15*s), int(y + 43*s)), (int(x + 20*s), int(y + 64*s)), (int(x - 20*s), int(y + 64*s))], (170, 138, 215), 0.95)
    c.rect(int(x - 17*s), int(y + 54*s), int(x + 17*s), int(y + 60*s), (132, 102, 184), 0.7)
    for gx in range(-12, 18, 8):
        c.line(int(x + gx*s), int(y + 44*s), int(x + gx*s), int(y + 64*s), (219, 202, 238), 1)
    # legs and boots
    step = math.sin(pose) * 8 * s
    for dx in (-10*s, 10*s):
        c.line(int(x + dx), int(y + 66*s), int(x + dx + step * (1 if dx < 0 else -1)), int(y + 116*s), (245, 218, 213), max(1, int(3*s)))
        c.rect(int(x + dx - 7*s), int(y + 112*s), int(x + dx + 8*s), int(y + 126*s), (248, 246, 255))
        c.rect(int(x + dx - 9*s), int(y + 123*s), int(x + dx + 11*s), int(y + 131*s), (150, 118, 201))
    # arms
    c.line(int(x - 21*s), int(y + 38*s), int(x - 45*s), int(y + 58*s), (248, 246, 255), max(1, int(5*s)))
    c.line(int(x + 22*s), int(y + 38*s), int(x + 43*s), int(y + 62*s), (248, 246, 255), max(1, int(5*s)))
    if book:
        c.polygon([(int(x - 62*s), int(y + 34*s)), (int(x - 35*s), int(y + 26*s)), (int(x - 28*s), int(y + 70*s)), (int(x - 56*s), int(y + 76*s))], (126, 101, 177))
        c.text(int(x - 58*s), int(y + 42*s), "JAVA", (255, 250, 255), max(1, int(s)))
        c.line(int(x - 58*s), int(y + 37*s), int(x - 33*s), int(y + 30*s), (218, 204, 239), 1)
    # neck, face, hair
    c.rect(int(x - 5*s), int(y + 26*s), int(x + 5*s), int(y + 40*s), (250, 221, 218))
    c.ellipse(x, int(y + 16*s), int(27*s), int(34*s), (172, 133, 210), 0.85)
    c.ellipse(x, int(y + 22*s), int(20*s), int(24*s), (255, 226, 224))
    c.ellipse(int(x - 8*s), int(y + 20*s), max(1, int(2*s)), max(1, int(3*s)), (116, 80, 176))
    c.ellipse(int(x + 8*s), int(y + 20*s), max(1, int(2*s)), max(1, int(3*s)), (116, 80, 176))
    c.line(int(x - 7*s), int(y + 31*s), int(x + 7*s), int(y + 31*s), (218, 117, 151), 1)
    for k in range(7):
        off = (k - 3) * 7 * s + math.sin(pose + k) * 2
        c.line(int(x + off), int(y - 4*s), int(x + off * 1.35), int(y + 82*s + math.sin(pose + k) * 9), (137, 102, 190), max(1, int(2*s)), 0.65)
    draw_flower(c, int(x + 19*s), int(y + 2*s), max(2, int(4*s)))
    draw_flower(c, int(x - 21*s), int(y + 10*s), max(2, int(3*s)))


def draw_window_scene(c: Canvas, frame: int) -> None:
    c.gradient_sky((255, 249, 243), (232, 221, 255))
    c.rect(25, 18, 132, 94, (255, 255, 255), 0.7)
    c.rect(29, 22, 128, 90, (255, 244, 207), 0.5)
    c.line(78, 18, 78, 94, (223, 206, 238), 2)
    c.line(25, 56, 132, 56, (223, 206, 238), 2)
    c.rect(0, 120, WIDTH, 180, (238, 227, 247))
    c.rect(38, 106, 268, 128, (211, 176, 221))
    c.rect(55, 126, 63, 180, (166, 132, 192))
    c.rect(242, 126, 250, 180, (166, 132, 192))
    c.rect(183, 85, 249, 122, (226, 219, 236))
    c.rect(189, 91, 243, 116, (126, 111, 160))
    c.text(194, 97, "NOTES", (204, 248, 227), 1)
    c.ellipse(267, 107, 13, 8, (250, 239, 224))
    c.rect(255, 96, 279, 108, (248, 246, 255))
    c.ellipse(267, 96, 11, 4, (187, 141, 97))
    draw_girl(c, 145, 45 + int(math.sin(frame / 8) * 2), 0.78, frame / 7, True)
    c.text(10, 8, "0-5S  MORNING JAVA READING", (126, 91, 173), 1)


def draw_coding_scene(c: Canvas, frame: int) -> None:
    c.gradient_sky((246, 240, 255), (224, 235, 255))
    c.rect(0, 122, WIDTH, 180, (225, 215, 240))
    c.rect(22, 112, 298, 134, (190, 154, 203))
    c.rect(82, 50, 234, 116, (36, 34, 58))
    c.rect(91, 59, 225, 105, (53, 50, 82))
    for i in range(9):
        y = 64 + i * 4
        color = (159, 241, 216) if i % 3 else (218, 195, 252)
        c.rect(103, y, 105 + ((i * 17 + frame) % 90), y + 2, color)
    c.rect(131, 116, 188, 122, (83, 70, 113))
    for n, x in enumerate([35, 57, 260, 280]):
        c.rect(x, 78 + n * 4, x + 22, 96 + n * 4, (255, 247, 166) if n % 2 else (233, 204, 255))
    draw_girl(c, 160, 42, 0.64, frame / 5, False)
    c.line(132, 89, 113, 107, (248, 246, 255), 4)
    c.line(188, 89, 207, 107, (248, 246, 255), 4)
    cursor_x = 111 + (frame % 24) * 4
    c.rect(cursor_x, 102, cursor_x + 3, 108, (255, 248, 170))
    c.text(9, 8, "5-10S  CODING AND NOTE TAKING", (97, 82, 151), 1)
    c.text(98, 140, "SYSTEM.OUT.PRINTLN > SMILE", (126, 91, 173), 1)


def draw_sunset_scene(c: Canvas, frame: int) -> None:
    c.gradient_sky((247, 183, 214), (174, 151, 224))
    for i in range(6):
        c.ellipse(35 + i * 56, 35 + (i % 2) * 10, 25, 7, (255, 223, 237), 0.35)
    c.polygon([(0, 121), (320, 105), (320, 180), (0, 180)], (93, 83, 139), 0.55)
    c.polygon([(120, 120), (204, 114), (254, 180), (63, 180)], (238, 228, 255), 0.8)
    for x in range(15, 315, 45):
        c.line(x, 88, x, 120, (82, 76, 122), 2)
        c.ellipse(x, 86, 4, 4, (255, 237, 168), 0.9)
    walk = frame / 4
    draw_girl(c, 168 + int(math.sin(walk) * 5), 46 + int(math.sin(walk * 1.5) * 1), 0.77, walk, True)
    for k in range(4):
        x = 45 + k * 68 + int((frame * 2) % 24)
        draw_flower(c, x, 139 + k % 2 * 8, 3)
    c.text(8, 8, "10-16S  SUNSET TECH PARK WALK", (255, 247, 255), 1)
    c.text(76, 164, "COZY DAILY LIFE 16 SECONDS", (255, 247, 255), 1)


def render_frame(n: int) -> bytes:
    c = Canvas(WIDTH, HEIGHT, (255, 255, 255))
    if n < FPS * 5:
        draw_window_scene(c, n)
    elif n < FPS * 10:
        draw_coding_scene(c, n - FPS * 5)
    else:
        draw_sunset_scene(c, n - FPS * 10)
    # soft vignette
    cx, cy = WIDTH / 2, HEIGHT / 2
    max_d = math.hypot(cx, cy)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            d = math.hypot(x - cx, y - cy) / max_d
            if d > 0.72:
                c.set_pixel(x, y, (255, 255, 255), min(0.22, (d - 0.72) * 0.8))
    return bytes(c.data)


def make_chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack("<I", len(payload)) + payload + (b"\0" if len(payload) % 2 else b"")


def riff_list(list_type: bytes, payload: bytes) -> bytes:
    return b"LIST" + struct.pack("<I", len(payload) + 4) + list_type + payload + (b"\0" if (len(payload) + 4) % 2 else b"")


def avi_headers(frame_size: int) -> bytes:
    row_size = ((WIDTH * 3 + 3) // 4) * 4
    max_bytes = row_size * HEIGHT
    avih = struct.pack(
        "<IIIIIIIIIIIIII",
        int(1_000_000 / FPS),
        max_bytes * FPS,
        0,
        0x10,
        TOTAL_FRAMES,
        0,
        1,
        max_bytes,
        WIDTH,
        HEIGHT,
        0,
        0,
        0,
        0,
    )
    strh = struct.pack(
        "<4s4sIIIIIIIIIIIIhhhh",
        b"vids",
        b"DIB ",
        0,
        0,
        0,
        0,
        1,
        FPS,
        0,
        TOTAL_FRAMES,
        frame_size,
        0xFFFFFFFF,
        0,
        0,
        0,
        0,
        WIDTH,
        HEIGHT,
    )
    strf = struct.pack(
        "<IIIHHIIIIII",
        40,
        WIDTH,
        HEIGHT,
        1,
        24,
        0,
        frame_size,
        2835,
        2835,
        0,
        0,
    )
    strl = riff_list(b"strl", make_chunk(b"strh", strh) + make_chunk(b"strf", strf))
    hdrl = riff_list(b"hdrl", make_chunk(b"avih", avih) + strl)
    return hdrl


def rgb_to_bottom_up_bgr(rgb: bytes) -> bytes:
    row_stride = WIDTH * 3
    padded_stride = ((row_stride + 3) // 4) * 4
    pad = b"\0" * (padded_stride - row_stride)
    out = bytearray()
    for y in range(HEIGHT - 1, -1, -1):
        row = rgb[y * row_stride : (y + 1) * row_stride]
        for i in range(0, len(row), 3):
            out.extend((row[i + 2], row[i + 1], row[i]))
        out.extend(pad)
    return bytes(out)


def write_avi(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = [rgb_to_bottom_up_bgr(render_frame(n)) for n in range(TOTAL_FRAMES)]
    frame_size = len(frames[0])
    movi_payload = bytearray()
    idx_entries = []
    offset = 4  # relative to the start of the movi list payload, including the 'movi' type
    for frame in frames:
        chunk = make_chunk(b"00db", frame)
        idx_entries.append(struct.pack("<4sIII", b"00db", 0x10, offset, len(frame)))
        movi_payload.extend(chunk)
        offset += len(chunk)
    movi = riff_list(b"movi", bytes(movi_payload))
    idx1 = make_chunk(b"idx1", b"".join(idx_entries))
    body = avi_headers(frame_size) + movi + idx1
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body) + 4) + b"AVI " + body)


if __name__ == "__main__":
    write_avi(OUTPUT)
    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"Generated {OUTPUT} ({DURATION_SECONDS}s, {TOTAL_FRAMES} frames, {WIDTH}x{HEIGHT}, {size_mb:.1f} MiB)")
