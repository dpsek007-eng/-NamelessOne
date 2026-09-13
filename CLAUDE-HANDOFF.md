# 이어서.md — 이렘의 탑(TOP) 프로젝트 계속하기

> **이 파일은 Claude Code 세션이 끊겼을 때, 이어서 작업하려면 반드시 읽어라.**
> 마지막 갱신: 2026-09-14, 남은 열린 항목 전부 판정 확인 — 결함이 아니라 설계 결정에 맡긴 것들

---

## 1. 이 저장소는 어디에 있나

- **원본 서버** 경로: `/media/hdd8/justin/my_project/TOP`
- **이사 번들** 경로: `/media/hdd8/justin/my_project/이사/`
  - 번들에 커밋 전부(`bc838aa` 포함)가 들어 있다
- ** 깃허브**(`dpsek007-eng/-NamelessOne`): 원격 `main` = `2f4c59b`, 로컬이 그 뒤 `N`개 앞 (2026-09-14 실측. N = `git rev-list --count 2f4c59b..HEAD` — 밑줄을 덧붙일 때마다 이 문서 맨 위 수치는 늘어난다)
  - `Navifra-Justin` 권한 문제로 push 불가 — dry-run 에러 그대로: `Permission to dpsek007-eng/-NamelessOne.git denied to Navifra-Justin`
  - 미푸시 (9개): `1eef4d9`(계속하기 파일) · `6af537e`(병합) · `e330338`(초상 젊어지기) · `a2daaed`(머리·두건) · `8a07bee`(소지품) · `e00fb08`(판정 기록) · `986c68c`(수치 실측) · `8baf797`(해시 정리) · `9e5ff72`(계수 정리)
  - ※ 종전 「39개 미푸시」는 폐기 — 원격이 이미 `2f4c59b`까지 있었으므로 오래된 수치였다
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

최근 15개 (전체는 `git log`). 작업 순서가 최신이 아래가 아니라 **위**다.

```
8baf797 계속하기 파일의 커밋 해시와 커밋 계수를 맞춘다
986c68c 계속하기 파일의 두 수치를 실측으로 고친다
e00fb08 계속하기 파일에 남은 항목의 판정을 남긴다 — 결함이 아니라 설계 결정
8a07bee 소지품 손 부착 경고를 사실에 맞춘다 — 2D 게임은 이미 해결됨
a2daaed 머리·두건 6종을 붙인다 — 계층이 머리로 읽히게 한다
e330338 초상을 젊고 이쁘게 다시 쓴다 — faces.py 전면 재작성 + 514장 재생성
6af537e 병합: 원격의 고유 특성·초상 연령 조정을 받아들인다
2f4c59b Adjust portrait style + age
8019ba8 초상 카드에 고유 특성을 표시한다
b4dd771 고유 특성 필드를 추가하고 전승·기록급 11명분을 쓴다
1eef4d9 이어서 작업할 수 있도록 규칙과 계속하기 파일을 만든다
bc838aa README 에 화면 찍는 줄을 넣는다
e7de4ff 움직이는 화면은 가상시간으로 못 찍는다 — CDP 로 직접 찍는 자를 만든다
760303a 현황표 두 줄을 사실에 맞춘다 — 한 사람이 아니라 쉰다섯
674cc47 소지품은 실루엣이 아니다 — 문서 세 곳을 고치고, 옮길 짐을 싼다
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
- ~~47개 소지품이 손 뼈에 미부착~~ → **게임 경로에서는 해결됨** — `rig.py:164` draw_prop()가 48×64 스프라이트의 손 위치에 소품을 그린다. TRADE_PROP 47종 전부 매핑, POSE로 캐릭터별 예외 有. `/tmp/prop_grid2.png` 로 시각 검증 완료. ※ 3D 캐스트 GLB(`chars/out/cast/`)에는 부착 안 되어 있음 — 뷰어는 개발용 실루엣 평가 도구이고, 소품이 실루엣으로 역할을 안 가른다는 실험 결과에 부합
- ~~머리·두건 6종 누락~~ → **해결** (커밋 `a2daaed`) — 판정 기준 선기록(`docs/22-아트.md` 「머리·두건 6종」+ 「계층은 읽힌다」: 성직 민머리, 술사 두건, 농어민 머릿수건) → `art.py`에 HEAD/BALD 상수 추가 → `rig.py` look_of/draw 머리 분기 6개 타입 구현 → 유니티 시트 73장 재생성 → `/tmp/head_grid.png` 격자 시각 검증 → 6종 모두 판정 통과
- 두상 6×이목구비 8 포트레이트 파트 누락 → **차단: 이목구비 8개 축이 정의된 곳이 없다.** 6×8=48개를 만들려면 그 8개가 무엇인지(초점이 풀리며 드러나는 얼굴 축) 먼저 정해야 한다. 파트 조립 전에 축 명명이 선행되어야 한다. ⚠ 어느 문서에도 「이목구비 8종」의 목록이 없다
- Unity `Silhouette.shader` / `_Focus` 미구현 → **차단: shader는 이미 있다** (`unity/Assets/Art/Chars/Silhouette.shader` — colour/light/fade 완성, IremChar.cs MaterialPropertyBlock 경로 완결). 누락은 `_Focus` 파라미터 하나뿐이고, 그것은 두상 포트레이트 파트에 매달려 있다
- 깊은 부름 efficiency 1.12배 (목표 미달) → **설계 결정** — `docs/18-소환.md:148` ⚠: 손댈 곳 둘 (① 먼 울림=울림 5개 환산 내리기 ② 고등급 본디 분포 더 기울이기), "지금은 어느 쪽도 하지 않았다. 고르는 것은 설계 결정이라 도구가 정할 일이 아니다." 실측값은 시뮬레이션으로 재확인됨
- 본디 10 비단조성성 문제 → **설계 결정, 미뤄져 있음** — ★3(0.5%) > ★5(0.3%), `docs/18-소환.md:160` "상한을 ★10 으로 열 때 같이 손본다". 지금 상한 ★6에서는 쓰는 값(본디≥6)이 단조롭다
- ★7 천장 경계 흐림 문제 → **설계 결정, 미뤄져 있음** — 상한이 ★6을 넘으면 ★7이 소환 표로 돌아오고 "180회 ★6 확정"이 「꼭대기 확정」→「최악이어도」로 의미가 바뀐다(`docs/18:181`). "★7 을 되돌릴지는 그때 정한다"(`docs/18:100`). 지금은 행 자체가 없다
- ★8 상한 흐림 문제 → **설계 결정, 미뤄져 있음** — 상한이 ★8로 열리면 초점 곡선 STEPS 25→35, ★6 초점 1.00→0.71 로 이미 맞춘 캐릭터가 도로 흐려진다(`docs/13:108`). "기존 도달분을 고정할지 정해야 한다"(`focus_curve.py:104`). 지금 상한 ★6 상태는 일관됨(도구 전부 자가검증 통과)
- ~~캐릭터 외형이 너무 성숙해 보임~~ → **해결** (커밋 `e330338`) — 판정 기준 선기록(`docs/22-아트.md` 「보상은 바람직해야 한다」) → `faces.py` 전면 재작성 → 514장 재생성 → 78종 격자 시각 검증 → 커밋. 비교용 before 증거는 `faces_current_preview.png`

### 미정 (문서)
- `docs/18:243` 무명 잔상 "같은 사람 겹치기" — 전승 40명만 같은 사람이고 확정 지급이라 재획득 경로를 따로 둘지, 무명 잔상의 조각 산출을 올려 메울지. **설계 결정**
- `docs/13:57` 3부 — "1부를 내고 반응을 본 뒤 정한다. 미리 확정하지 않는다." **명시적으로 뒤로 미룬 것**
- `tools/gacha_sim.py` 섹션 4 — 옛 2배 승급 모형 계산인 게 **파일 안에서 고백되고 경고됨**(`gacha_sim.py:73-76,102`). 두 소환 경로의 격차를 상대 비교로 보려고 남겨 둔 것. 미정은 「이 구형 절을 조각 모형으로 다시 쓰느냐」이고, 쓰면 fusion_sim.py 와 중복될 수 있다

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

1. ~~캐릭터 외형 젊어지기~~ — **완료** (커밋 `e330338`) — 재작성 · 514장 재생성 · 격자 검증 · 커밋 전부 끝
2. **GitHub push 문제 해결** (권한 또는 deploy key) — ⛔ 사용자 행동 필요: `dpsek007-eng`가 collaborator 초대를 보내거나, 공개키(`CLAUDE-HANDOFF.md` 1절)를 write 권한 deploy key로 등록해야 한다. 미푸시 N개 (원격 `main`=`2f4c59b`, N = `git rev-list --count 2f4c59b..HEAD`)
3. ~~소지품 47개 손 뼈 부착~~ — **게임 경로 해결** — 2D 스프라이트(draw_prop)에서 47종 전부 손에 그림. 3D 캐스트 GLB에는 미부착 상태이나 실루엣 실험 결과 소품 불가 분리 확인됨
4. ~~머리·두건 6종 생성~~ — **완료** (`tools/rig.py` + `tools/art.py`, HEAD/BALD 상수, 6타입 분기)
5. **두상 포트레이트 파트 완성** (6×8=48개) — ⛔ 차단: 이목구비 8개 축을 먼저 정해야 한다. 정하면 파트 생성 → 유니티 시트 → `_Focus` 순으로 풀린다
6. **Unity Silhouette.shader `_Focus`** — ⛔ 차단: shader 본체는 완성. `_Focus`는 5번의 파트가 준비된 뒤
7. **★7/★8 천장 문제** — 판정 완료: **결함 아님, 열린 설계 결정** — 두 건 다 「상한을 ★8 이상으로 여는 그때」에 다시 정하기로 문서에 명시됨. 지금 ★6 상한 상태는 도구·문서 전부 일관(2026-09-14 회귀 점검 통과)
8. **docs/13 3부, docs/18 겹치기 미정 해소** — ⛔ 설계 결정. 3부는 문서가 명시적으로 "미리 확정하지 않는다"

> **2026-09-14 회귀 점검**: sim 도구 9종 전부 무오류 실행(power · pacing · fusion · cap · summon_value · gacha · bondi · trait_odds · focus_curve), `check_unique` 11명 스키마 통과, `docs/18` 소환 표(★6=5%) ↔ `gacha_sim.py DEEP` 일치. 현재 ★6 상한 상태는 잡혀 있다.
