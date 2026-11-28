"""Vorschauvideo einer Kampfszene wie im Spiel: Angriffs- und Sterbevideo (freigestellte WebP-Bilder aus public/)
übereinander, Opfer bis zum Trefferbild als erstes Bild, danach sein Video, am Ende ausgeblendet; Weiß über Schwarz.
Ton aus den Original-MP4 (oder '-' ohne Ton): Angriff ab 0, Sterben ab dem Treffer.

  python3 tools/ritter/kampf_vorschau.py <angriff-ordner> <angriff.mp4> <tod-ordner> <tod.mp4> <tod-ab> <w|b> <out.mp4>

angriff-/tod-ordner: public/assets/sets/ritter/kampf/{angriff,tod}/<figur>; tod-ab: erstes genommenes Bild des
Sterbevideos (kampf_frames.sh Angabe ab), damit der Ton passt; w|b: Farbe des Angreifers. Braucht Pillow und ffmpeg.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

atk_dir, atk_mp4, die_dir, die_mp4, die_from, colour, out = sys.argv[1:8]
die_from = int(die_from)
FADE = 12      # wie BATTLE.fade im Spiel
SIZE = 768
BG = (92, 64, 40)

atk = json.loads(Path(atk_dir, 'meta.json').read_text())
die = json.loads(Path(die_dir, 'meta.json').read_text())
hit, n_atk, n_die = atk['hit'], atk['frames'], die['frames']
die_from = die.get('react', die_from)   # neue Sterbevideos: ungekürzt, Reaktionsbild in meta.json
wait = max(0, die_from - hit)           # wie im Spiel: Angreifer wartet, wenn das Opfer später reagiert
start = hit - die_from + wait           # Bild, bei dem das Sterbevideo beginnt
count = max(n_atk + wait, start + n_die)
fps = atk.get('fps', 24)


def frame(d, i):
    return Image.open(Path(d, f'{i:03d}.webp')).convert('RGBA').resize((SIZE, SIZE))


with tempfile.TemporaryDirectory() as tmp:
    for i in range(count):
        img = Image.new('RGBA', (SIZE, SIZE), BG + (255,))
        a = frame(atk_dir, min(max(0, i - wait), n_atk - 1))
        j = max(0, i - start)
        v = None
        if j < n_die:
            v = frame(die_dir, j)
            alpha = min(1, (n_die - j) / FADE)
            if alpha < 1:
                v.putalpha(v.getchannel('A').point(lambda x: int(x * alpha)))
        layers = [v, a] if colour == 'w' else [a, v]
        for layer in layers:
            if layer is not None:
                img.alpha_composite(layer)
        img.convert('RGB').save(f'{tmp}/{i:04d}.png')
    # Ton des Sterbevideos: sein Bild die_from erscheint beim Treffer -> um (hit - die_from) Bilder verschieben.
    # Statt einer MP4 darf '-' stehen (Bilder aus dem Studio, ohne Ton).
    shift = start / fps
    move = f'adelay={int(shift * 1000)}:all=1' if shift >= 0 else f'atrim=start={-shift},asetpts=PTS-STARTPTS'
    cmd = ['ffmpeg', '-loglevel', 'error', '-y', '-framerate', str(fps), '-i', f'{tmp}/%04d.png']
    sounds = []
    for k, (mp4, filt) in enumerate([(atk_mp4, 'anull'), (die_mp4, move)]):
        if mp4 != '-':
            cmd += ['-i', mp4]
            if k == 0 and wait:
                filt = f'adelay={int(wait / fps * 1000)}:all=1'
            sounds.append(f'[{len(sounds) + 1}:a]{filt}[s{k}]')
    if sounds:
        labels = ''.join(x[x.rindex('['):] for x in sounds)
        cmd += ['-filter_complex', ';'.join(sounds) + f';{labels}amix=inputs={len(sounds)}:duration=longest:normalize=0[a]',
                '-map', '0:v', '-map', '[a]', '-c:a', 'aac']
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-t', str(count / fps), out]
    subprocess.run(cmd, check=True)
print('geschrieben', out, f'{count} Bilder')
