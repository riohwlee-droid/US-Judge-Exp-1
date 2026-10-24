# Chat이 제출하는 변경 요청

새 JSON 파일만 추가합니다. 양식은 templates/request.json입니다. 이벤트는 프로그램 실행 명령이 아닌 선언적 데이터입니다. base_checkpoint/base_revision은 방금 읽은 CURRENT를 사용합니다. 한 회차에는 하나의 요청만 제출하고 접수증을 확인한 뒤 다음 요청을 만듭니다. 거부된 요청은 수정하지 말고 새 ID로 재제출합니다.
