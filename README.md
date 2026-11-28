# US Judge Experience — Federal Courts of Appeals

미국 연방항소법원 판사 전용 시뮬레이션. ChatGPT에서 심리·합의·집필을 진행하고 GitHub에 기록한다. [시작 지침](START_HERE.md) · [사건 업무 사이트](CASEBOOK.md).

## 현재 상태
- 제9순회항소법원(CA9) 확정. 일반 합의부 및 재심리·제한적 전원합의체·mandate v2 규칙 구현; 가상 판사단·직원 명단 준비 완료(미설치); 플레이어·게임 날짜·사건 미확정. [조직 및 인물](courts/ca9/ORGANIZATION.md). [운영 패키지](courts/ca9/OPERATIONS.md) · [절차 엔진](courts/ca9/LIFECYCLE.md).
- 메인주 캠페인은 종료하고 기본 브랜치에서 제거. 기존 기록은 archive/maine-law-court 브랜치에 보존.
- 기존 이벤트 저장 엔진, 검증, 원문 해시, 부분 동참·회람·선례 장부 유지.
- 공식 저장본은 CURRENT.json → manifest/state. 사이트는 이 저장본을 실시간 조회하는 읽기 전용 뷰어 초안이며 Pages 활성화 필요.
- 별도 AI API는 없음. GitHub Actions/ChatGPT 이용 한도 적용. 이 저장소는 공개이며 기술적 비밀 보장 없음.

다음: 제9순회 핵심 운영규칙 구현 → 가상 재판부 → 완전한 첫 사건 기록 → 검증 후 배당.

- [초정밀 사건 생성 금형](courts/ca9/CASE_FACTORY.md): 단계별 제작, 원문·인용 검증, 봉인·배당 게이트. 실제 첫 사건은 아직 미제작.

- [법률조사 및 인용 검증](courts/ca9/LEGAL_RESEARCH.md): 실제 원문·명제별 효력·후속취급·문서 인용 검증, 연구보고서와 초안 검증 게이트.

- [지속형 사건 생산·공급 시스템](courts/ca9/SUPPLY.md): 검증 대기열, 재작업, 봉인 재고, 서기국 접수 및 배당 통지. [재고 집계](supply/PUBLIC.json) (공식 상태와 revision 대조).
