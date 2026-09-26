# -*- coding: utf-8 -*-
"""유니티로 내보낸다 — 시트 PNG, 지형 타일 PNG, 그리고 표 하나.

   시험판(HTML)과 유니티가 같은 표를 읽는다. 표가 갈라지면 둘 다 틀린 것이다.
   JsonUtility 는 사전을 못 읽으므로 전부 배열로 편다.
"""
import json, os, re, shutil, sys
sys.path.insert(0, 'tools')
import art, rig, trades, bonds

ROOT   = 'unity/Assets/Resources/Irem'
SHADES = ROOT + '/Shades'
TILES  = ROOT + '/Tiles'
PROTO  = 'proto/battle_proto.html'
TILE_VARIANTS = 5
TILE_KIND = {'.': 'plain', '#': 'block', ':': 'rubble', '~': 'crack', '_': 'drain',
             '^': 'high', 'o': 'cover', 'w': 'water', 'x': 'fire'}

# 체형·계층 슬러그. unity/.../IremCharScene.cs 의 Bodies·Classes 와 같아야 한다 —
# 다르면 없는 FBX 를 찾는다.
BODY  = {'수호': 'guard', '저항': 'resist', '헌신': 'devote', '탐구': 'seek', '도피': 'flee'}
CLASS = {'왕실': 'royal', '귀족': 'noble', '술사': 'mage', '성직': 'clergy', '관리': 'clerk',
         '상인': 'merchant', '장인': 'artisan', '병졸': 'soldier', '농어민': 'peasant',
         '하인': 'servant', '유랑': 'vagrant'}
# 역할도 생업도 없는 잔상(이름 없는 자). 이름도 일도 없다는 설정과 맞는 것을 고른다.
NOBODY_BODY, NOBODY_CLASS = 'flee', 'vagrant'


def proto_data():
    h = open(PROTO, encoding='utf-8').read()
    m = re.search(r'<script id="DATA" type="application/json">\n(.*?)\n</script>', h, re.S)
    return json.loads(m.group(1))


def garden(proto_chars):
    """뜰 표 — 네 원본에서 조립한다. 목록을 손으로 적어 두면 사람이 늘 때 조용히 틀린다.
         data/characters.json  잔상 23명 · 관계 인연
         data/garden.json      지도 · 일터 열네 곳
         tools/trades.py       생업 → 일터(place) · 계층(cls)
         tools/bonds.py        자동 인연 규칙
       성향의 무게는 proto 의 것을 쓴다. 전투와 뜰이 같은 성향에서 나와야
       「층에서는 죽음을, 뜰에서는 삶을 본다」가 같은 사람의 두 모습이 된다.
    """
    G   = json.load(open('data/garden.json', encoding='utf-8'))
    src = json.load(open('data/characters.json', encoding='utf-8'))
    place = {t['n']: t['place'] for t in trades.TRADES}
    cls   = {t['n']: t['cls']   for t in trades.TRADES}
    pro   = {c['id']: c for c in proto_chars}
    known = {s['name'] for s in G['일터']}

    agents = []
    for c in src['characters']:
        trade = c['garden']['생업']
        pl    = place.get(trade, '')
        cl    = cls.get(trade, '')
        if trade != '없음' and pl not in known:
            raise SystemExit(f"[틀림] {c['id']} 의 생업 {trade} → 일터 {pl!r} 가 뜰에 없다")
        p = pro.get(c['id'], {})
        w = (p.get('trait') or {}).get('w', {})
        agents.append({
            'id': c['id'], 'name': c['name'], 'role': c['role'], 'era': c['era'],
            'cls': cl, 'trade': trade, 'place': pl,
            'body':    BODY.get(c['role'],  NOBODY_BODY),
            'garment': f"{BODY.get(c['role'], NOBODY_BODY)}_{CLASS.get(cl, NOBODY_CLASS)}",
            'col': (c.get('visual') or {}).get('key_color', p.get('col', '#888888')),
            'tag': c.get('tagline', ''),
            'idleLine': c['garden'].get('idle_line', ''),
            'deed': c['garden'].get('desc', ''),
            # 층이 null 인 잔상이 하나 있다(이름 없는 자 — 몇 층 것인지 불명).
            # 0 은 뜰이므로 쓸 수 없다. -1 을 「불명」으로 둔다.
            'r': c.get('rarity') or 1, 'floor': -1 if c.get('floor') is None else c['floor'],
            'wKeys': list(w.keys()), 'wVals': list(w.values()),
        })

    rel = [b for b in src['bonds'] if b['type'] == '관계']
    T = {
        'w': G['크기']['w'], 'h': G['크기']['h'], 'map': G['지도'],
        'terrain': [{'ch': ch, 'name': t['n'], 'mv': t.get('mv', 1),
                     'dmg': 0.0, 'block': bool(t.get('block')), 'def': 0.0}
                    for ch, t in G['지형'].items()],
        'agents': agents,
        'stations': [{'name': s['name'], 'prop': s['prop'], 'desc': s.get('desc', ''),
                      'x': s['x'], 'y': s['y']} for s in G['일터']],
        'bonds': [{'id': r['id'], 'kind': r['kind'], 'title': r['title'],
                   'story': r['story'], 'reward': r.get('reward', ''),
                   'note': r.get('note', ''),
                   'members': r.get('members', []),
                   'a': r.get('a', ''), 'b': r.get('b', ''), 'role': r.get('role', ''),
                   'na': r.get('na', 0), 'nb': r.get('nb', 0), 'n': r.get('n', 0),
                   'ratio': r.get('ratio', 0.0),
                   # 처음엔 피하는 인연. docs/03-뜰.md 가 그렇다고 적은 것만 켜져 있다.
                   'shy': bool(r.get('avoid_first'))}
                  for r in bonds.rules(rel)],
        # 대사는 tools/lines.py 가 따로 굽는다. 없으면 없는 대로 비워 둔다.
        'lines': json.load(open('data/lines.json', encoding='utf-8'))['lines']
                 if os.path.exists('data/lines.json') else [],
        'idleX': G['서있는자리']['x'], 'idleY': G['서있는자리']['y'],
        'activeSlots': bonds.ACTIVE_SLOTS,
    }
    with open(ROOT + '/garden.json', 'w', encoding='utf-8') as fp:
        json.dump(T, fp, ensure_ascii=False, separators=(',', ':'))
    kb = os.path.getsize(ROOT + '/garden.json') / 1024
    nb = len([1 for a in agents if not a['wKeys']])
    print(f"뜰 — 표 {kb:.0f}KB (잔상 {len(agents)}, 일터 {len(T['stations'])}, "
          f"인연 규칙 {len(T['bonds'])}, "
          f"대사 {sum(len(r['lines']) for r in T['lines'])}줄({len(T['lines'])}뱅크), 성향 없는 잔상 {nb})")


def main():
    for d in (SHADES, TILES):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

    D   = proto_data()
    src = {c['id']: c for c in json.load(open('data/characters.json', encoding='utf-8'))['characters']}

    # ── 잔상 시트 ──
    for c in D['chars']:
        s = src.get(c['id'])
        trade = s['garden']['생업'] if s else c.get('trade', '없음')
        L = rig.look_of(c['id'], c.get('cls', '하인'), trade, c['role'], c['col'], c['r'])
        rig.sheet(L).save(f'{SHADES}/{c["id"]}.png')
    for k in ('재', '잔해', '그림자'):
        rig.sheet(rig.foe_look(k)).save(f'{SHADES}/foe_{k}.png')
    for i in range(4):
        rig.sheet(rig.refugee_look(i)).save(f'{SHADES}/ref{i}.png')

    # ── 지형 타일 ──
    for ch, kind in TILE_KIND.items():
        for v in range(TILE_VARIANTS):
            art.tile(ch, v).save(f'{TILES}/{kind}_{v}.png')

    # ── 표 ──
    T = {
        'nf': rig.NF,
        'clips': [{'name': k, **v} for k, v in rig.clip_table().items()],
        'terrain': [{'ch': ch, 'name': t['n'], 'mv': t.get('mv', 1),
                     'dmg': t.get('dmg', 0.0), 'block': bool(t.get('block')),
                     'def': t.get('def', 0.0)}
                    for ch, t in D['terrain'].items()],
        'chars': [{
            'id': c['id'], 'name': c['name'], 'role': c['role'], 'era': c['era'],
            'cls': c.get('cls', '하인'), 'trade': c.get('trade', '없음'),
            'col': c['col'], 'tag': c.get('tag', ''), 'gen': bool(c.get('gen')),
            'r': c['r'], 'floor': c['floor'], 'hp': c['hp'], 'atk': c['atk'],
            'def': c['def'], 'spd': c['spd'], 'pw': c['pw'],
            'traitName': (c.get('trait') or {}).get('name', ''),
            'traitLine': (c.get('trait') or {}).get('line', ''),
            'skill': (c.get('skills') or [{'n': '공격'}])[0].get('n', '공격'),
            'wKeys': list((c.get('trait') or {}).get('w', {}).keys()),
            'wVals': list((c.get('trait') or {}).get('w', {}).values()),
        } for c in D['chars']],
        'floors': [{
            'n': f['n'], 'name': f['name'], 'era': f['era'], 'teams': f['teams'],
            'slot': f['slot'], 'need': f['need'], 'baseReq': f['base'],
            'note': f.get('note', ''), 'mapNote': f.get('mapNote', ''),
            'goalKind': (f.get('goal') or {}).get('t', '전멸'),
            'goalName': (f.get('goal') or {}).get('name', ''),
            'goalN': (f.get('goal') or {}).get('n', 0),
            'env': f.get('env', []), 'map': f['map'],
            'routes': [{'id': r['id'], 'pw': r['pw'],
                        'cond': [{'t': c['t'], 'v': str(c['v']), 'n': c.get('n', 1)}
                                 for c in r.get('cond', [])]}
                       for r in f.get('routes', [])],
        } for f in D['floors']],
        # 수호자 종류 — proto 의 FOE_KINDS 와 같아야 한다
        'foes': [
            {'name': '재',    'rng': 1, 'mv': 4, 'spd': 88,  'hp': 1.15, 'atk': 1.00},
            {'name': '잔해',  'rng': 4, 'mv': 2, 'spd': 96,  'hp': 0.70, 'atk': 1.25},
            {'name': '그림자', 'rng': 2, 'mv': 6, 'spd': 118, 'hp': 0.80, 'atk': 0.95},
        ],
    }
    with open(ROOT + '/tables.json', 'w', encoding='utf-8') as fp:
        json.dump(T, fp, ensure_ascii=False, separators=(',', ':'))

    garden(D['chars'])

    n_sheets = len(os.listdir(SHADES))
    n_tiles  = len(os.listdir(TILES))
    kb = os.path.getsize(ROOT + '/tables.json') / 1024
    print(f'유니티 — 시트 {n_sheets}장, 타일 {n_tiles}장, 표 {kb:.0f}KB '
          f'(잔상 {len(T["chars"])}, 층 {len(T["floors"])}, 프레임 {rig.NF})')


if __name__ == '__main__':
    main()
