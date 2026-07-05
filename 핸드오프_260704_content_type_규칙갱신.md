# 핸드오프 — content_type·male_lead 축 가동·발행성과·대시보드 편집·자동화 연결 (2026-07-04 ~ 07-05)

> 다른 계정/머신에서 이 작업을 그대로 이어받기 위한 문서.
> **이 저장소(cony-byte/story-v1-system main)가 SSOT다.** 로컬 폴더나 Drive 사본이 이 저장소와 다르면 저장소가 맞다.

---

## 0. 이 작업 묶음의 커밋 8개 (시간순)

| 커밋 | 내용 |
|---|---|
| `ebd1deed` | content_type 소급 분류(100편) + engine.py `--content-type` 필터 + drama_clip 76편 기준 규칙 재계산 + 비교 리포트 + 로우데이터 CSV |
| `181630b6` | recommend.py 데이터 칩 정책 갱신 (low_sample 수치 생략 / 기준선 미달 주의 칩 / "현 표본 기준" 표현) |
| `1f9737cb` | engine.py 라벨 사전에 LABELS_V2 41종 추가 → 규칙_최신 hook/story 랭킹 ⟨미분류⟩ 0건 |
| `15a5f80d` | 핸드오프 문서 + 분류프롬프트_v2.md(§3 사전 전문) 저장소 수록 |
| `ec023d2e` | drama_clip 76편에 male_lead_type 소급(+male_lead_confidence) + 10편 실험 CSV를 로우데이터/로 이동 |
| `b5879743` | engine에 male_lead_ranking 집계 (다중 태그 중복 카운트, 저표본 n<10 별도, unknown 제외) + md 섹션 |
| `551f047a` | recommend find_entry가 male_lead_ranking 축 조회 → 남주 유형 데이터 칩 활성화 |
| `4f2f06aa` | 발행성과 템플릿 engine 연결 (복합키·D7 고정·ER 자동계산) + 발행성과_운영.md |

이 밖의 커밋: `cbb0ebc8`(고정 상수 대시보드 편집), `5cc5b865`(치환 규칙 프리셋),
`499506e0`(**CI: 로우데이터 CSV 커밋 시 규칙 자동 재계산** — `.github/workflows/recalc-rules.yml`),
`7514aa9e`(recalc-bot의 첫 자동 재계산 커밋), `0b484a19`(대시보드 TRIG 폴백 라벨을 엔진 사전과 통일),
`6e2a3819`(대시보드에 남주 유형 순위 카드). 이제 로우데이터 CSV를 push하면 규칙_최신.json/md는 봇이 갱신한다.

**관련 저장소 3개**: 이 repo(기획 SSOT) + [story-v1-crawler](https://github.com/cony-byte/story-v1-crawler)(크롤링 생산, `publish.py`로 연결) + [story-v1-scripts](https://github.com/cony-byte/story-v1-scripts)(대본 라이브러리, Actions `rebuild-library`가 이 repo 로우데이터를 매일 00시 KST에 읽어 리빌드).

구버전이 필요하면 git 이력에서 꺼내면 된다 (별도 백업 파일 없음).

---

## 1. 무엇을 왜 바꿨나

### 1-1. content_type 소급 (스키마 v2.1 §2-3)
0701 크롤링 100편에 `content_type` 부여 (author/description/transcript 기반, 프레임 미확인이라 경계 사례는 재검수 대상).

- 사전: `drama_clip` / `bts` / `trailer_recap` / `movie_clip` / `fan_edit` / `other`
- 분포: **drama_clip 76 / trailer_recap 15 / fan_edit 4 / bts 3 / movie_clip 1 / other 1**
- 데이터: `00_규칙엔진/로우데이터/0701_크롤링_영상-분석_로우데이터_content_type.csv`
- **주의**: drama_clip 76편에 AI 제작 시리즈 10편 포함(@catlynx23 4, @ai.frivolities 6). 분리하려면 v2.2에서 `is_ai_generated` 플래그 검토.

### 1-2. engine.py — content_type 필터 (하위 호환)
- `python3 engine.py` → 기존과 동일 (전체 표본). `--content-type drama_clip` → 본편만 재계산. **현행 `규칙_최신.json/md`는 후자의 산출물.**
- 같은 video_id가 여러 CSV에 있으면 content_type 있는 행(소급본)이 이긴다.

### 1-3. 규칙 재계산 — 순위 대변동 (상세: `규칙변경_비교_260704_content_type소급.md`)
- **구 상위 규칙이 비본편 오염이었다**: breakup 상황 1→8위, jealousy_rival극 1→7위, danger_rescue 트로프 반토막
- **위기구원(protective_claim_or_rescue)은 필터 전후 모두 2위** — 가장 신뢰할 만한 트리거
- **첫3초 클로즈업 역설 해소**: 본편 기준 상위 1/3 클로즈업 1.0 vs 하위 0.75 (정방향). 기준선 ER 0.42→0.407%

### 1-4. recommend.py — 데이터 칩 정책 (`_scripts/recommend.py` `data_chips()`)
- low_sample: 수치 칩 생략 → `표본 수집 중(n=N편)` 라벨만 (표본 차면 자동 복귀)
- ER 기준선 **-5% 초과** 미달: `⚠ 현 표본 기준 ER 기준선 미달` 주의 칩. ±5% 밴드인 이유: 태그 중앙값이 기준선에 몰려 있어 엄격 비교 시 2위(위기구원 0.406 vs 0.407)까지 미달 처리됨. 밴드 조정은 `data_chips()`의 `* 0.95` 한 곳.
- 모든 성과 표현에 "현 표본 기준" 접두

### 1-5. 라벨 사전 (engine.py `TRIGGER_LABEL`)
- LABELS_V2 41종: 훅 15 + 스토리 9 + 비주얼 훅 7(선등록) + 남주 유형 7(선등록) + v2.1 신설 3
- 용어는 대본 라이브러리 HTML과 동일 체계. 새 태그는 라벨부터 등록 (미등록 시 `⟨미분류:태그⟩` 노출이 의도된 동작)

### 1-6. male_lead_type 축 — 엔드투엔드 가동 (스키마 v2 §5 마지막 체크리스트 완료)
남캐 실험 단위와 직결되는 최우선 축. 3단계로 연결:

1. **데이터** (`ec023d2e`): drama_clip 76편에 §3-6 사전으로 소급 (영상당 최대 2태그, `male_lead_confidence` 병기). 근거는 스크립트>설명 — desc 단서만 있는 편은 conf 0.3~0.5 저신뢰 → 검수 대상.
2. **엔진** (`b5879743`): `male_lead_ranking` — 다중 태그 중복 카운트, ER·저장률 중앙값+n, **이 축만 저표본 n<10**, unknown 제외.
3. **추천** (`551f047a`): `find_entry()` 조회 축에 추가 → 칩 자동 활성화.

**첫 랭킹 (76편, 판별 가능 60편)**: 집착·독점형 1위(n=17, ER 0.483, 기준선 상회) > 직진·헌신형(14, 0.449) > 위험·금기형(16, 0.421) > [냉정→다정 n=9 수집 중] > **권력·재벌형(33, 0.365 기준선 미달 — 최다 표본인데 약함)** > [위기구원·보호형 n=3 수집 중].
읽을거리: 대사문법 축의 독점욕은 9위로 하락했지만 남주 유형 축의 집착·독점형은 1위 — "질투 대사"와 "집착형 캐릭터"는 다른 축이라는 게 실측으로 갈라졌다.

### 1-7. 발행성과 연결 — 예측 vs 실제 루프 (`4f2f06aa`, 운영 규칙: `발행성과_운영.md`)
- **연결 키 = `{character_id}/{ep_id}` 복합키** (예: `char_seojun/ep_01`). ep_01이 캐릭터별로 겹치므로 필수. 이 키로 기획의 target_trigger를 찾아 크롤링 트리거 통계에 합산.
- 템플릿(`발행성과_템플릿.csv`) 컬럼은 크롤링 스키마와 동일 지표 필드명. ER%·저장률%는 엔진이 자동 계산.
- 측정 시점 고정: D+7 기본, D+30은 행 추가(시계열 보존, 집계는 D7만). notes "예시" 행 자동 스킵. 자체발행은 content_type 필터 면제.
- 절차: Drive 입력 시트 → CSV 내보내기 → `발행성과/` 투입 → engine 재실행.

### 1-8. 대시보드(app-shell.html) — 팀 편집·표시 기능
- **고정 상수 편집** (`cbb0ebc8`): 세계관·여주 카드의 ✏️ 수정 버튼 → 인라인 폼 → 저장 시 `driveUpdateJson`으로 Drive의 01_세계관.json/02_여주.json 직접 갱신 + 파생 화면 재렌더. id는 참조 고정 키라 잠금.
- **치환 규칙 프리셋** (`5cc5b865`): 보편 소재 5축(재벌CEO/계약결혼/권력차/정략/조폭)을 세계관 유형별로 번역한 내장 사전 `WORLD_RULE_PRESETS`. 유형 키 8종은 **스키마 v2.1 setting 사전(§3-7)과 동일 체계**. 규칙 기반·LLM 없음 — 팀원은 유형 선택→자동 채우기→저장 3클릭.
- **남주 유형 순위 카드** (`6e2a3819`): 규칙 카드에 `male_lead_ranking` 테이블. n<10은 recommend 칩과 동일하게 수치 숨기고 "표본 수집 중 · n=N" 필. 랭킹 키가 없으면(구버전 Drive 규칙) 교체 안내 문구가 뜨는 게 의도된 동작.
- **라벨 원천**: 대시보드 표시 라벨은 규칙_최신.json의 `label` 필드를 그대로 씀 — 엔진 라벨 사전이 바뀌면 JSON 재생성만으로 따라옴. RULES 로드 전 폴백 `TRIG` 사전은 엔진과 용어 통일됨(`0b484a19`) — 앞으로도 엔진 사전 수정 시 함께 맞출 것.
- 퍼블 배포는 GitHub Pages(cony-byte.github.io/story-v1-system) — repo push로 코드는 자동 배포, **데이터(규칙 JSON)는 Drive 교체 필요**.

---

## 2. 다른 계정에서 재현하는 법

```bash
git clone https://github.com/cony-byte/story-v1-system.git
cd story-v1-system

# 규칙 재계산 (현행 기준)
python3 00_규칙엔진/engine.py --content-type drama_clip

# 검증 1: ⟨미분류⟩ 0건
grep -c 미분류 00_규칙엔진/규칙_최신.json 00_규칙엔진/규칙_최신.md

# 검증 2: 추천 칩 (독점욕 대사문법=⚠주의 / 위기구원=강점 / 남주 유형 칩)
python3 _scripts/recommend.py tag jealousy_possession_or_rival
python3 _scripts/recommend.py tag protective_claim_or_rescue
python3 _scripts/recommend.py tag dominant_possessive      # → "현 표본 기준 ER 1위, n=17"
python3 _scripts/recommend.py tag cold_to_warm             # → "표본 수집 중(n=9편)"
python3 _scripts/recommend.py all
```

기대값: 76편 / 기준선 ER 0.407% / 상황 1위 "일반 대화" / 남주 유형 1위 집착·독점형.

### 계정·권한 주의
- 저장소 쓰기는 **cony-byte** 계정 (JoyJoeng은 pull만). `gh auth status`로 활성 계정 확인.
- 이전 계정 머신의 로컬 `~/Claude/Projects/영상 기획/`은 **저장소보다 구버전** — 참고 금지, 저장소 기준으로 작업.

---

## 3. 아직 안 끝난 것 (다음 계정이 할 일)

1. ~~Drive 동기화~~ → **✅ 완료 (2026-07-05 02:48)**: 오너가 대시보드 고정 폴더(공유드라이브 기획-v2/00_규칙엔진)의 `규칙_최신.json`을 최신본으로 교체 — 사본 1개·바이트 일치까지 검증됨. 이제 대시보드에 한글 라벨·drama_clip 순위·남주 유형 카드가 반영된다.
   **단, 이건 반복 루틴이다**: CI(recalc-bot)가 저장소의 규칙_최신을 자동 갱신해도 **Drive 교체는 매번 수동**. 새 크롤링 배치가 규칙을 바꿀 때마다 repo의 `00_규칙엔진/규칙_최신.json`을 받아 같은 방식(기존 파일 삭제 후 업로드 — Drive는 동명 업로드 시 사본을 만들기 때문)으로 교체할 것. judge.py·recommend.py는 저장소 파일을 직접 읽어 교체 불필요.
2. **발행성과 실무 합의**: episode_id **복합키 형식**(`char_x/ep_y`)을 실무자와 지금 합의 + Drive 입력 시트의 예시 행을 복합키 형식으로 교정. 소급은 지옥이다.
3. **male_lead 소급 검수**: `male_lead_confidence`<0.7이 65편 (desc 기반 다수). 자동화 파이프라인의 프레임 기반 재분류 또는 사람 검수로 정제 후 랭킹 재신뢰.
4. **크롤러 스모크 테스트**: 자동화 파이프라인은 **별도 저장소 https://github.com/cony-byte/story-v1-crawler (private)**에 6단계 전체 구현 완료(`run.py --market EN`, whisper+Claude 분류, 오디오 재시도 포함). crawler `publish.py` → 이 저장소 로우데이터 push → CI 자동 재계산까지 연결 검증됨. **단 실크롤링(TikTok 차단 가능)·YOLO·whisper는 미검증 — 첫 실행은 `--limit 5` 스모크 권장.** 상세는 crawler 저장소의 `HANDOFF.md`.
5. **저표본 태그 확충**: 냉정→다정형(n=9, 1편 차이로 수집 중), 위기구원·보호형(n=3), protective_male 트로프(n=1) 등 — 다음 크롤링 배치로 채워짐.
6. **KR 크롤링은 오너가 직접 실행하기 전까지 착수 금지** (스키마 v2 확정사항).

---

## 4. 저장소 밖 산출물 (이전 계정 로컬, 필요 시 요청)

| 위치 | 내용 |
|---|---|
| `~/Downloads/0701_크롤링_영상-분석_로우데이터.csv` | 원본 로우데이터 (저장소에는 소급 태깅본만 있음) |
| `~/Downloads/발행성과 템플릿.csv` | 복합키 형식 교정본 (Drive 시트 교정용) |
| `~/Downloads/260704_스키마v2_분류실험_10편.csv` | v2 분류 실험 뷰 (v1 태그 비교 컬럼 포함) |
| `~/Downloads/기획-v2/` | 저장소 main 통짜 내보내기 (Drive 업로드용 패키지, 2026-07-05 기준) |
| `~/Downloads/규칙_최신.json` | repo main 최신 규칙 단일 추출본 (07-05 02:48 Drive 교체 완료 — 다음 교체 때 새로 추출할 것) |

※ `260701_크롤링_로우데이터_v2.csv`(10편 실험본)는 저장소 `로우데이터/`로 이동 완료.
스키마 v2 문서 SSOT는 아티팩트: https://claude.ai/public/artifacts/f9918853-0bc0-42f9-8b91-a8cfc2e23501 (JS 렌더링 — 브라우저로 열 것)
