'''Replace the app logo with any image (PNG, JPG, WEBP, ...).

Usage:
    python tools/set_logo.py <image> [--crop] [--round 22] [--preview preview.png]

Writes assets/emaahhhpilot_logo.png (512x512) and assets/emaahhhpilot_logo.ico
(16-256 px). A non-square image is centred on a transparent square (nothing is cut);
with --crop it is centre-cropped to a square instead. --round N cuts the corners to a
rounded square (N = corner radius in % of the side, like modern app icons).
'''
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_PNG = ROOT / 'assets' / 'emaahhhpilot_logo.png'
OUT_ICO = ROOT / 'assets' / 'emaahhhpilot_logo.ico'
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def to_square(img, crop):
    w, h = img.size
    if w == h:
        return img
    if crop:
        side = min(w, h)
        left, top = (w - side) // 2, (h - side) // 2
        return img.crop((left, top, left + side, top + side))
    side = max(w, h)
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2), img)
    return canvas


def round_corners(img, percent):
    '''Rounded-square alpha mask, drawn at 4x and scaled down for smooth edges.'''
    side = img.size[0]
    big = side * 4
    mask = Image.new('L', (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1], radius = int(big * percent / 100), fill = 255)
    mask = mask.resize((side, side), Image.LANCZOS)
    out = img.copy()
    out.putalpha(Image.composite(img.getchannel('A'), Image.new('L', (side, side), 0), mask))
    return out


def main():
    ap = argparse.ArgumentParser(description = 'Set the app logo from an image.')
    ap.add_argument('image')
    ap.add_argument('--crop', action = 'store_true', help = 'centre-crop to a square instead of padding')
    ap.add_argument('--round', type = float, default = 0, help = 'corner radius in %% of the side (0 = square)')
    ap.add_argument('--preview', help = 'also write a preview sheet (512 + 64/32/16 px) here')
    args = ap.parse_args()

    img = Image.open(args.image).convert('RGBA')
    square = to_square(img, args.crop)
    if args.round > 0:
        square = round_corners(square, args.round)
    big = square.resize((512, 512), Image.LANCZOS)
    big.save(OUT_PNG)
    square.resize((256, 256), Image.LANCZOS).save(OUT_ICO, sizes = ICO_SIZES)
    print(f'logo: {OUT_PNG.name} (512x512), {OUT_ICO.name} ({len(ICO_SIZES)} sizes) from {img.size[0]}x{img.size[1]}')

    if args.preview:
        sheet = Image.new('RGBA', (512 + 20 + 64 + 20 + 32 + 20 + 16 + 20, 512), (30, 30, 34, 255))
        sheet.paste(big, (0, 0), big)
        x = 532
        for n in (64, 32, 16):
            small = square.resize((n, n), Image.LANCZOS)
            sheet.paste(small, (x, 20), small)
            x += n + 20
        sheet.save(args.preview)
        print(f'preview: {args.preview}')


if __name__ == '__main__':
    main()
