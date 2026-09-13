# -*- coding: utf-8 -*-
"""머리·두건 6종 검증 — 실제 프로토 캐릭터의 idle 첫 프레임을 머리 타입별로 본다.

판정 기준 (docs/22 선기록): 계층이 머리로 읽혀야 한다 —
  성직은 민머리, 술사는 두건, 농어민은 머릿수건, 병졸은 투구, 관리·상인은 모자,
  왕실은 관. 맨머리는 원래의 4갈래 머리다.
"""
import json, os, re, sys
sys.path.insert(0, 'tools')
from PIL import Image, ImageDraw, ImageFont
import rig

def proto():
    h = open('proto/battle_proto.html').read()
    m = re.search(r'<script id="DATA" type="application/json">\n(.*?)\n</script>', h, re.S)
    return json.loads(m.group(1))

def main():
    D = proto()
    src = {c['id']: c for c in json.load(open('data/characters.json', encoding='utf-8'))['characters']}
    heads = ['bare', 'hood', 'helmet', 'hat', 'kerchief', 'circlet']
    cols = 4
    cell = 96
    pad = 18
    rows = len(heads)
    W = cols * (cell + pad) + pad
    H = rows * (cell + 26 + pad) + pad
    sheet = Image.new("RGB", (W, H), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 13)
    except OSError:
        font = ImageFont.load_default()

    for hi, hd in enumerate(heads):
        # 이 머리 타입의 캐릭터를 골라 낸다 (왕실은 현재 0명이라 합성한다)
        cands = [c for c in D['chars'] if rig.look_of(
            c['id'], c.get('cls', '하인'), (src.get(c['id']) or {}).get('garden', {}).get('생업', '없음'),
            c['role'], c['col'], c['r'])['head'] == hd]
        picks = cands[:cols]
        while len(picks) < cols and hd != 'circlet':
            picks.append(picks[-1] if picks else None)
        if hd == 'circlet':
            c = {"id": "royal_sample", "cls": "왕실", "role": "수호", "col": "#C9A227", "r": 6}
            picks = [c] + [None]*(cols-1)
        for ci in range(cols):
            x = pad + ci*(cell + pad)
            y = pad + hi*(cell + 26 + pad)
            if picks[ci] is None:
                continue
            c = picks[ci]
            s = src.get(c['id'])
            trade = (s['garden']['생업'] if s else c.get('trade', '없음'))
            L = rig.look_of(c['id'], c.get('cls', '하인'), trade, c['role'], c['col'], c['r'])
            f0 = rig.draw(L, rig.pose(L, 'idle', 0, 6))
            # 체스판 배경 + 3배 확대
            bg = Image.new("RGBA", (cell, cell), (24, 24, 28))
            tile = 12
            for yy in range(0, cell, tile):
                for xx in range(0, cell, tile):
                    if (xx//tile + yy//tile) % 2:
                        bg.paste(Image.new("RGBA", (tile, tile), (30, 30, 35)), (xx, yy))
            # 48x64 → 가로세로 비율 유지해 중앙 배치
            f0 = f0.resize((int(cell*0.75), int(cell)), Image.NEAREST)
            bg.alpha_composite(f0, ((cell - f0.width)//2, 0))
            sheet.paste(bg.convert("RGB"), (x, y))
            name = c.get('name') or c['id']
            draw.text((x+2, y+cell+4), f"{name} · {c.get('cls', '하인')}",
                      fill=(220, 220, 230), font=font)
        draw.text((pad + cols*(cell+pad) - 8, y+cell+4), hd, fill=(150, 200, 255), font=font,
                  anchor="ra")

    out = "/tmp/head_grid.png"
    sheet.save(out)
    print(f"머리 {len(heads)}타입 → {out}  ({W}x{H})")
    # 어떤 캐릭터가 골랐는지도 적는다
    for hd in heads:
        picks = [c for c in D['chars'] if rig.look_of(
            c['id'], c.get('cls', '하인'), (src.get(c['id']) or {}).get('garden', {}).get('생업', '없음'),
            c['role'], c['col'], c['r'])['head'] == hd]
        print(f"  {hd:9s} {len(picks)}명 — {', '.join(c['name'] for c in picks[:6])}")

if __name__ == '__main__':
    main()