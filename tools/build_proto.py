# -*- coding: utf-8 -*-
"""proto/battle_proto.html 의 DATA 블록에 아트를 다시 넣는다.

   기존 DATA(층·지형·조건)는 그대로 두고 그림만 갈아끼운다.
   - chars[].sp : 잔상 스프라이트
   - foes       : 수호자 종류별 스프라이트
   - ref        : 피난민 스프라이트
   - tiles      : 지형 타일 (칸마다 변형 여러 장)
"""
import json, re, sys
sys.path.insert(0, 'tools')
import art, rig
from shade_gen4 import make
from power import power

HTML = 'proto/battle_proto.html'
PAT  = re.compile(r'(<script id="DATA" type="application/json">\n)(.*?)(\n</script>)', re.S)

VARIANTS = {'.': 5, '#': 3, ':': 3, '~': 3, '_': 2, '^': 2, 'o': 3, 'w': 3, 'x': 3}

# 무명 잔상은 손으로 쓰지 않는다. 시드에서 나온다.
# 뜰이 스물세 명뿐일 리가 없다 — 멸망한 도시에는 사람이 있었다.
EXTRA   = 44
SEED0   = 907_0000
RARITY  = [1]*16 + [2]*14 + [3]*9 + [4]*4 + [5]*1        # 일반 소환에 가까운 분포
ROLE_TRAIT = {
    "수호": ["물러서지않는다", "감싼다", "메운다", "내려오지않는다", "먼저나선다"],
    "저항": ["앞뒤가없다", "돌아서지않는다", "먼저나선다", "물러서지않는다"],
    "헌신": ["멈추지않는다", "먹인다", "마르지않는다", "감싼다", "종을친다"],
    "탐구": ["세어둔다", "기록한다", "원인을본다", "가까이간다", "양쪽을본다"],
    "도피": ["버리고간다", "길을낸다", "양쪽을본다"],
    "미상": ["메운다", "세어둔다"],
}

def extra_shades(traits):
    out = []
    for i in range(EXTRA):
        seed = SEED0 + i * 7919
        sh = make(seed, 1, RARITY[i % len(RARITY)])
        st = sh["stats"]
        tid = ROLE_TRAIT.get(sh["role"], ["메운다"])[seed % len(ROLE_TRAIT.get(sh["role"], ["메운다"]))]
        t = traits[tid]
        out.append({
            "id": "s%d" % seed, "name": sh["name"], "r": sh["rarity"], "role": sh["role"],
            "floor": sh["floor"], "era": sh["era"], "cls": sh["cls"], "trade": sh["trade"],
            "hp": st["잔존"], "atk": st["의지"], "def": st["자취"], "spd": st["공명"],
            "pw": round(power(st)), "col": sh["visual"]["key_color"],
            "tag": sh["death"].split(". ")[0] + ".",
            "sp": rig.uri(rig.sheet(rig.look_of("s%d" % seed, sh["cls"], sh["trade"],
                          sh["role"], sh["visual"]["key_color"], sh["rarity"]))),
            "trait": {"id": tid, "name": t["name"], "line": t["line"], "w": t["w"]},
            "skills": [{"n": k["name"], "t": "액티브", "d": k["effect"]} for k in sh["skills"][:2]],
            "gen": True,
        })
    return out

def main():
    html = open(HTML, encoding='utf-8').read()
    m = PAT.search(html)
    D = json.loads(m.group(2))

    src = {c['id']: c for c in json.load(open('data/characters.json', encoding='utf-8'))['characters']}
    for c in D['chars']:
        s = src.get(c['id'])
        trade = s['garden']['생업'] if s else '없음'
        c['sp'] = rig.uri(rig.sheet(rig.look_of(c['id'], c.get('cls', '하인'), trade,
                                    c['role'], c['col'], c['r'])))
    traits = json.load(open('data/traits.json', encoding='utf-8'))['성향']
    D['chars'] = [c for c in D['chars'] if not c.get('gen')] + extra_shades(traits)
    D['foes'] = {k: rig.uri(rig.sheet(rig.foe_look(k))) for k in ('재', '잔해', '그림자')}
    D['ref']  = [rig.uri(rig.sheet(rig.refugee_look(i))) for i in range(4)]
    D['clips'] = rig.clip_table()
    D['nf']    = rig.NF
    D['tiles'] = {ch: [art.uri(art.tile(ch, v)) for v in range(n)]
                  for ch, n in VARIANTS.items()}

    blob = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
    open(HTML, 'w', encoding='utf-8').write(html[:m.start(2)] + blob + html[m.end(2):])
    kb = len(blob) / 1024
    print('DATA %.0fKB — 잔상 %d, 수호자 %d, 피난민 %d, 타일 %d, 프레임 %d/장'
          % (kb, len(D['chars']), len(D['foes']), len(D['ref']),
             sum(len(v) for v in D['tiles'].values()), rig.NF))

if __name__ == '__main__':
    main()
