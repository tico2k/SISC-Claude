from .base_collector import BaseCollector
from .sentinel_collector import SentinelCollector
from ..models import SiemType, SiemConfiguration
from ..core.security import decrypt_secret
import os

class CollectorFactory:
    """
    SIEM 타입에 맞는 Collector를 생성하는 팩토리 클래스
    """
    
    @staticmethod
    def get_collector(config: SiemConfiguration) -> BaseCollector:
        if config.siem_type == SiemType.SENTINEL:
            # 복호화 처리 (데이터베이스에서 가져온 경우 암호화되어 있음)
            client_secret = config.client_secret
            if client_secret and client_secret.startswith("gAAAA"):
                try:
                    client_secret = decrypt_secret(client_secret)
                except Exception as e:
                    # 복호화 실패 시 원본을 사용 (Test Connection 등에서 이미 복호화된 평문이 들어올 수 있음)
                    pass
                
            return SentinelCollector(
                tenant_id=config.tenant_id,
                client_id=config.client_id,
                client_secret=client_secret,
                workspace_id=config.workspace_name # Workspace ID used in query URL
            )
        elif config.siem_type == SiemType.ELK:
            # ELK 구현체 추가 예정 (현재는 Sentinel 예시로 대체하거나 에러 발생)
            raise NotImplementedError("ELK Collector is not implemented yet")
        elif config.siem_type == SiemType.SPLUNK:
            raise NotImplementedError("Splunk Collector is not implemented yet")
        else:
            raise ValueError(f"Unsupported SIEM type: {config.siem_type}")
