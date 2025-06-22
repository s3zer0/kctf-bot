import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Set, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FirstBloodMonitor:
    """First Blood 이벤트를 모니터링하고 관리하는 클래스"""
    
    # 카테고리별 색상 매핑
    CATEGORY_COLORS = {
        'web': 0x3498db,      # 파란색
        'pwn': 0xe74c3c,      # 빨간색
        'crypto': 0x2ecc71,   # 초록색
        'rev': 0x9b59b6,      # 보라색
        'forensics': 0x34495e, # 회색
        'misc': 0xf39c12,     # 주황색
        'default': 0x7289da   # Discord 기본 색상
    }
    
    def __init__(self, ctfd_api, state_file: str = 'first_bloods.json'):
        self.ctfd_api = ctfd_api
        self.state_file = Path(state_file)
        self.notified_challenges: Set[int] = self._load_state()
        self.alert_channel = None  # Discord 채널 객체
        self.use_submissions_api = False  # 제출 API 사용 여부
    
    def _load_state(self) -> Set[int]:
        """이전에 알림을 보낸 챌린지 ID 목록을 로드"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('notified_challenges', []))
            except Exception as e:
                logger.error(f"상태 파일 로드 실패: {e}")
        return set()
    
    def _save_state(self):
        """현재 상태를 파일에 저장"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'notified_challenges': list(self.notified_challenges),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"상태 파일 저장 실패: {e}")
    
    def set_alert_channel(self, channel):
        """알림을 보낼 Discord 채널 설정"""
        self.alert_channel = channel
    
    async def create_first_blood_embed(
        self,
        challenge_name: str,
        solver_name: str,
        team_name: Optional[str],
        category: str,
        points: int,
        solve_time: datetime
    ) -> dict:
        """First Blood Discord 임베드 생성"""
        
        # 카테고리에 따른 색상 선택
        color = self.CATEGORY_COLORS.get(
            category.lower(), 
            self.CATEGORY_COLORS['default']
        )
        
        # 솔버 표시 텍스트 생성
        solver_display = solver_name
        if team_name:
            solver_display = f"{solver_name} ({team_name})"
        
        # 임베드 생성
        embed = {
            "title": "🩸 First Blood! 🩸",
            "description": f"**{solver_display}** 님이 **{challenge_name}** 문제를 가장 먼저 해결했습니다!",
            "color": color,
            "fields": [
                {
                    "name": "📁 카테고리",
                    "value": category.upper(),
                    "inline": True
                },
                {
                    "name": "🏆 점수",
                    "value": f"{points} pts",
                    "inline": True
                },
                {
                    "name": "⏱️ 해결 시간",
                    "value": solve_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "inline": True
                }
            ],
            "footer": {
                "text": "CTFd First Blood Alert",
                "icon_url": "https://raw.githubusercontent.com/CTFd/CTFd/master/CTFd/themes/core/static/img/logo.png"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return embed
    
    def _get_challenge_solves(self, challenge_id: int) -> List[Dict]:
        """챌린지의 솔브 정보를 가져옴 - 여러 방법 시도"""
        
        # 방법 1: 기본 solves 엔드포인트
        solves = self.ctfd_api.get_challenge_solves(challenge_id)
        if solves:
            logger.debug(f"Challenge {challenge_id}: {len(solves)} solves found via /solves")
            return solves
        
        # 방법 2: submissions API 사용
        logger.debug(f"Challenge {challenge_id}: Trying submissions API")
        import requests
        
        headers = {
            'Authorization': f'Token {self.ctfd_api.api_token}',
            'Content-Type': 'application/json'
        }
        
        # 정답 제출만 필터링
        url = f"{self.ctfd_api.base_url}/api/v1/submissions?challenge_id={challenge_id}&type=correct"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                submissions = data.get('data', [])
                if submissions:
                    logger.info(f"Challenge {challenge_id}: {len(submissions)} correct submissions found")
                    self.use_submissions_api = True
                    return submissions
        except Exception as e:
            logger.error(f"Submissions API 오류: {e}")
        
        return []
    
    async def check_for_first_bloods(self):
        """모든 챌린지를 확인하여 새로운 First Blood를 감지"""
        if not self.alert_channel:
            logger.warning("알림 채널이 설정되지 않았습니다")
            return
        
        try:
            # 모든 챌린지 가져오기
            challenges = self.ctfd_api.get_challenges()
            logger.debug(f"총 {len(challenges)}개의 챌린지 확인 중...")
            
            for challenge in challenges:
                challenge_id = challenge['id']
                
                # 이미 알림을 보낸 챌린지는 건너뛰기
                if challenge_id in self.notified_challenges:
                    continue
                
                # 챌린지의 solve 정보 가져오기
                solves = self._get_challenge_solves(challenge_id)
                
                # solve가 있는 경우 (First Blood가 있는 경우)
                if solves:
                    # 첫 번째 solve가 First Blood
                    first_solve = solves[0]
                    logger.info(f"First Blood 발견! Challenge ID: {challenge_id}")
                    
                    # 챌린지 상세 정보 가져오기
                    challenge_detail = self.ctfd_api.get_challenge_detail(challenge_id)
                    if not challenge_detail:
                        logger.error(f"챌린지 {challenge_id} 상세 정보를 가져올 수 없습니다")
                        continue
                    
                    # 사용자 정보 추출
                    solver_name = None
                    team_name = None
                    solve_time = None
                    
                    # CTFd가 직접 이름을 반환하는 경우 (현재 형식)
                    if 'name' in first_solve:
                        solver_name = first_solve['name']
                        solve_time = first_solve.get('date', first_solve.get('created'))
                        
                        # account_id로 추가 정보 조회 시도
                        if 'account_id' in first_solve:
                            # account가 user인지 team인지 확인
                            try:
                                user = self.ctfd_api.get_user(first_solve['account_id'])
                                if user and 'team_id' in user and user['team_id']:
                                    team = self.ctfd_api.get_team(user['team_id'])
                                    if team:
                                        team_name = team['name']
                            except:
                                # account_id가 team일 수도 있음
                                pass
                    
                    # submissions API를 사용하는 경우
                    elif self.use_submissions_api and 'user' in first_solve:
                        solver_name = first_solve.get('user', {}).get('name', 'Unknown')
                        team_name = first_solve.get('team', {}).get('name') if 'team' in first_solve else None
                        solve_time = first_solve.get('date', first_solve.get('created'))
                    
                    # 기존 API 형식 (user_id 사용)
                    else:
                        if 'user_id' in first_solve:
                            user = self.ctfd_api.get_user(first_solve['user_id'])
                            if user:
                                solver_name = user['name']
                                
                                # 팀전인 경우 팀 정보도 가져오기
                                if 'team_id' in user and user['team_id']:
                                    team = self.ctfd_api.get_team(user['team_id'])
                                    if team:
                                        team_name = team['name']
                        
                        elif 'team_id' in first_solve:
                            # 팀 모드인 경우
                            team = self.ctfd_api.get_team(first_solve['team_id'])
                            if team:
                                solver_name = team['name']
                        
                        solve_time = first_solve.get('date', first_solve.get('created'))
                    
                    if solver_name and solve_time:
                        # solve 시간 파싱
                        try:
                            if isinstance(solve_time, str):
                                # ISO 형식 파싱
                                solve_time = datetime.fromisoformat(
                                    solve_time.replace('Z', '+00:00').replace('T', ' ').split('.')[0]
                                )
                            else:
                                solve_time = datetime.fromtimestamp(solve_time)
                        except Exception as e:
                            logger.error(f"시간 파싱 오류: {e}")
                            solve_time = datetime.now()
                        
                        # Discord 임베드 생성
                        embed_dict = await self.create_first_blood_embed(
                            challenge_name=challenge_detail['name'],
                            solver_name=solver_name,
                            team_name=team_name,
                            category=challenge_detail.get('category', 'misc'),
                            points=challenge_detail.get('value', 0),
                            solve_time=solve_time
                        )
                        
                        # Discord Embed 객체 생성
                        import discord
                        embed = discord.Embed.from_dict(embed_dict)
                        
                        # 알림 전송
                        await self.alert_channel.send(embed=embed)
                        
                        # 상태 업데이트
                        self.notified_challenges.add(challenge_id)
                        self._save_state()
                        logger.info(f"First Blood 알림 전송 완료: {challenge_detail['name']} - {solver_name}")
                    else:
                        logger.warning(f"챌린지 {challenge_id}의 솔버 정보를 파싱할 수 없습니다")
                        
        except Exception as e:
            logger.error(f"First Blood 확인 중 오류 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def reset_notifications(self):
        """알림 상태 초기화 (새 대회 시작 시 사용)"""
        self.notified_challenges.clear()
        self._save_state()
        logger.info("First Blood 알림 상태가 초기화되었습니다")