import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CTFdAPI:
    """CTFd API와 상호작용하는 클래스"""
    
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json'
        })
        
        # 초기 연결 확인
        self._validate_connection()
    
    def _validate_connection(self):
        """API 연결 검증"""
        if self.api_token.startswith('http'):
            logger.error("API 토큰이 URL 형태입니다. 실제 API 토큰을 사용해주세요!")
            logger.error("CTFd Admin → Settings → Access Tokens에서 토큰을 생성하세요.")
            raise ValueError("Invalid API token format")
    
    def _make_request(self, endpoint: str, method: str = 'GET', **kwargs) -> Optional[Dict]:
        """API 요청을 수행하고 응답을 반환"""
        url = f"{self.base_url}/api/v1/{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # 상태 코드별 처리
            if response.status_code == 401:
                logger.error("CTFd API 인증 실패 (401 Unauthorized)")
                logger.error("가능한 원인:")
                logger.error("1. API 토큰이 올바르지 않음")
                logger.error("2. API 토큰이 만료됨")
                logger.error("3. API 토큰 권한 부족")
                logger.error(f"현재 토큰: {self.api_token[:20]}..." if len(self.api_token) > 20 else f"현재 토큰: {self.api_token}")
                return None
            
            elif response.status_code == 403:
                logger.error(f"CTFd API 접근 거부 (403 Forbidden): {endpoint}")
                return None
            
            elif response.status_code == 404:
                logger.error(f"CTFd API 엔드포인트를 찾을 수 없음 (404): {url}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            logger.error(f"CTFd 서버에 연결할 수 없습니다: {self.base_url}")
            logger.error("URL이 올바른지 확인하세요.")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"CTFd API 요청 시간 초과: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"CTFd API 요청 실패: {e}")
            return None
    
    def test_connection(self) -> bool:
        """API 연결 테스트"""
        data = self._make_request('users/me')
        if data and 'data' in data:
            user = data['data']
            logger.info(f"CTFd API 연결 성공! 사용자: {user.get('name', 'Unknown')}")
            return True
        return False
    
    def get_challenges(self) -> List[Dict]:
        """모든 챌린지 정보를 가져옴"""
        data = self._make_request('challenges')
        if data and 'data' in data:
            return data['data']
        return []
    
    def get_challenge_detail(self, challenge_id: int) -> Optional[Dict]:
        """특정 챌린지의 상세 정보를 가져옴"""
        data = self._make_request(f'challenges/{challenge_id}')
        if data and 'data' in data:
            return data['data']
        return None
    
    def get_challenge_solves(self, challenge_id: int) -> List[Dict]:
        """특정 챌린지의 모든 solve 정보를 가져옴"""
        data = self._make_request(f'challenges/{challenge_id}/solves')
        if data and 'data' in data:
            return data['data']
        return []
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """사용자 정보를 가져옴"""
        data = self._make_request(f'users/{user_id}')
        if data and 'data' in data:
            return data['data']
        return None
    
    def get_team(self, team_id: int) -> Optional[Dict]:
        """팀 정보를 가져옴"""
        data = self._make_request(f'teams/{team_id}')
        if data and 'data' in data:
            return data['data']
        return None