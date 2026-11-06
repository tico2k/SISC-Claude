import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.sentinel_collector import SentinelCollector

# 자격 증명은 환경 변수에서 읽는다 (하드코딩 금지)
TENANT_ID = os.environ["SENTINEL_TENANT_ID"]
CLIENT_ID = os.environ["SENTINEL_CLIENT_ID"]
CLIENT_SECRET = os.environ["SENTINEL_CLIENT_SECRET"]
WORKSPACE_ID = os.environ["SENTINEL_WORKSPACE_ID"]

def main():
    print("Initializing SentinelCollector...")
    collector = SentinelCollector(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        workspace_id=WORKSPACE_ID
    )

    print("Fetching incidents (last 20 days)...")
    incidents = collector.fetch_incidents(days=20, limit=5)
    
    if incidents:
        print(f"Successfully fetched {len(incidents)} incidents:")
        for incident in incidents:
            print(f"- [{incident['Severity']}] {incident['Title']} (ID: {incident['IncidentID']})")
    else:
        print("No incidents found or error occurred.")

if __name__ == "__main__":
    main()
