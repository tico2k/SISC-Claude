import os
from pydantic_settings import BaseSettings
from typing import Optional

class EntraSettings(BaseSettings):
    """
    Microsoft Entra ID (Azure AD) 연동 설정
    """
    ENTRA_TENANT_ID: str = os.getenv("ENTRA_TENANT_ID", "")
    ENTRA_CLIENT_ID: str = os.getenv("ENTRA_CLIENT_ID", "")
    ENTRA_CLIENT_SECRET: str = os.getenv("ENTRA_CLIENT_SECRET", "")
    
    # Redirect URI (Frontend login callback or Backend callback depends on flow)
    # Typically OIDC via MSAL.js handles frontend, but we might need backend validation
    ENTRA_REDIRECT_URI: str = os.getenv("ENTRA_REDIRECT_URI", "http://localhost:5173/login/callback")
    
    # Graph API Scopes
    GRAPH_USER_SCOPES: list[str] = ["User.Read", "User.Read.All"]
    
    # Authority URL
    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.ENTRA_TENANT_ID}"

entra_settings = EntraSettings()
