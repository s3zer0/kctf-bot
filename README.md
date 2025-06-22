# Discord 티켓 봇 + CTFd First Blood 알림

Discord 티켓 시스템과 CTFd First Blood 알림 기능을 통합한 봇입니다.

## 기능

### 티켓 시스템
- 버튼을 통한 간편한 티켓 생성
- 티켓 담당자 지정 (claim) 기능
- 트랜스크립트 자동 생성 및 DM 전송
- 티켓 관리 명령어 (이름 변경, 주제 변경 등)

### CTFd First Blood 알림 (새 기능!)
- CTFd 플랫폼에서 First Blood 이벤트 자동 감지
- Discord 채널로 실시간 알림 전송
- 카테고리별 색상 구분
- 문제 정보, 솔버 정보, 점수 표시

## 설치

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 입력:

```env
# Discord 설정
DISCORD_TOKEN=your_bot_token
GUILD_ID=your_server_id
LOG_CHANNEL_ID=log_channel_id
TICKET_CATEGORY_ID=ticket_category_id
SUPPORT_ROLE_ID=support_role_id
ADMIN_ROLE_ID=admin_role_id

# CTFd 설정 (선택사항)
CTFD_URL=https://your-ctf.com
CTFD_API_TOKEN=your_api_token
CTFD_POLL_INTERVAL=30
```

### 3. CTFd API 토큰 얻기
1. CTFd 관리자로 로그인
2. Settings → Access Tokens
3. "Generate" 클릭하여 새 토큰 생성

## 사용법

### 티켓 시스템 명령어
- `/setup` - 티켓 생성 패널 설치 (관리자)
- `/claim` - 티켓 담당하기 (지원팀)
- `/close` - 티켓 종료
- `/add @사용자` - 티켓에 사용자 추가
- `/remove @사용자` - 티켓에서 사용자 제거
- `/rename 이름` - 티켓 이름 변경
- `/topic 주제` - 티켓 주제 변경
- `/checkconfig` - 봇 설정 확인 (관리자)

### CTFd 알림 명령어
- `/ctfd-setup [채널]` - CTFd 알림 채널 설정 (관리자)
- `/ctfd-start` - First Blood 모니터링 시작
- `/ctfd-stop` - First Blood 모니터링 중지
- `/ctfd-status` - 모니터링 상태 확인
- `/ctfd-test` - CTFd API 연결 테스트
- `/ctfd-reset` - First Blood 알림 기록 초기화 (관리자)

## CTFd 알림 설정 방법

1. **CTFd API 토큰 생성**
   - CTFd 관리자 계정으로 로그인
   - Settings → Access Tokens에서 토큰 생성

2. **.env 파일 업데이트**
   ```env
   CTFD_URL=https://your-ctf.com
   CTFD_API_TOKEN=생성한_토큰
   ```

3. **봇 재시작**
   ```bash
   python main.py
   ```

4. **Discord에서 설정**
   ```
   /ctfd-setup #알림채널
   /ctfd-start
   ```

## 주의사항

- CTFd 기능은 선택사항입니다. 설정하지 않으면 티켓 봇만 작동합니다.
- First Blood 알림은 한 번만 전송됩니다 (재시작해도 중복 알림 없음).
- 새 CTF 대회를 시작할 때는 `/ctfd-reset` 명령어로 기록을 초기화하세요.

## 문제 해결

### CTFd 연결 오류
- API 토큰이 올바른지 확인
- CTFd URL이 정확한지 확인 (https:// 포함)
- 방화벽이 CTFd 서버 접근을 차단하지 않는지 확인

### 알림이 오지 않음
- `/ctfd-status`로 모니터링 상태 확인
- 알림 채널이 올바르게 설정되었는지 확인
- 봇이 해당 채널에 메시지 전송 권한이 있는지 확인