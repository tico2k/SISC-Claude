from backend.core.config import settings
from .base import MailProvider
from .smtp_provider import SMTPProvider
from .graph_provider import GraphMailProvider

class MailFactory:
    """메일 프로바이더 팩토리"""
    
    _instance: MailProvider = None
    
    @classmethod
    def get_provider(cls) -> MailProvider:
        """설정에 따른 프로바이더 싱글톤 반환"""
        if cls._instance is None:
            if settings.MAIL_SENDER_TYPE.upper() == "OUTLOOK":
                cls._instance = GraphMailProvider()
            else:
                cls._instance = SMTPProvider()
        return cls._instance
