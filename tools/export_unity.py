# -*- coding: utf-8 -*-
"""유니티로 내보낸다 — 시트 PNG, 지형 타일 PNG, 그리고 표 하나.

   시험판(HTML)과 유니티가 같은 표를 읽는다. 표가 갈라지면 둘 다 틀린 것이다.
   JsonUtility 는 사전을 못 읽으므로 전부 배열로 편다.
"""
import json, os, re, shutil, sys
sys.path.insert(0, 'tools')
import art, rig

ROOT   = 'unity/Assets/Resources/Irem'
SHADES = ROOT + '/Shades'
TILES  = ROOT + '/Tiles'
PROTO  = 'proto/battle_proto.html'
TILE_VARIANTS = 5
TILE_KIND = {'.': 'plain', '#': 'block', ':': 'rubble', '~': 'crack', '_': 'drain',
             '^': 'high', 'o': 'cover', 'w': 'water', 'x': 'fire'}


def proto_data():
    h = open(PROTO, encoding='utf-8').read()
    m = re.search(r'<script id="DATA" type="application/json">\n(.*?)\n</script>', h, re.S)
    return json.loads(m.group(1))


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

    n_sheets = len(os.listdir(SHADES))
    n_tiles  = len(os.listdir(TILES))
    kb = os.path.getsize(ROOT + '/tables.json') / 1024
    print(f'유니티 — 시트 {n_sheets}장, 타일 {n_tiles}장, 표 {kb:.0f}KB '
          f'(잔상 {len(T["chars"])}, 층 {len(T["floors"])}, 프레임 {rig.NF})')


if __name__ == '__main__':
    main()
