# US-Judge-Exp-1

미국 법관 경력을 ChatGPT 대화로 진행하고 GitHub에 기록하는 개인용 시뮬레이션 기반입니다.

**플레이 시작 파일: [START_HERE.md](START_HERE.md)**

## 휴대전화에서 사용

Chat에서 GitHub를 선택하고 이 저장소의 `START_HERE.md`, `AGENTS.md`, `CURRENT.json`과 그 저장본을 읽어 달라고 합니다. GitHub 읽기·쓰기 도구가 있는 대화가 필요합니다. 일반 Chat의 기능 제공과 사용량 차감은 실제 계정에서 확인합니다. 저장소가 모든 대화를 자동 수집하지는 않습니다.

자연어로 행동하면 진행 담당 ChatGPT가 변경 이벤트를 작성합니다. 기본 저장 방식은 `requests/`에 JSON 요청을 올리는 것입니다. GitHub Actions가 이벤트·원문을 검사하고 `saves/`와 `CURRENT.json`, `receipts/`를 갱신합니다. **사용자는 사건 상태 칸을 직접 수정하지 않습니다.** 노트북·상주 서버·별도 AI API는 필요하지 않습니다. Actions는 GitHub 계정의 실행 한도를 사용합니다.

## 현재 구현 상태

| 구분 | 상태 |
|---|---|
| 재개·상태 조회·변경 요청·저장 확인 절차 | 구현 |
| 이벤트 재생, 중복 방지, 오래된 저장본 거부 | 구현 |
| 원문 해시·고정 논리 쪽수·제출 여부 검사 | 구현 |
| 심리, 업무, 집필, 의견 회람·부분 동참, 기한 | 저장 엔진 구현 |
| 경력·가상 선례 | 등록·보존과 검토 기준 구현, 자동 인사·법률 판단 미구현 |
| 50개 주·연방·특수법원 확장 | 목록·조사 양식 마련, 개별 운영 구현은 부임 전에 조사 |
| 실제 플레이 인물·법원·시작 날짜 | 미선택 |
| 실제 법원이 적용된 완성 사건 | 아직 없음 |
| 검증용 기록 | `examples/`에 격리, 실제 플레이가 아님 |

모든 법원을 완성했다고 표시하거나, 이름만 있는 사건을 플레이 가능한 기록으로 취급하지 않습니다. 시작 법원과 가상 인물·날짜를 정하고 해당 법원의 규칙과 첫 사건 원문을 준비한 뒤 플레이합니다.

## 주요 파일

- [START_HERE.md](START_HERE.md): 새 대화 시작·재개
- [AGENTS.md](AGENTS.md): 진행 담당 AI 운영 규칙
- [docs/SAVE_PROTOCOL.md](docs/SAVE_PROTOCOL.md): 휴대전화 기반 저장·복구
- [docs/PLAY_RULES.md](docs/PLAY_RULES.md): 시간·대화·심리·합의·인물
- [docs/RECORDS.md](docs/RECORDS.md): 원문·증거·인용·사건 제작
- [docs/COURTS_AND_LAW.md](docs/COURTS_AND_LAW.md): 법원 조사·실제 법률 자료
- [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md): 데이터·검사 범위·한계
- [docs/ROADMAP.md](docs/ROADMAP.md): 남은 제작 작업
- [docs/CHAT_PROJECT_INSTRUCTIONS.md](docs/CHAT_PROJECT_INSTRUCTIONS.md): 일반 Chat 프로젝트에 넣을 짧은 지침

개발·검사는 서버에서 `python3 -m unittest discover -s tests -v`, `python3 -m judgesim verify`로 실행합니다. 사용자의 PC 실행은 필요하지 않습니다. 이 저장소의 Python은 대화와 법률 논증을 생성하는 AI가 아닙니다.
