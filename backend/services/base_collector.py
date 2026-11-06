from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class BaseCollector(ABC):
    """
    SIEM 데이터 수집을 위한 기본 추상 클래스
    """
    
    @abstractmethod
    def fetch_incidents(self, days: int = 1, limit: int = 10, last_sync_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        SIEM 시스템에서 인시던트를 수집합니다.
        """
        pass

    @abstractmethod
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        SIEM 시스템에서 원시 쿼리를 실행합니다.
        """
        pass
