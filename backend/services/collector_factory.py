from .base_collector import BaseCollector
from .sentinel_collector import SentinelCollector
from ..models import SiemType, SiemConfiguration
from ..core.security import decrypt_secret

class CollectorFactory:
    """
    SIEM 타입에 맞는 Collector를 생성하는 팩토리 클래스
    """
    
    @staticmethod
    def get_collector(config: SiemConfiguration) -> BaseCollector:
        if config.siem_type == SiemType.SENTINEL:
            # 복호화 처리 (데이터베이스에서 가져온 경우 암호화되어 있음)
            # DB에서 읽은 값은 암호문, 연결 테스트에서 넘어온 값은 이미 평문
            # 복호화 실패 시 암호문을 그대로 외부로 보내지 않도록 DecryptionError를 전달한다
            client_secret = config.client_secret
            if client_secret and client_secret.startswith("gAAAA"):
                client_secret = decrypt_secret(client_secret)

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
