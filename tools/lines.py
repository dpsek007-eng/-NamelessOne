#!/usr/bin/env python3
"""뜰 대사를 미리 굽는다 — data/lines.json.
사용: python3 tools/lines.py --all [--force] | --id seren [--dry]

왜 미리 굽는가(03-뜰.md · CLAUDE.md 측정 규칙):
  1. 같은 시드로 두 번 돌리면 같은 뜰이 나와야 한다. 실행 중에 문장을 만들면 재현되지 않는다
  2. 방치형이라 뜰은 계속 돈다. 호출을 런타임에 두면 끝없이 늘어난다
  3. 오프라인에서도 돌아야 한다
그래서 게임은 실행 중에 API 를 부르지 않는다. Irem.Sim/Heart.Pick 이 salt % n 으로 고른다.

재료는 그 사람 것만 쓴다 — life·death·memories·garden·voice·unique·title.
남의 기록을 넣으면 그 사람 입으로 남에 대한 사실을 주장하게 된다.
검사는 tools/check_lines.py 의 것을 그대로 부른다. 통과 못 한 줄은 굽지 않는다.
"""
import json, os, sys, time, requests
from check_lines import BANKS, MIN_LINES, MAX_LINES, MAX_LEN, check_rows

OUT   = 'data/lines.json'
MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-opus-5')
TRIES = 3

def ask(prompt, retry_note=''):
    url = os.environ['ANTHROPIC_BASE_URL'].rstrip('/') + '/v1/messages'
    head = {'anthropic-version': '2023-06-01', 'content-type': 'application/json'}
    if os.environ.get('ANTHROPIC_API_KEY'):
        head['x-api-key'] = os.environ['ANTHROPIC_API_KEY']
    else:
        head['authorization'] = 'Bearer ' + os.environ['ANTHROPIC_AUTH_TOKEN']
    body = {'model': MODEL, 'max_tokens': 2000,
            'messages': [{'role': 'user', 'content': prompt + retry_note}]}
    r = requests.post(url, headers=head, json=body, timeout=180)
    r.raise_for_status()
    return ''.join(b.get('text', '') for b in r.json()['content'])

def material(c):
    g = c.get('garden') or {}
    v = c.get('voice') or {}
    u = c.get('unique') or {}
    m = {
        '이름': c['name'], '호칭': c.get('title'), '역할': c.get('role'), '시대': c.get('era'),
        '한 줄': c.get('tagline'),
        '생업': g.get('생업'), '뜰에서 하는 일': g.get('desc'),
        '평소 하는 말': g.get('idle_line'),
        '살아 있을 때': c.get('life'), '마지막': c.get('death'),
        '남은 기억': c.get('memories'),
        '부를 때·이길 때·흐려질 때': [v.get('summon'), v.get('victory'), v.get('fade')],
        '고유 특성': u.get('line'),
    }
    return {k: x for k, x in m.items() if x}

def prompt_for(c):
    banks = '\n'.join(f'  "{k}": {d}' for k, d in BANKS.items())
    return f"""이렘의 탑이라는 게임의 0층 「뜰」에 세울 대사를 쓴다.

뜰은 이렘이 멸망하기 직전의 평범한 하루가 통째로 남은 조각이다.
여기서는 시간이 흐르지 않는다. 탑의 다른 층에서 그들은 죽은 사람이고, 뜰에서는 그냥 사람이다.
모든 잔상은 생전에 하던 일을 뜰에서 그대로 한다.

이 사람의 기록이다. 이 기록 밖의 사실을 만들지 마라.

{json.dumps(material(c), ensure_ascii=False, indent=1)}

상황 여섯 가지에 대해 이 사람이 뜰에서 혼자 내놓는 말을 각각 {MIN_LINES}~{MAX_LINES}줄 써라.
{banks}

지켜야 할 것:
- 이 사람이 직접 하는 말이다. 서술문이 아니다. 제 이름을 주어로 쓰지 마라
- **다른 사람의 이름이나 호칭을 하나도 쓰지 마라.** 「그」 「누군가」 정도로만 가리켜라
  (누가 같은 뜰에 있을지는 플레이어가 정한다. 이름을 쓰면 없는 사람을 부르게 된다)
- 한 줄은 {MAX_LEN}자 이내. 큰따옴표·줄바꿈·이모지·대괄호를 쓰지 마라
- 죽음을 말하지 마라. 뜰에서 그는 자기가 죽은 줄 모른다. 다만 무언가 끝났다는 감각은 남아 있다
- 말투는 위의 「부를 때·이길 때·흐려질 때」와 「평소 하는 말」에 맞춰라
- 같은 줄을 두 번 쓰지 마라

JSON 하나만 답하라. 다른 말은 붙이지 마라:
{{"work": ["…"], "rest": ["…"], "meet": ["…"], "avoid": ["…"], "pass": ["…"], "alone": ["…"]}}"""

def parse(txt):
    i, j = txt.find('{'), txt.rfind('}')
    if i < 0 or j < 0:
        raise ValueError('JSON 이 없다: ' + txt[:80])
    return json.loads(txt[i:j + 1])

def load():
    if not os.path.exists(OUT):
        return {}
    got = {}
    for row in json.load(open(OUT, encoding='utf-8'))['lines']:
        got.setdefault(row['id'], {})[row['bank']] = row['lines']
    return got

def save(got, chars):
    order = [c['id'] for c in chars]
    rows = [{'id': cid, 'bank': b, 'lines': got[cid][b]}
            for cid in order if cid in got
            for b in BANKS if b in got[cid]]
    json.dump({'note': 'tools/lines.py 가 굽는다. 손으로 고치면 tools/check_lines.py 로 다시 재라.',
               'model': MODEL, 'lines': rows},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def main():
    chars = json.load(open('data/characters.json', encoding='utf-8'))['characters']
    want = [c for c in chars if '--all' in sys.argv]
    if '--id' in sys.argv:
        cid = sys.argv[sys.argv.index('--id') + 1]
        want = [c for c in chars if c['id'] == cid]
    if not want:
        print(__doc__); sys.exit(2)
    got = {} if '--force' in sys.argv else load()

    if '--dry' in sys.argv:
        print(prompt_for(want[0])); return

    made = bad = 0
    for c in want:
        if c['id'] in got and len(got[c['id']]) == len(BANKS):
            print(f"  {c['name']} — 이미 있다"); continue
        note = ''
        for t in range(TRIES):
            try:
                rows = parse(ask(prompt_for(c), note))
            except Exception as e:
                print(f"  {c['name']} — {t+1}번째 실패: {e}"); time.sleep(2); continue
            errs = check_rows(chars, c, rows)
            if not errs:
                got[c['id']] = rows
                save(got, chars)        # 한 명씩 적는다 — 중간에 끊겨도 앞의 것은 남는다
                n = sum(len(v) for v in rows.values())
                print(f"  {c['name']} — {n}줄")
                made += 1
                break
            note = ('\n\n앞서 답한 것이 아래 검사에 걸렸다. 같은 곳을 되풀이하지 말고 다시 써라:\n'
                    + '\n'.join('- ' + e for e in errs[:8]))
            print(f"  {c['name']} — {t+1}번째 검사 {len(errs)}건 걸림")
        else:
            print(f"  {c['name']} — {TRIES}번 다 걸려서 굽지 않았다")
            bad += 1
    print(f"— 구운 잔상 {made}명 · 굽지 못한 잔상 {bad}명 · {OUT}")
    if bad:
        sys.exit(1)

if __name__ == '__main__':
    main()
