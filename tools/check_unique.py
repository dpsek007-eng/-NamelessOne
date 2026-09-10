#!/usr/bin/env python3
"""고유 특성(unique) 검증 — 문장의 주어·이름 중복·스키마 일치를 실측으로 잡는다.
사용: python3 tools/check_unique.py [--quiet]
실패하면 exit 1. 데이터가 원하는 상태인지 확인하는 자다.

주어 규칙(02-캐릭터-시스템.md 4-3): 고유 특성 문장은 그 사람이 주어로 있어야 한다.
주어 후보는 공식 name, 그리고 name에서 접두(마지막/어느/누군가…)를 뺀 축약 호칭까지 인정한다.
("마지막 물장수"의 line은 "물장수는 …" 로 쓰는 것이 문서 호칭과 맞다)
"""
import json,sys,re,jsonschema

FSKIP=('마지막 ','누군가 ','어느 ','그 ','한 명의 ','이름 없는 ','이름을 적던 ','빵을 굽던 ')

def subject_candidates(c):
    """주어 후보 = 공식 name + 축약 호칭(접두 제거) + 대명사 그/그는."""
    n=c.get('name','')
    cand=[n]
    for skip in FSKIP:
        if n.startswith(skip):
            core=n[len(skip):].strip()
            if len(core)>=2: cand.append(core)
    cand += ['그','그는']
    return [c for c in cand if c]

def main():
    quiet='--quiet' in sys.argv
    obj=json.load(open('data/characters.json',encoding='utf-8'))
    schema=json.load(open('data/characters.schema.json',encoding='utf-8'))
    jsonschema.validate(obj,schema)   # 스키마가 캐릭터를 읽는지

    chars=obj['characters']
    errs=[]
    names={}
    for c in chars:
        u=c.get('unique')
        if u is None:
            if c.get('rarity',0)>=4:
                errs.append(f"{c['id']} (★{c['rarity']}) — 전승·기록급인데 고유 특성이 없다")
            continue
        for f in ('name','rule','line'):
            if not u.get(f):
                errs.append(f"{c['id']} unique.{f} 비어 있음")
        if u.get('name') in names:
            errs.append(f"고유 특성 이름 중복: {u['name']} ({names[u['name']]} / {c['id']})")
        names[u.get('name')]=c['id']
        s=u.get('line','')
        if s and not any(re.search(re.escape(subj), s) for subj in subject_candidates(c)):
            errs.append(f"{c['id']} — line 주어가 자기 이름/호칭/대명사가 아니다: {s[:30]}…")
    if errs:
        for e in errs: print('ERR',e)
        sys.exit(1)
    if not quiet:
        print(f"OK — 고유 특성 {len(names)}명, 스키마 일치, 주어/이름 규칙 통과")

if __name__=='__main__':
    main()
