# 구현과 검사 범위

## 실행

Python 표준 라이브러리만 사용한다. 사용자의 PC는 필요하지 않고 GitHub Actions가 실행한다.

- `python3 -m unittest discover -s tests -v`: 의미 있는 전이·불변성·저장 통합 시험.
- `python3 -m judgesim verify`: CURRENT에서 genesis까지 해시·이벤트 재생·원문 검사.
- `python3 -m judgesim resume`: 현재 플레이어가 볼 수 있는 상태 출력.
- `python3 -m judgesim apply --packet <파일>`: 실행 환경이 있는 경우 직접 후보 저장본 만들기. GitHub 게시 전에는 로컬 후보이며 저장 완료가 아님.
- `python3 scripts/process_requests.py`: 새 요청 처리·접수증 생성. workflow가 결과를 한 번에 커밋한다.

## 이벤트

| type | payload 핵심 |
|---|---|
| system.check | purpose=connection_check, 게임 설정 변경 없음 |
| campaign.configure | user_confirmed, player, court_id, game_time, legal_cutoff |
| person.register | person: id, fictional=true, role, active와 성향·관계 |
| case.register | case: id, fictional, court_id, matter_type, record_status=complete, initial_document_ids, assigned_judges |
| document.register | document: id, case_id, path, sha256, pages, access, status, supersedes 선택 |
| hearing.start | case_id, hearing_id, kind |
| hearing.complete | case_id, hearing_id |
| task.assign | task_id, case_id, assignee_id, instructions, due_at |
| task.complete | task_id, output_document_id |
| draft.start | case_id, author_id |
| opinion.circulate | opinion: id, case_id, document_id, author_id, parts, supersedes 선택 |
| opinion.position | opinion_id, judge_id, disposition, stance, joined_parts, comment |
| opinion.issue | opinion_id, opinion_kind, rule_basis, legal_review_completed |
| precedent.register | precedent: id, opinion_id, origin=simulation, source_type=issued_simulated_opinion, issued_at, authority_status, scope, rule_basis |
| deadline.add | deadline: id, case_id, due_at, basis |
| deadline.satisfy | deadline_id, document_id |
| time.advance | minutes, user_authorized=true |
| scene.set | scene |
| career.record | basis, effective_at, 기타 경력 정보 |

모든 ID는 영문/숫자/점/밑줄/하이픈으로 120자 이하. 시간은 UTC offset을 포함한 ISO 8601이다. 사용자에게는 법원 현지 시간과 한국 시간을 필요에 따라 표시한다. initial_document_ids에 속하는 문서 등록은 case.register 뒤 같은 배치에 넣는다.

## 서버가 검사하는 것

중복 이벤트/상충 ID, 잘못된 상태 전이, 미구현 법원, 법원 capability와 사건 유형, 재판부 외 동참, 없는 문서·쪽, 미제출 증거 접근, 초안 재회람 시 표결 초기화, 완료 보고서의 실제 존재, 오래된 revision, 원문 해시, parent 연결, snapshot/event 재생, 불변 파일 수정 탐지.

## 서버가 보증하지 않는 것

자연어의 완전한 해석, 실질 관할·증거능력, 법률 주장/기한/선례의 정확성, 원문 인용의 의미상 지지, page 분량의 현실성, 인물의 지식 누출이 전혀 없음, 모든 지역규칙의 최신성, 법적 정당한 다수의견 여부. 이 부분은 출처 조사·사건 제작·사람의 판단을 요구한다. opinion.issue의 legal_review_completed는 검토 기록 표시이지 법률 검증 AI가 아니다.

CI는 실패를 탐지하지만 main 쓰기 자체를 막는 branch protection을 설정하지 않았다. 누군가 과거 상태와 검사 코드를 모두 바꾸면 논리적 보호를 우회할 수 있다. Git 커밋 이력이 복구 근거다. 비밀 GM 시스템이나 독립 법률 검증기로 표현하지 않는다.
