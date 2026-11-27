# US Judge Experience — Federal Courts of Appeals

미국 연방항소법원 판사 전용 시뮬레이션. ChatGPT에서 심리·합의·집필을 진행하고 GitHub에 기록한다. [시작 지침](START_HERE.md) · [사건 업무 사이트](CASEBOOK.md).

## 현재 상태
- 제9순회항소법원(CA9) 확정. 일반 합의부 핵심 규칙 구현; 가상 판사·게임 날짜·사건 미확정. [운영 패키지](courts/ca9/OPERATIONS.md).
- 메인주 캠페인은 종료하고 기본 브랜치에서 제거. 기존 기록은 archive/maine-law-court 브랜치에 보존.
- 기존 이벤트 저장 엔진, 검증, 원문 해시, 부분 동참·회람·선례 장부 유지.
- 공식 저장본은 CURRENT.json → manifest/state. 사이트는 이 저장본을 실시간 조회하는 읽기 전용 뷰어 초안이며 Pages 활성화 필요.
- 별도 AI API는 없음. GitHub Actions/ChatGPT 이용 한도 적용. 이 저장소는 공개이며 기술적 비밀 보장 없음.

다음: 제9순회 핵심 운영규칙 구현 → 가상 재판부 → 완전한 첫 사건 기록 → 검증 후 배당.
