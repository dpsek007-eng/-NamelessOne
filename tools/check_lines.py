#!/usr/bin/env python3
"""뜰 대사(data/lines.json) 검증 — 주어·남의 이름 섞임·스키마·길이·중복을 실측으로 잡는다.
사용: python3 tools/check_lines.py [--quiet]
실패하면 exit 1. tools/lines.py 도 굽기 전에 이 파일의 검사를 그대로 부른다 —
검사를 두 벌 적으면 굽는 쪽과 재는 쪽이 조용히 갈라진다.

주어 규칙(02-캐릭터-시스템.md 4-3): 문장의 주어는 항상 그 사람이다.
대사에서 이 규칙이 깨지는 꼴은 둘이다.
  1. 남의 이름을 부른다 — 그러면 그 사람에 대한 사실을 주장하게 된다
  2. 제 이름을 주어로 쓴다 — 그건 대사가 아니라 서술문이다
호칭 판별은 tools/check_unique.py 의 것을 그대로 빌린다.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_unique import subject_candidates

# Irem.Sim/Heart.cs 의 BankFor 와 같아야 한다 — 다르면 게임이 빈 뱅크를 집는다.
BANKS = {
    'work':  '제 생업을 하는 중',
    'rest':  '손을 놓고 잠깐 쉬는 중',
    'meet':  '누군가와 마주 서서',
    'avoid': '마주치고 싶지 않아 돌아설 때',
    'pass':  '그냥 지나가는 중',
    'alone': '혼자 서성일 때의 혼잣말',
}
MIN_LINES, MAX_LINES = 3, 4
MIN_LEN,  MAX_LEN   = 3, 40      # 뜰 말풍선에 들어가는 길이
BAD = re.compile(r'[\n\r"“”\[\]{}*|]|[\U0001F300-\U0001FAFF]')

def others_titles(chars, me):
    """나 말고 다른 잔상을 가리키는 호칭 전부. 두 글자 이하는 우연히 겹치므로 뺀다."""
    out = set()
    for c in chars:
        if c['id'] == me['id']:
            continue
        for t in subject_candidates(c):
            if len(t) >= 3 and t not in ('그', '그는'):
                out.add(t)
        if c.get('title') and len(c['title']) >= 3:
            out.add(c['title'])
    return out

def check_rows(chars, me, rows):
    """한 사람의 뱅크 묶음을 잰다. 돌아온 목록이 비어 있으면 통과다."""
    errs, seen = [], {}
    tag = f"{me['id']}"
    banks = set(rows)
    for missing in sorted(BANKS.keys() - banks):
        errs.append(f"{tag} — 뱅크 {missing} 이 없다")
    for extra in sorted(banks - BANKS.keys()):
        errs.append(f"{tag} — 없는 뱅크 {extra}")
    theirs = others_titles(chars, me)
    mine = re.compile('^(' + '|'.join(re.escape(n) for n in [me['name']] ) + r')(은|는|이|가)\s')
    for bank in sorted(banks & BANKS.keys()):
        ls = rows[bank]
        if not isinstance(ls, list) or not all(isinstance(x, str) for x in ls):
            errs.append(f"{tag}.{bank} — 줄 목록이 아니다"); continue
        if not MIN_LINES <= len(ls) <= MAX_LINES:
            errs.append(f"{tag}.{bank} — {len(ls)}줄 (있어야 할 것은 {MIN_LINES}~{MAX_LINES}줄)")
        for s in ls:
            t = s.strip()
            if t != s:
                errs.append(f"{tag}.{bank} — 앞뒤 공백: {s!r}")
            if not MIN_LEN <= len(t) <= MAX_LEN:
                errs.append(f"{tag}.{bank} — {len(t)}자: {t[:20]}…")
            if BAD.search(t):
                errs.append(f"{tag}.{bank} — 쓸 수 없는 글자: {t[:20]}…")
            if mine.match(t):
                errs.append(f"{tag}.{bank} — 제 이름이 주어다(대사가 아니라 서술문): {t[:24]}…")
            for n in theirs:
                if n in t:
                    errs.append(f"{tag}.{bank} — 남({n})의 이름이 섞였다: {t[:24]}…")
                    break
            if t in seen:
                errs.append(f"{tag}.{bank} — {seen[t]} 와 같은 줄: {t[:20]}…")
            else:
                seen[t] = bank
    return errs

def main():
    quiet = '--quiet' in sys.argv
    chars = json.load(open('data/characters.json', encoding='utf-8'))['characters']
    by_id = {c['id']: c for c in chars}
    if not os.path.exists('data/lines.json'):
        print('ERR data/lines.json 이 없다 — python3 tools/lines.py --all 로 먼저 굽는다')
        sys.exit(1)
    obj = json.load(open('data/lines.json', encoding='utf-8'))

    errs, per, total, allseen = [], {}, 0, {}
    for row in obj.get('lines', []):
        for f in ('id', 'bank', 'lines'):
            if f not in row:
                errs.append(f"줄에 {f} 가 없다: {str(row)[:40]}")
        if 'id' not in row:
            continue
        if row['id'] not in by_id:
            errs.append(f"없는 잔상: {row['id']}"); continue
        per.setdefault(row['id'], {})[row.get('bank')] = row.get('lines')
    for cid, rows in sorted(per.items()):
        errs += check_rows(chars, by_id[cid], rows)
        for bank, ls in rows.items():
            for s in ls if isinstance(ls, list) else []:
                total += 1
                if s in allseen and allseen[s] != cid:
                    errs.append(f"{cid} — {allseen[s]} 의 줄과 똑같다: {s[:20]}…")
                allseen.setdefault(s, cid)
    for cid in sorted(by_id.keys() - per.keys()):
        errs.append(f"{cid} — 대사가 하나도 없다")

    if errs:
        for e in errs:
            print('ERR', e)
        print(f"— 틀린 것 {len(errs)}개")
        sys.exit(1)
    if not quiet:
        print(f"OK — 잔상 {len(per)}명 × 뱅크 {len(BANKS)}종 = {total}줄, "
              f"주어·남의 이름·길이·중복 규칙 통과")

if __name__ == '__main__':
    main()
