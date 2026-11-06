from abc import ABC, abstractmethod
from typing import List, Optional

class MailProvider(ABC):
    """이메일 발송 프로바이더 인터페이스"""
    
    @abstractmethod
    def send_mail(
        self,
        to_email: str,
        subject: str,
        content: str,
        is_html: bool = True,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """이메일 발송 실행"""
        pass
