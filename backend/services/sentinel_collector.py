import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from .base_collector import BaseCollector

# Configure logging
logger = logging.getLogger(__name__)

class SentinelCollector(BaseCollector):
    """
    Sentinel 인시던트 수집 모듈
    Azure Sentinel (Log Analytics) API를 통해 SecurityIncident 데이터를 수집합니다.
    """

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, workspace_id: str):
        """
        초기화
        :param tenant_id: Azure Tenant ID
        :param client_id: Azure Client ID (Application ID)
        :param client_secret: Azure Client Secret
        :param workspace_id: Log Analytics Workspace ID (UUID)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.workspace_id = workspace_id
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.query_url = f"https://api.loganalytics.azure.com/v1/workspaces/{self.workspace_id}/query"
        self._access_token = None

    def _get_access_token(self) -> Optional[str]:
        """
        OAuth2 Access Token을 발급받습니다.
        :return: Access Token (str) or None if failed
        """
        try:
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://api.loganalytics.io/.default"
            }
            
            response = requests.post(self.token_url, data=token_data)
            
            if response.status_code != 200:
                logger.error(f"Failed to acquire access token: {response.text}")
                return None
            
            token_json = response.json()
            if "access_token" not in token_json:
                logger.error("Response json does not contain access_token")
                return None
                
            return token_json["access_token"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during token request: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token acquisition: {str(e)}")
            return None

    def fetch_incidents(self, days: int = 1, limit: int = 10, last_sync_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Sentinel SecurityIncident 테이블에서 인시던트를 조회합니다.
        :param days: 조회할 기간 (일 단위, last_sync_time이 없을 경우 사용)
        :param limit: 최대 조회 건수
        :param last_sync_time: 마지막 동기화 시간 (이 시간 이후 데이터만 조회)
        :return: 인시던트 리스트 (List[Dict])
        """
        
        # 1. Access Token 획득
        token = self._get_access_token()
        if not token:
            logger.error("Cannot fetch incidents without access token")
            return []

        # 2. Time Filter 구성
        if last_sync_time:
            # ISO format string for KQL
            time_filter = f"datetime({last_sync_time.isoformat()})"
        else:
            time_filter = f"ago({days}d)"

        # 3. KQL 쿼리 작성 (IncidentID, Title, Severity, Status, TimeGenerated 추출)
        kql_query = f"""
        SecurityIncident
        | where TimeGenerated > {time_filter}
        | sort by TimeGenerated desc
        | take {limit}
        | project IncidentNumber, Title, Severity, Status, TimeGenerated, Description, IncidentUrl
        """

        query_body = {
            "query": kql_query
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.query_url, headers=headers, json=query_body)
            
            if response.status_code != 200:
                logger.error(f"Query execution failed: {response.text}")
                return []
            
            result = response.json()
            
            # 4. 결과 파싱 및 매핑
            if 'tables' not in result or not result['tables']:
                logger.warning("No tables in query result")
                return []
            
            table = result['tables'][0]
            columns = [col['name'] for col in table['columns']]
            rows = table['rows']
            
            incidents = []
            for row in rows:
                # Zip columns and row values into a dict
                raw_data = dict(zip(columns, row))
                
                # Map to requested structure
                incident = {
                    "IncidentID": raw_data.get("IncidentNumber"), # Using IncidentNumber as readable ID
                    "Title": raw_data.get("Title"),
                    "Severity": raw_data.get("Severity"),
                    "Status": raw_data.get("Status"),
                    "TimeGenerated": raw_data.get("TimeGenerated"),
                    "Description": raw_data.get("Description"),
                    "IncidentUrl": raw_data.get("IncidentUrl")
                }
                incidents.append(incident)
                
            logger.info(f"Successfully fetched {len(incidents)} incidents")
            return incidents

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during query execution: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during fetch_incidents: {str(e)}")
            return []

    def execute_query(self, kql_query: str) -> List[Dict[str, Any]]:
        """
        Executes a raw KQL query against the Sentinel workspace.
        :param kql_query: The KQL query string to execute.
        :return: A list of dictionaries representing the query results.
        """
        token = self._get_access_token()
        if not token:
            logger.error("Cannot execute query without access token")
            raise Exception("Failed to acquire access token")

        query_body = {
            "query": kql_query
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.query_url, headers=headers, json=query_body)
            
            if response.status_code != 200:
                logger.error(f"Query execution failed: {response.text}")
                error_msg = "Unknown error"
                try:
                    err_json = response.json()
                    if "error" in err_json:
                        err_obj = err_json["error"]
                        error_msg = err_obj.get("message", response.text)
                        
                        # Extract deeper innererror for more specific cause (e.g. SEM0100)
                        current_inner = err_obj.get("innererror")
                        while current_inner:
                            if current_inner.get("message"):
                                error_msg = current_inner["message"]
                            current_inner = current_inner.get("innererror")
                except Exception:
                    error_msg = response.text
                
                raise Exception(f"Query failed: {error_msg}")
            
            result = response.json()
            
            if 'tables' not in result or not result['tables']:
                return []
            
            table = result['tables'][0]
            columns = [col['name'] for col in table['columns']]
            rows = table['rows']
            
            data = []
            for row in rows:
                data.append(dict(zip(columns, row)))
                
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during query execution: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during execute_query: {str(e)}")
            raise
