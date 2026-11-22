'''Build EmaahhhPilot.exe and put it in the project folder.

Usage (from the project folder, with PyInstaller installed):
    python tools/build_exe.py

PyInstaller writes to build/dist; the finished exe is then moved to
<project>/EmaahhhPilot.exe, replacing the previous build. Close the app first:
a running exe cannot be replaced.
'''
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / 'EmaahhhPilot.spec'
STAGING = ROOT / 'build' / 'dist'
TARGET = ROOT / 'EmaahhhPilot.exe'


def main():
    bundle = ROOT / 'tesseract_bundle'
    if not (bundle / 'tesseract.exe').is_file() or not (bundle / 'tessdata' / 'eng.traineddata').is_file():
        sys.exit('tesseract_bundle is missing or incomplete: copy tesseract.exe, its DLLs and '
                 'tessdata/eng.traineddata there first (see README, "Building the exe").')
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', str(STAGING), str(SPEC)]
    print('Running:', ' '.join(cmd))
    subprocess.run(cmd, cwd = ROOT, check = True)
    built = STAGING / TARGET.name
    if not built.is_file():
        sys.exit(f'Build finished but {built} was not found.')
    try:
        if TARGET.exists():
            TARGET.unlink()
    except PermissionError:
        sys.exit(f'{TARGET.name} is running (or locked): close the app and run this again. '
                 f'The new build is at {built}.')
    shutil.move(str(built), str(TARGET))
    print(f'Done: {TARGET} ({TARGET.stat().st_size / 1024 / 1024:.1f} MB)')


if __name__ == '__main__':
    main()
