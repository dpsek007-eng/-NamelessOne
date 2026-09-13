# 이어서.md — 이렘의 탑(TOP) 프로젝트 계속하기

> **이 파일은 Claude Code 세션이 끊겼을 때, 이어서 작업하려면 반드시 읽어라.**
> 마지막 갱신: 2026-09-14, 머리·두건 6종 완료

---

## 1. 이 저장소는 어디에 있나

- **원본 서버** 경로: `/media/hdd8/justin/my_project/TOP`
- **이사 번들** 경로: `/media/hdd8/justin/my_project/이사/`
  - 번들에 커밋 전부(`bc838aa` 포함)가 들어 있다
- ** 깃허브**(`dpsek007-eng/-NamelessOne`): 39개 커밋이 미푸시 상태.
  - `Navifra-Justin` 권한 문제로 push 불가.
  - 해결 방법: (1) `dpsek007-eng`가 `Navifra-Justin`을 collaborator로 초대, 또는
    (2) 서버 공개키(`ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEjfbZbP/pwTWcy9RAWTKN1Da1rO4QlRRktzDdWqw3eH justin@navifra.com`)를 write 권한 deploy key로 등록

---

## 2. 새 서버에서 이사 번들 풀기

```bash
# 1. 번들을 옮긴다 (이미 옮겼다면 이 단계 건너뛰기)
scp old-server:/media/hdd8/justin/my_project/이사/00-저장소.bundle /tmp/
scp old-server:/media/hdd8/justin/my_project/이사/0{1,2,3,4,5,6}-*.tar /tmp/

# 2. 체크섬 확인
cd /tmp
grep -E '00-저장소|01-초상|02-소품|03-소품이미지|04-역할실험|05-캐릭터|06-초점' \
  <path-to>/이사/체크섬.txt | while read sum file; do
  echo -n "$file "; echo "$sum  $file" | sha256sum -c
done

# 3. 저장소 복구
mkdir -p /media/hdd8/justin/my_project/TOP && cd /media/hdd8/justin/my_project/TOP
git init
git remote add origin old-server:/media/hdd8/justin/my_project/TOP
git fetch origin
git bundle unbundle /tmp/00-저장소.bundle
git checkout bc838aa

# 4. 부산물 풀기 (chars/out/cast/ 이 없을 때만)
tar xf /tmp/05-캐릭터.tar
```

> 번들 검증: `git bundle verify /tmp/00-저장소.bundle`

---

## 3. 이 프로젝트가 뭔가

**이렘의 탑 (Tower of Irem)** — 잔상(이름 없는 존재)이 탑을 오르는 방치형 수집 RPG.

- 탑은 그냥 탑대로 올라간다
- **성장의 끝이 정보의 끝** — 캐릭터는 층에 절대 안 묶인다
- 55명의 잔상이 전부 세팅 완료 (GLB 55개, 동작 220개)

---

## 4. 절대 어길 수 없는 규칙 (인용)

> "서버컴이니깐 혹시 무슨 설치가 필요하면, **도커로 진행해줘**"

> "탑은 그냥 탑대로 올라가고, **성장의 끝이 정보의 끝**이야."

네 가지 확정 설계:
1. **★6+ 는 특성을 준다, 스탯이 아니다**
2. **레벨은 계속 오른다**
3. **성급은 각성으로만 상승**
4. **레벨 상한 = 도달 최고층**

---

## 5. 커밋 히스토리

```
2f4c59b Adjust portrait style + age
8019ba8 초상 카드에 고유 특성을 표시한다
b4dd771 고유 특성 필드를 추가하고 전승·기록급 11명분을 쓴다
1eef4d9 이어서 작업할 수 있도록 규칙과 계속하기 파일을 만든다
bc838aa README 에 화면 찍는 줄을 넣는다
e7de4ff 움직이는 화면은 가상시간으로 못 찍는다 — CDP 로 직접 찍는 자를 만든다
760303a 현황표 두 줄을 사실에 맞춘다 — 한 사람이 아니라 쉰다섯
674cc47 소지품은 실루엣이 아니다 — 문서 세 곳을 고치고, 옮길 짐을 싼다
1759efe 쉰다섯을 다 세우고, 넓힌 자로 소지품을 다시 측정한다
```

---

## 6. 캐릭터 시스템 핵심 측정값

- **본수**: 53개 (game_engine 리그)
- **얼굴 뼈**: 0개 (MPFB 리그의 한계 — 표정 불가)
- **몸 메시**: 약 26,756 버텍스
- **옷 메시**: 약 6,112 버텍스
- **동작**: 숨/걷기/휘두름/돌아본다 (4클립, 총 220클립)
- **실루엣 배경 대비**: 82.5% (BG=0,0,0 기준)
- **실루엣 narrow-ruler 기준**: 역할 2.13%, 계층 8.67%, ratio 4.1배

---

## 7. 도구 목록

| 도구 | 용도 |
|------|------|
| `tools/serve.py` | 뷰어 웹서버 (8000번 포트, `cast()` 함수로 55인 manifest) |
| `tools/shot.py` | **CDP 기반 스크린샷** — rAF 멈추지 않는 페이지도 촬영 |
| `tools/silhouette_diff.py` | 실루엣 측정 (`sil(path)`, `diff(a,b)` — 배열을 받는다) |
| `tools/make_demo.py` | 캐릭터 일괄 생성 (55인, CPU 약 8분) |
| `tools/art.py` | 초상 생성 도구 |
| `tools/check_unique.py` | 고유 특성 검증 (주어·이름 중복·스키마 확인) |
| `tools/face_grid.py` | 초상 78종 격자 — 눈으로 보는 판정용 |
| `tools/gacha_sim.py` | 뽑기 시뮬레이션 |
| `tools/bondi_sim.py` | 본디 시뮬레이션 |
| `tools/cap_sim.py` | 천장 시뮬레이션 |
| `tools/fusion_sim.py` | 합성 시뮬레이션 |
| `tools/focus_curve.py` | 초점 곡선 |
| `tools/focus_stack.py` | 초점 스택 |

---

## 8. 스크린샷 찍는 법 (`tools/shot.py`)

```bash
# 기본 사용법
python3 tools/shot.py http://127.0.0.1:8000/viewer/#one /tmp/a.png --wait 90

# 특정 크기
python3 tools/shot.py http://127.0.0.1:8000/viewer/#one /tmp/a.png --wait 90 --width 1400 --height 900
```

> ⚠ `chrome --screenshot --virtual-time-budget`는 rAF가 멈추지 않는 페이지에서 **절대 동작하지 않는다** (500~40000ms 전부 실패 확인). 반드시 `tools/shot.py`를 사용하라.

---

## 9. 열린 질문과 남은 것

### 열린 경고 (⚠)
- 47개 소지품이 손 뼈에 미부착
- ~~머리·두건 6종 누락~~ → **해결** (커밋 예정) — 판정 기준 선기록(`docs/22-아트.md` 「머리·두건 6종」+ 「계층은 읽힌다」: 성직 민머리, 술사 두건, 농어민 머릿수건) → `art.py`에 HEAD/BALD 상수 추가 → `rig.py` look_of/draw 머리 분기 6개 타입 구현 → 유니티 시트 73장 재생성 → `/tmp/head_grid.png` 격자 시각 검증 → 6종 모두 판정 통과
- 두상 6×이목구비 8 포트레이트 파트 누락
- Unity `Silhouette.shader` / `_Focus` 미구현
- 깊은 부름 efficiency 1.12배 (목표 미달)
- 본디 10 비단조성성 문제
- ★7 천장 경계 흐림 문제
- ★8 상한 흐림 문제
- ~~캐릭터 외형이 너무 성숙해 보임~~ → **해결** (커밋 `d27bade`) — 판정 기준 선기록(`docs/22-아트.md` 「보상은 바람직해야 한다」) → `faces.py` 전면 재작성 → 514장 재생성 → 78종 격자 시각 검증 → 커밋. 비교용 before 증거는 `faces_current_preview.png`

### 미정 (문서)
- `docs/18` 무명 잔상 "같은 사람 겹치기" 미정
- `docs/13` 3부 미정
- `tools/gacha_sim.py` 섹션 4 구형 모델

### 자아(고유 특성) — 쓰기 시작함 ✅
- **위치**: `data/characters.json`의 각 캐릭터 `unique` 필드 (`name` / `rule` / `line`)
- **완료**: 11명 — 세렌·카브릴·이델·미로·마지막 물장수·도른·유안·깃발을 든 사람·이름을 적던 병사·레안·골목을 메우던 사람
- **규칙**: 문장의 주어는 항상 그 사람 (`02-캐릭터-시스템.md` 4-3). 검증 자 `tools/check_unique.py`가 주어·이름 중복·스키마를 실측
- **스키마**: `data/characters.schema.json` 0.1 견본
- **남음**: ★1~3(무명·편린)은 고유 특성이 아직 없다 — 손으로 쓸 필요는 ★6 도달 시에만, 지금은 전승/기록급부터

---

## 10. 현재 서버 환경

- **Blender**: 5.2.1 LTS (snap, CPU 전용)
- **MPFB 애드온**: 설치됨
- **Node.js**: v22.23.2
- **Chrome**: headless (`google-chrome`)
- **Python 패키지**: PIL, numpy, cv2, websockets 16.0
- **도커 이미지**: `irem-imagegen:latest`, `irem-triposr:latest`

---

## 11. Git 속성

```
Git user: Navifra-Justin
현재 브랜치: main
원격: origin → git@github.com:dpsek007-eng/-NamelessOne.git
`.git` 크기: 약 29M (gc 완료)
```

---

## 12. 다음에 이어서 할 것

1. ~~캐릭터 외형 젊어지기~~ — **완료** (커밋 `d27bade`) — 재작성 · 514장 재생성 · 격자 검증 · 커밋 전부 끝
2. **GitHub push 문제 해결** (권한 또는 deploy key)
3. **소지품 47개 손 뼈 부착**
4. ~~머리·두건 6종 생성~~ — **완료** (`tools/rig.py` + `tools/art.py`, HEAD/BALD 상수, 6타입 분기)
5. **두상 포트레이트 파트 완성** (6×8=48개)
6. **Unity Silhouette.shader 구현**
7. **★7/★8 천장 문제 해결**
8. **docs/13 3부, docs/18 겹치기 미정 해소**
