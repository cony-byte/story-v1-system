# 규칙 변경 비교 — content_type 소급 후 drama_clip 필터 (2026-07-04)

- 구 규칙: 이 커밋 직전의 `규칙_최신.json` (git 이력 참조) — 전체 100편, 기준선 ER 0.42%
- 신(현행): `규칙_최신.json` — **content_type=drama_clip 76편**, 기준선 ER 0.407%
- 소급 분류 분포: drama_clip 76 / trailer_recap 15 / fan_edit 4 / bts 3 / movie_clip 1 / other 1
- 데이터: `로우데이터/0701_크롤링_영상-분석_로우데이터_content_type.csv` (content_type 컬럼 추가본, 원본은 보존)
- 재실행: `python3 engine.py --content-type drama_clip` (필터 없이 실행하면 기존과 동일하게 전체 표본)

## 핵심 변동 — "기존 상위 규칙이 비(非)본편 표본에 의존하고 있었다"

### 1. 트리거(대사문법) 상위권 물갈이
| 태그 | 구→신 순위 | ER 구→신 | 원인 |
|---|---|---|---|
| breakup_rejection_or_distance | **1위 → 8위** | 0.497→0.361 (n 5→2) | 리캡 영상 2편이 견인했던 순위. drama_clip만 남기니 저표본 붕괴 |
| jealousy_possession_or_rival | 3위 → 9위 | 0.454→0.360 | ER 1.46의 BTS(rank4)가 표본에서 제외됨 |
| threat_danger_or_revenge | 6위 → 13위 | 0.44→0.338 | 리캡/트레일러 이탈 |
| choice_ultimatum_or_deadline | 4위 → 7위 | 0.454→0.366 | 동상 |
| misunderstanding_or_accusation | 10위 → 5위 ↑ | 0.404→0.399 | 본편 표본에서 안정적 |
| humiliation_status_drop_or_bullying | 9위 → 4위 ↑ | 0.404→0.399 | 동상 |
| protective_claim_or_rescue (위기구원) | **2위 유지** | 0.496→0.406 | 필터 후에도 생존 — 가장 믿을 만한 트리거 |

### 2. 트로프
- danger_rescue_romance 2→4위 (ER 0.827→0.428 반토막) — 리캡 2편이 절반이었음
- protective_male_or_partner 1위 유지하나 n 2→1 (저표본, 참고용으로만)
- forbidden_love 4→2위 (0.505) — drama_clip 순수 표본에서 상승

### 3. 스토리타입
- jealousy_rival_drama **1위(0.758) → 7위(0.35)** — 구 1위가 BTS+AI영상 의존이었음
- danger_protection_drama 2→8위 (0.497→0.322)

### 4. 컷/연출 지표 — 방향 반전 (가장 중요)
| 지표 | 구 (56편) | 신 (drama_clip 45편) |
|---|---|---|
| 첫3초 클로즈업 (상위 vs 하위) | 0.583 vs 1.0 → "클로즈업 낮을수록 좋음(?)" | **1.0 vs 0.75 → "클로즈업 높을수록 좋음"** |
| 영상 길이 (상위 vs 하위) | 45.9s vs 25.0s (길수록 좋음?) | 38.0s vs 36.6s (차이 소멸 — 길이는 비변별) |
| 총 컷 수 | 16.5 vs 8.5 | 16.0 vs 10.0 (유지 — 컷 많은 쪽 우위) |

구 규칙의 "첫3초 클로즈업 역설"은 비본편(BTS/팬에딧/리캡) 오염이 원인이었다. **본편 기준으로는 첫3초 클로즈업 훅이 정방향으로 작동한다** (영상문법가이드의 클로즈업 훅 원칙과 일치).

## 캐릭터/에피소드 기획에 적용할 갱신 근거 (dashboard 추천용)
1. 1차 트리거 추천 축: **위기구원(protective_claim_or_rescue)** — 필터 전후 모두 상위, 저장률 0.456으로 최상
2. 독점욕·질투는 "강한 트리거" 지위 상실 (기준선 0.407 미달) — 남캐 실험 시 단독 사용 주의
3. 오해·누명 / 굴욕·반전 축 재평가 — 본편 표본에서 기준선 근접 상위권, v2 신설 훅(misunderstanding_hook, humiliation_reversal_hook)과 연결
4. 첫 3초: 클로즈업 훅 정방향 확인 → 스토리보드 규칙 유지·강화
5. n<5 저표본 태그(protective_male, forbidden_love 등)는 다음 크롤링 배치로 검증 필요

## 주의
- drama_clip 76편 중 AI 제작 시리즈 10편 포함 (@catlynx23 4편, @ai.frivolities 6편) — 분리하려면 v2.2에서 `is_ai_generated` 플래그 신설 검토
- content_type은 author/description/transcript 기반 소급 분류 (프레임 미확인). trailer_recap↔drama_clip 경계 편은 재검수 대상
- dashboard(추천)는 Drive의 `00_규칙엔진/규칙_최신.json`을 읽음 → **이 저장소 갱신본을 Drive에도 업로드해야 추천 근거가 실제로 바뀜**
