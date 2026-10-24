# Chat + GitHub 저장 프로토콜

## 공식 저장본

CURRENT.json이 가리키는 saves/<id>/manifest.json, state.json, events.json이 공식 상태다. state는 사건·문서·기한·표결·경력의 한 시점 스냅샷이다. events는 직전 저장본 이후의 변경 원인이며, 처음부터 재생했을 때 같은 state가 나와야 한다. 수정 가능한 두 개의 독립 장부를 만들지 않는다.

체크포인트와 원문은 새 경로에만 추가한다. 마지막 확정 지점은 CURRENT로 찾고 그 parent를 따라 복구한다. 임의로 CURRENT를 과거로 되돌리지 않는다. 복구하려면 별도 브랜치/명시적 복원 작업으로 새 진행선을 만들고 사용자의 결정을 받는다.

## 기본: 서버가 계산하는 저장

1. 대화 담당 AI는 main HEAD SHA, CURRENT의 checkpoint와 revision을 읽는다.
2. 원문이 생겼으면 records/<case>/<document>-v1.md에 온전한 내용을 쓴다. 원문 파일이 먼저 올라가도 등록 전에는 판사의 제출 기록이 아니다.
3. templates/request.json 양식으로 requests/<고유-request-id>.json을 추가한다. base_checkpoint/base_revision, 새로운 checkpoint ID, 고유 event ID를 쓴다. 문서 해시는 server_computed로 두어도 된다.
4. GitHub Actions 'Publish chat save'가 최신 main에서 요청을 처리한다. 같은 저장소의 발행 작업은 직렬화한다. 신뢰하지 않은 임의 명령은 실행하지 않는다.
5. 서버가 이벤트·문서 원문·쪽수·일관성을 검사하고 스냅샷·접수증을 만든다. 이전 저장본을 기준으로 한 요청은 rejected다. 원문·직원 보고가 실제 생성되지 않았다면 완료 이벤트도 거부한다.
6. 봇이 하나의 커밋으로 CURRENT + saves + receipts를 게시한다. push가 충돌하면 강제 덮어쓰지 않고 실패한다. 다음 실행/재시도 때 최신 main을 기준으로 다시 평가한다.
7. Chat은 receipts/<request-id>.json의 accepted, 해당 manifest와 CURRENT 또는 그 parent 연결을 읽는다. 가능하면 발행 커밋 SHA도 확인한다. 그때만 저장 완료라고 말한다.

여러 파일을 각각 갱신하는 동안의 부분 상태는 공식 저장으로 읽지 않는다. 요청 작성 커밋과 발행 커밋은 다르다. 연결 시험 접수증은 게임 시작을 뜻하지 않는다.

## 대기·실패

| 상태 | 사용자 안내와 다음 행동 |
|---|---|
| 요청만 존재 | 저장 처리 대기. 시간이 걸리면 Actions 실행 상태 확인 |
| accepted + 연결 확인 | 저장 완료. checkpoint/revision과 실제 커밋 알림 |
| rejected stale base | 최신 상태를 읽고 새 요청 ID로 행동을 재구성 |
| rejected 검증 오류 | 원인을 고쳐 새 요청 추가. 거부된 요청/접수증 보존 |
| workflow 실패/쓰기 불가 | 실패 사실 알림. 워크플로 권한·실행 한도·브랜치 정책 확인 |
| 도구가 없음 | 갱신 묶음을 사용자에게 전달. 저장소 반영 전까지 미저장 |

실패가 반복될 때 무제한 도구 호출/폴링을 하지 않는다. 실행 중이면 잠깐 기다린 뒤 상태를 알리고 다음 대화에서도 확인할 수 있게 request ID를 남긴다.

## 도구로 직접 저장하는 대안

Actions를 쓸 수 없지만 실행·검증 도구가 있는 환경에서는 Python으로 후보 저장본을 검증하고 Git data API로 새 tree/commit을 생성한다. 현재 branch HEAD를 예상 SHA로 묶어 fast-forward update_ref 한다. main이 바뀌면 최신 HEAD를 재조회하고 재검증한다. force push는 금지한다. 직접 저장에서도 새 접수증을 만들고 체크포인트와 함께 게시한다.

실행 도구가 없는 Chat에서는 직접 스냅샷·다이제스트를 손으로 작성하여 검증됐다고 하지 않는다. Actions를 켜거나, 실행 가능한 환경에서 일괄 반영하는 대안을 사용한다.

## 중복·충돌

이벤트 ID와 내용 해시가 같으면 재생은 한 번만 반영한다. ID는 같지만 내용이 다르면 거부한다. 동일 요청의 중복 처리는 접수증으로 차단한다. Chat/Work 두 창에서 동시에 플레이하지 않는 것을 기본으로 한다. GitHub는 자연어 대화의 전역 잠금 장치가 아니다.

## 비용과 제약

AI API 호출은 없다. GitHub Actions는 GitHub의 실행 시간·스토리지 한도와 계정 설정에 따른다. 무제한 무료를 보장하지 않는다. 사용자 PC가 없어도 실행된다. 워크플로 파일 쓰기/실행·봇의 contents:write가 허용되어야 하며, 브랜치 보호나 조직 정책에 막히면 상태를 알린다. 이 저장소는 사용자 계정의 보안·사용량 설정을 자동 변경하지 않는다.
