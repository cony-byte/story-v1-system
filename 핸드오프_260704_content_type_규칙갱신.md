# 핸드오프 — content_type 소급·규칙 재계산·추천 칩 갱신 (2026-07-04)

> 다른 계정/머신에서 이 작업을 그대로 이어받기 위한 문서.
> **이 저장소(cony-byte/story-v1-system main)가 SSOT다.** 로컬 폴더나 Drive 사본이 이 저장소와 다르면 저장소가 맞다.

---

## 0. 이 작업 묶음의 커밋 3개

| 커밋 | 내용 |
|---|---|
| `ebd1deed` | content_type 소급 분류(100편) + engine.py `--content-type` 필터 + drama_clip 76편 기준 규칙 재계산 + 비교 리포트 + 로우데이터 CSV |
| `181630b6` | recommend.py 데이터 칩 정책 갱신 (low_sample 수치 생략 / 기준선 미달 주의 칩 / "현 표본 기준" 표현) |
| `1f9737cb` | engine.py 라벨 사전에 LABELS_V2 41종 추가 → 규칙_최신 hook/story 랭킹 ⟨미분류⟩ 0건 |

구버전이 필요하면 git 이력에서 꺼내면 된다 (별도 백업 파일 없음).

---

## 1. 무엇을 왜 바꿨나

### 1-1. content_type 소급 (스키마 v2.1 §2-3)
0701 크롤링 100편에 `content_type` 컬럼을 소급으로 부여했다 (author/description/transcript 기반, 프레임 미확인이라 경계 사례는 재검수 대상).

- 사전: `drama_clip` / `bts` / `trailer_recap` / `movie_clip` / `fan_edit` / `other`
- 분포: **drama_clip 76 / trailer_recap 15 / fan_edit 4 / bts 3 / movie_clip 1 / other 1**
- 데이터: `00_규칙엔진/로우데이터/0701_크롤링_영상-분석_로우데이터_content_type.csv` (컷 단위 롱 포맷, 같은 영상의 모든 컷 행에 동일 값)
- 분류 기준: 본편 장면 그대로=drama_clip · Trailer/teaser/릴리즈 홍보/내레이션 리캡=trailer_recap · 촬영장=bts · 팬 재편집/배우 에딧=fan_edit · 장편 영화=movie_clip · 추천/리뷰 등 메타=other
- **주의**: drama_clip 76편에 AI 제작 시리즈 10편 포함(@catlynx23 4편, @ai.frivolities 6편). 분리하려면 v2.2에서 `is_ai_generated` 플래그 신설 검토.

### 1-2. engine.py — content_type 필터 (하위 호환)
- `python3 engine.py` → 기존과 완전히 동일 (전체 표본, v1 CSV 하위 호환)
- `python3 engine.py --content-type drama_clip` → 본편만으로 규칙 재계산. **현행 `규칙_최신.json/md`는 이 명령의 산출물이다.**
- 같은 video_id가 여러 CSV에 있으면 content_type 있는 행이 이긴다 (소급본 우선).
- 산출 json에 `content_type_filter` 키가 기록된다.

### 1-3. 규칙 재계산 결과 — 순위 대변동
상세는 `00_규칙엔진/규칙변경_비교_260704_content_type소급.md`. 요약:

- **구 상위 규칙이 비본편 오염이었다**: breakup 상황 1→8위, jealousy_rival극 1→7위(0.758→0.35), danger_rescue 트로프 반토막
- **위기구원(protective_claim_or_rescue)은 필터 전후 모두 2위** — 가장 신뢰할 만한 트리거
- **첫3초 클로즈업 역설 해소**: 본편 기준 상위 1/3이 클로즈업 1.0 vs 하위 0.75 (정방향). 영상 길이는 비변별로 판명
- 기준선 ER 0.42% → 0.407%

### 1-4. recommend.py — 데이터 칩 정책 (`_scripts/recommend.py` `data_chips()`)
- **low_sample(n<4)**: 순위·저장률·도달 수치 칩 전부 생략 → `표본 수집 중(n=N편)` 라벨만. 표본이 차면 수치 칩 자동 복귀
- **ER 기준선 -5% 초과 미달**: "상위권" 강점 대신 `⚠ 현 표본 기준 ER 기준선 미달 (N/M위)` 주의 칩 (독점욕·질투 9/14위 하락이 칩에 그대로 반영됨)
- **±5% 밴드의 이유**: drama_clip 필터 후 태그 중앙값들이 기준선(0.407)에 몰려 있어, 엄격 비교 시 2위(위기구원 0.406)까지 미달 처리됐다. 밴드 폭 조정은 `data_chips()`의 `* 0.95` 한 곳
- 모든 성과 표현에 **"현 표본 기준"** 접두 — 배치 갱신 시 바뀌는 값임을 명시

### 1-5. 라벨 사전 (engine.py `TRIGGER_LABEL`)
- LABELS_V2 41종 병합: 훅 유형 15 + 스토리 구동 9 + 비주얼 훅 7(선등록) + 남주 유형 7(선등록) + v2.1 신설 3(`recap_narration`, `sweet_daily_or_flirting`, `sweet_flirting_or_daily`)
- 용어 체계는 대본 라이브러리 HTML과 동일. 새 태그가 데이터에 등장하면 반드시 여기에 라벨부터 추가 (미등록 시 `⟨미분류:태그⟩`로 노출되는 게 의도된 동작)

---

## 2. 다른 계정에서 재현하는 법

```bash
git clone https://github.com/cony-byte/story-v1-system.git
cd story-v1-system

# 규칙 재계산 (현행 기준)
python3 00_규칙엔진/engine.py --content-type drama_clip

# 검증 1: ⟨미분류⟩ 0건이어야 함
grep -c 미분류 00_규칙엔진/규칙_최신.json 00_규칙엔진/규칙_최신.md

# 검증 2: 추천 칩 확인 (독점욕은 ⚠ 주의, 위기구원은 강점이어야 정상)
python3 _scripts/recommend.py tag jealousy_possession_or_rival
python3 _scripts/recommend.py tag protective_claim_or_rescue
python3 _scripts/recommend.py all
```

기대값: 76편 / 기준선 ER 0.407% / 상황 1위 "일반 대화".

### 계정·권한 주의
- 저장소 쓰기는 **cony-byte** 계정 (JoyJoeng은 pull만 가능). `gh auth status`로 활성 계정 확인.
- 이전 계정 머신의 로컬 폴더 `~/Claude/Projects/영상 기획/`은 **저장소보다 구버전**이다(라벨 체계 없음, recommend.py 없음). 참고하지 말고 저장소 기준으로 작업할 것.

---

## 3. 아직 안 끝난 것 (다음 계정이 할 일)

1. **Drive 동기화**: dashboard(_public)/index.html은 Drive의 `00_규칙엔진/규칙_최신.json`을 런타임에 읽는다. 저장소 갱신본을 dashboard가 보는 Drive 폴더에 업로드해야 추천 UI 근거가 실제로 바뀐다. Drive에 동명 사본이 5개+ 있으니 dashboard의 ROOT 폴더 것만 교체할 것. (judge.py·recommend.py는 저장소 파일을 직접 읽으므로 이미 반영됨)
2. **v2 분류 파이프라인 자동화**: `00_규칙엔진/분류프롬프트_v2.md`(§3 사전 전문 포함)로 LLM 태그 분류 단계 구축. 무발화 영상은 첫 3초 프레임 3장(0s/1.5s/3s, FFmpeg) 입력 필수 — 프레임 없이 컷 지표만으로 분류하면 tag_confidence 0.4~0.55로 전부 검수 큐행(10편 실험으로 실측).
3. **크롤러 개선**: `[NO_AUDIO_STREAM]`은 진짜 무발화가 아니라 오디오 스트림 수집 실패일 수 있다(실측 1건 확인). 마커 구분 컬럼 또는 오디오 재시도 로직 필요.
4. **저표본 태그 검증**: protective_male(n=1), forbidden_love(n=2) 등은 다음 크롤링 배치로 표본 확충 후 판단.
5. **KR 크롤링은 오너가 직접 실행하기 전까지 착수 금지** (스키마 v2 확정사항).

---

## 4. 저장소 밖 산출물 (이전 계정 로컬 `~/Downloads/`, 필요 시 요청)

| 파일 | 내용 |
|---|---|
| `0701_크롤링_영상-분석_로우데이터.csv` | 원본 로우데이터 (읽기 전용 사본이 구 로컬 폴더에도 있음) |
| `260701_크롤링_로우데이터_v2.csv` | 스키마 v2 §2 완전 준수 출력 샘플 (10편 358컷, 신설 13컬럼 포함) |
| `260704_스키마v2_분류실험_10편.csv` | v2 분류 실험 결과 (v1 태그 비교 컬럼 포함 실험 뷰) |

스키마 v2 문서 자체의 SSOT는 아티팩트: https://claude.ai/public/artifacts/f9918853-0bc0-42f9-8b91-a8cfc2e23501 (JS 렌더링이라 브라우저로 열어야 함)
