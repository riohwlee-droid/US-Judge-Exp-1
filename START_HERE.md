# 연방항소법원 판사 — 시작/재개

저장소 riohwlee-droid/US-Judge-Exp-1, main. 메인주 캠페인을 재개하지 않는다.

1. main HEAD를 확인하고 같은 SHA로 AGENTS.md, CURRENT.json, 해당 manifest와 state를 읽는다.
2. 이전 요청이 있으면 receipts의 accepted 및 CURRENT 연결을 확인한다.
3. checkpoint/revision/게임 날짜/법원/현재 장면/기한을 알린다. setup_required이면 아직 부임/사건 배당이 없음을 알린다.
4. 첫 시작이면 연방항소법원(제1~11순회, D.C., Federal Circuit), 가상 판사 이름, 게임 날짜를 정한다. Federal Circuit은 전문 관할이다. 순회법원 선택을 임의 확정하지 않는다.
5. 선택 법원의 FRAP, 지역규칙, IOP, 관할·윤리·인사·합의·집필 관행을 실제 출처로 조사한다. 법원 프로필과 가상 인물, 첫 사건 전체 기록 검증 이후에만 ready 및 campaign.configure를 허용한다.

플레이는 한국어 자연어, 서류 원문은 영어 기본. 원심 기록 열람, 구두변론, 로클럭 지시, 비공개 합의, 부분 동참, 초안 회람 및 별개·반대의견 집필을 지원한다. 실제 법·판례와 가상 선례는 구분한다. 저장 도구와 accepted 접수증 없이 저장 완료라고 하지 않는다.
