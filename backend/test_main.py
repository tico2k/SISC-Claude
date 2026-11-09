from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.core.database import Base, get_db
from backend.core.dependencies import get_password_hash
from backend import models
from backend.core.limiter import limiter
from backend.modules.submissions import router as submissions_router
import pytest

# 테스트 전체에서 /login 요청 제한(5/minute)에 걸리지 않도록 비활성화
limiter.enabled = False

# Test DB Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests(monkeypatch):
    # 테스트 중 실제 메일 발송 및 운영 DB(SessionLocal) 접근 차단
    from backend.core.config import settings
    from backend.tasks import email_tasks
    from backend.core import database as core_db
    monkeypatch.setattr(settings, "ENABLE_EMAIL_NOTIFICATIONS", False)
    monkeypatch.setattr(email_tasks, "SessionLocal", TestingSessionLocal)
    # 메일 템플릿 조회·Teams 설정 조회 등 core_db.SessionLocal을 쓰는 코드도 테스트 DB로
    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)

    Base.metadata.create_all(bind=engine)
    # 초기 시스템 관리자 계정 생성 (테스트용)
    db = TestingSessionLocal()
    sysadmin = models.User(
        user_email="sysadmin@example.com",
        user_name="System Admin",
        hashed_password=get_password_hash("sysadmin123!"),
        role=models.UserRole.SYSTEM_ADMIN,
        company="Fleit",
        department="IT"
    )
    db.add(sysadmin)
    db.commit()
    db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)

def get_sysadmin_token():
    login_res = client.post(
        "/login",
        data={"username": "sysadmin@example.com", "password": "sysadmin123!"},
    )
    return login_res.json()["access_token"]

def test_register_user():
    admin_token = get_sysadmin_token()
    response = client.post(
        "/register",
        json={
            "user_email": "test@example.com",
            "password": "password123",
            "user_name": "Test User",
            "role": "일반"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_email"] == "test@example.com"
    assert "user_id" in data

def test_login_user():
    admin_token = get_sysadmin_token()
    # Register first via sysadmin
    client.post(
        "/register",
        json={
            "user_email": "test@example.com",
            "password": "password123",
            "user_name": "Test User",
            "role": "일반"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Login
    response = client.post(
        "/login",
        data={"username": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_create_case_permission():
    admin_token = get_sysadmin_token()
    # Regular user registration
    client.post(
        "/register",
        json={
            "user_email": "user@example.com",
            "password": "password123",
            "user_name": "Regular User",
            "role": "일반"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    login_res = client.post(
        "/login",
        data={"username": "user@example.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]
    
    response = client.post(
        "/cases",
        json={
            "siem_type": "Sentinel",
            "rule_title": "Test Rule",
            "case_type": "정보유출",
            "due_date": "2024-12-31T23:59:59",
            "related_employee_id": 1
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_create_case_admin():
    admin_token = get_sysadmin_token()
    # Create related user first
    reg_rel = client.post(
        "/register",
        json={
            "user_email": "related@example.com",
            "password": "password123",
            "user_name": "Related User",
            "role": "일반"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    related_user_id = reg_rel.json()["user_id"]

    # Create security admin
    client.post(
        "/register",
        json={
            "user_email": "admin@example.com",
            "password": "password123",
            "user_name": "Admin User",
            "role": "보안관리자"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    login_res = client.post(
        "/login",
        data={"username": "admin@example.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]
    
    response = client.post(
        "/cases",
        json={
            "siem_type": "Sentinel",
            "rule_title": "Test Rule",
            "case_type": "정보유출",
            "due_date": "2024-12-31T23:59:59",
            "related_employee_id": related_user_id
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rule_title"] == "Test Rule"


def _create_case_with_attachment(file_path: str) -> int:
    """일반 사용자 소유 케이스와 지정 경로의 첨부파일을 DB에 직접 생성하고 file_id 반환"""
    db = TestingSessionLocal()
    try:
        owner = models.User(
            user_email="owner@example.com",
            user_name="Owner",
            hashed_password=get_password_hash("password123"),
            role=models.UserRole.USER,
        )
        db.add(owner)
        db.flush()
        case = models.ClarificationCase(
            rule_title="Attachment Test",
            case_type=models.CaseType.INFO_LEAK,
            related_employee_id=owner.user_id,
            due_date=datetime(2099, 12, 31),
            case_status=models.CaseStatus.REQUEST,
        )
        db.add(case)
        db.flush()
        attachment = models.ClarificationAttachment(
            case_id=case.case_id,
            original_filename="evidence.txt",
            stored_filename="evidence.txt",
            file_path=file_path,
            file_size=4,
        )
        db.add(attachment)
        db.commit()
        return attachment.file_id
    finally:
        db.close()


def test_download_attachment_inside_upload_dir(tmp_path, monkeypatch):
    upload_dir = (tmp_path / "uploads").resolve()
    (upload_dir / "1").mkdir(parents=True)
    target = upload_dir / "1" / "evidence.txt"
    target.write_text("data")
    monkeypatch.setattr(submissions_router, "UPLOAD_DIR", upload_dir)

    file_id = _create_case_with_attachment(str(target))
    response = client.get(
        f"/attachments/{file_id}",
        headers={"Authorization": f"Bearer {get_sysadmin_token()}"},
    )
    assert response.status_code == 200
    assert response.content == b"data"


def test_download_attachment_blocks_sibling_prefix_dir(tmp_path, monkeypatch):
    """uploads_evil/ 처럼 UPLOAD_DIR과 접두사만 같은 형제 폴더의 파일은 차단되어야 한다"""
    upload_dir = (tmp_path / "uploads").resolve()
    upload_dir.mkdir()
    evil_dir = tmp_path / "uploads_evil"
    evil_dir.mkdir()
    target = evil_dir / "secret.txt"
    target.write_text("secret")
    monkeypatch.setattr(submissions_router, "UPLOAD_DIR", upload_dir)

    file_id = _create_case_with_attachment(str(target))
    response = client.get(
        f"/attachments/{file_id}",
        headers={"Authorization": f"Bearer {get_sysadmin_token()}"},
    )
    assert response.status_code == 403
    assert b"secret" not in response.content


# --- Phase 1 보안 회귀 테스트 ---

def test_new_skill_template_router_not_exposed():
    """스킬 생성용 템플릿 라우터는 운영 앱에 등록되지 않아야 한다"""
    response = client.post(
        "/new-skill/",
        json={"name": "x"},
        headers={"Authorization": f"Bearer {get_sysadmin_token()}"},
    )
    assert response.status_code in (404, 405)


def test_decrypt_secret_raises_on_invalid_token():
    from backend.core.security import decrypt_secret, DecryptionError
    with pytest.raises(DecryptionError):
        decrypt_secret("gAAAAA-invalid-token")


def _write_fake_env(tmp_path, monkeypatch):
    from backend.modules.system import router as system_router
    # 실제 .env를 건드리지 않도록 임시 파일로 교체
    monkeypatch.setattr(system_router, "BACKEND_ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(system_router, "FRONTEND_ENV_PATH", tmp_path / "frontend.env")
    (tmp_path / ".env").write_text(
        "ENCRYPTION_KEY=abcdefghijklmnop\n"
        "SECRET_KEY=supersecretvalue\n"
        "DATABASE_URL=postgresql://u:pw@host/db\n"
        "LOG_LEVEL=INFO\n",
        encoding="utf-8",
    )


def test_env_sensitive_values_fully_masked(tmp_path, monkeypatch):
    _write_fake_env(tmp_path, monkeypatch)
    response = client.get("/system/env", headers={"Authorization": f"Bearer {get_sysadmin_token()}"})
    assert response.status_code == 200
    entries = {e["key"]: e for e in response.json()["backend"]}
    for key in ("ENCRYPTION_KEY", "SECRET_KEY", "DATABASE_URL"):
        assert entries[key]["is_sensitive"] is True
        assert entries[key]["value"] == "********"
    assert entries["LOG_LEVEL"]["value"] == "INFO"


def test_env_update_rejects_invalid_and_unknown_keys(tmp_path, monkeypatch):
    _write_fake_env(tmp_path, monkeypatch)
    headers = {"Authorization": f"Bearer {get_sysadmin_token()}"}
    before = (tmp_path / ".env").read_text(encoding="utf-8")

    for key in ("#EVIL", "BAD-KEY", "NEW_UNKNOWN_KEY"):
        response = client.post("/system/env", json={"file_type": "backend", "key": key, "value": "1"}, headers=headers)
        assert response.status_code == 422, key
    assert (tmp_path / ".env").read_text(encoding="utf-8") == before

    response = client.post("/system/env", json={"file_type": "backend", "key": "LOG_LEVEL", "value": "DEBUG"}, headers=headers)
    assert response.status_code == 200
    assert "LOG_LEVEL=DEBUG" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_app_version_matches_settings():
    from backend.core.config import settings
    assert client.get("/openapi.json").json()["info"]["version"] == settings.APP_VERSION == "2.1.0"


# --- Phase 2: 케이스 워크플로우(상태 전이·격리·Lock·감사로그) 테스트 ---

@pytest.fixture
def wf(monkeypatch):
    """일반 사용자 2명(owner, other)과 보안관리자 2명(admin, admin2) 생성 후 토큰 반환"""
    from backend.core.config import settings
    monkeypatch.setattr(settings, "ENABLE_EMAIL_NOTIFICATIONS", False)

    db = TestingSessionLocal()
    users = {}
    for key, role in (("owner", models.UserRole.USER), ("other", models.UserRole.USER),
                      ("admin", models.UserRole.SECURITY_ADMIN), ("admin2", models.UserRole.SECURITY_ADMIN)):
        u = models.User(
            user_email=f"{key}@wf.com", user_name=key,
            hashed_password=get_password_hash("password123"), role=role,
        )
        db.add(u)
        db.flush()
        users[key] = u.user_id
    db.commit()
    db.close()

    def headers(key):
        res = client.post("/login", data={"username": f"{key}@wf.com", "password": "password123"})
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    return {"ids": users, "h": {k: headers(k) for k in users}}


def _make_case(owner_id, status, result=None, locked_by=None, locked_at=None) -> int:
    db = TestingSessionLocal()
    try:
        case = models.ClarificationCase(
            rule_title="WF Rule", case_type=models.CaseType.INFO_LEAK,
            related_employee_id=owner_id, due_date=datetime(2099, 12, 31),
            case_status=status, case_result=result,
            locked_by_id=locked_by, locked_at=locked_at,
        )
        db.add(case)
        db.commit()
        return case.case_id
    finally:
        db.close()


def _case_status(case_id):
    db = TestingSessionLocal()
    try:
        return db.get(models.ClarificationCase, case_id).case_status
    finally:
        db.close()


def _submit(case_id, headers):
    return client.post("/submissions", data={"case_id": case_id, "content": "사유", "classification": "업무"}, headers=headers)


def _review(case_id, status, result, headers):
    return client.post("/reviews", json={"case_id": case_id, "case_status": status, "case_result": result, "comments": "c"}, headers=headers)


def test_workflow_happy_path_and_audit_log(wf):
    """미확인 → 요청 → 제출 → 승인 → 종결 정상 흐름과 각 단계 감사로그 기록"""
    h, owner = wf["h"], wf["ids"]["owner"]
    cid = _make_case(owner, models.CaseStatus.UNCLASSIFIED)

    res = client.post(f"/cases/{cid}/request", data={"due_date": "2099-12-31", "request_reason": "확인 요청"}, headers=h["admin"])
    assert res.status_code == 201, res.text
    assert _submit(cid, h["owner"]).status_code == 201
    assert _review(cid, "승인", "정당 사유", h["admin"]).status_code == 201
    res = client.post(f"/cases/{cid}/close", json={"case_result": "정당 사유", "close_reason": "완료"}, headers=h["admin"])
    assert res.status_code == 200, res.text
    assert _case_status(cid) == models.CaseStatus.CLOSE

    db = TestingSessionLocal()
    actions = [a.action for a in db.query(models.SystemAuditLog).all()]
    db.close()
    for prefix in ("CASE_REQUESTED", "CASE_SUBMITTED", "CASE_REVIEWED", "CASE_CLOSED"):
        assert any(a.startswith(f"{prefix}: Case {cid}") for a in actions), prefix


@pytest.mark.parametrize("status", [models.CaseStatus.UNCLASSIFIED, models.CaseStatus.CLOSE])
def test_owner_cannot_submit_to_hidden_case(wf, status):
    """미확인·종결 케이스에는 본인도 제출할 수 없고 상태가 바뀌지 않아야 한다"""
    cid = _make_case(wf["ids"]["owner"], status)
    assert _submit(cid, wf["h"]["owner"]).status_code == 403
    assert _case_status(cid) == status


@pytest.mark.parametrize("status,result", [
    (models.CaseStatus.SUBMIT, None),
    (models.CaseStatus.APPROVE, models.CaseResult.JUSTIFIED),
    (models.CaseStatus.REJECT, models.CaseResult.EDUCATION_NEEDED),
    (models.CaseStatus.REJECT, models.CaseResult.DISCIPLINARY_ACTION),
])
def test_submit_rejected_in_invalid_state(wf, status, result):
    cid = _make_case(wf["ids"]["owner"], status, result)
    assert _submit(cid, wf["h"]["owner"]).status_code == 409
    assert _case_status(cid) == status


def test_resubmit_allowed_after_reject_type_a(wf):
    """반려 A(소명 불충분)는 재소명 가능"""
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.REJECT, models.CaseResult.INSUFFICIENT)
    assert _submit(cid, wf["h"]["owner"]).status_code == 201
    assert _case_status(cid) == models.CaseStatus.SUBMIT


def test_other_user_cannot_submit_or_view(wf):
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.REQUEST)
    assert _submit(cid, wf["h"]["other"]).status_code == 403
    assert client.get(f"/cases/{cid}", headers=wf["h"]["other"]).status_code == 403


def test_user_case_list_hides_unclassified_and_closed(wf):
    owner = wf["ids"]["owner"]
    visible = _make_case(owner, models.CaseStatus.REQUEST)
    _make_case(owner, models.CaseStatus.UNCLASSIFIED)
    _make_case(owner, models.CaseStatus.CLOSE)
    _make_case(wf["ids"]["other"], models.CaseStatus.REQUEST)
    items = client.get("/cases", headers=wf["h"]["owner"]).json()["items"]
    assert [c["case_id"] for c in items] == [visible]


@pytest.mark.parametrize("status", [models.CaseStatus.UNCLASSIFIED, models.CaseStatus.REQUEST,
                                    models.CaseStatus.APPROVE, models.CaseStatus.CLOSE])
def test_review_only_from_submit(wf, status):
    cid = _make_case(wf["ids"]["owner"], status)
    assert _review(cid, "승인", "정당 사유", wf["h"]["admin"]).status_code == 409
    assert _case_status(cid) == status


@pytest.mark.parametrize("status,result", [
    ("승인", "징계 요청"),      # 승인에 반려 사유
    ("반려", "정당 사유"),      # 반려에 승인 사유
    ("종결", "오탐"),           # 심의로 종결 불가(종결 API 사용)
    ("요청", "정당 사유"),
])
def test_review_rejects_invalid_status_result(wf, status, result):
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.SUBMIT)
    assert _review(cid, status, result, wf["h"]["admin"]).status_code == 422
    assert _case_status(cid) == models.CaseStatus.SUBMIT


def test_user_cannot_review(wf):
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.SUBMIT)
    assert _review(cid, "승인", "정당 사유", wf["h"]["owner"]).status_code == 403


def test_review_blocked_when_locked_by_other_admin(wf):
    ids, h = wf["ids"], wf["h"]
    cid = _make_case(ids["owner"], models.CaseStatus.SUBMIT, locked_by=ids["admin2"], locked_at=datetime.now())
    assert _review(cid, "승인", "정당 사유", h["admin"]).status_code == 409
    assert _case_status(cid) == models.CaseStatus.SUBMIT
    # 잠근 본인은 심의 가능
    assert _review(cid, "반려", "소명 불충분", h["admin2"]).status_code == 201
    assert _case_status(cid) == models.CaseStatus.REJECT


def test_review_allowed_when_other_lock_expired(wf):
    from datetime import timedelta
    ids = wf["ids"]
    cid = _make_case(ids["owner"], models.CaseStatus.SUBMIT, locked_by=ids["admin2"],
                     locked_at=datetime.now() - timedelta(minutes=31))
    assert _review(cid, "승인", "정당 사유", wf["h"]["admin"]).status_code == 201


def test_request_only_from_unclassified(wf):
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.SUBMIT)
    res = client.post(f"/cases/{cid}/request", data={"due_date": "2099-12-31", "request_reason": "r"}, headers=wf["h"]["admin"])
    assert res.status_code == 409
    assert _case_status(cid) == models.CaseStatus.SUBMIT


def test_close_twice_rejected(wf):
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.CLOSE, models.CaseResult.FALSE_POSITIVE)
    res = client.post(f"/cases/{cid}/close", json={"case_result": "정당 사유", "close_reason": "x"}, headers=wf["h"]["admin"])
    assert res.status_code == 409


def test_owner_cannot_download_attachment_of_closed_case(tmp_path, monkeypatch):
    upload_dir = (tmp_path / "uploads").resolve()
    (upload_dir / "1").mkdir(parents=True)
    target = upload_dir / "1" / "evidence.txt"
    target.write_text("data")
    monkeypatch.setattr(submissions_router, "UPLOAD_DIR", upload_dir)

    file_id = _create_case_with_attachment(str(target))
    owner_headers = {"Authorization": "Bearer " + client.post(
        "/login", data={"username": "owner@example.com", "password": "password123"}).json()["access_token"]}
    assert client.get(f"/attachments/{file_id}", headers=owner_headers).status_code == 200

    db = TestingSessionLocal()
    db.query(models.ClarificationCase).update({"case_status": models.CaseStatus.CLOSE})
    db.commit()
    db.close()
    assert client.get(f"/attachments/{file_id}", headers=owner_headers).status_code == 403


def test_case_create_and_close_trigger_email_tasks(wf, monkeypatch):
    """케이스 생성·종결 시 메일 작업이 실제로 호출되어야 한다 (잘못된 import 경로 회귀 방지)"""
    from backend.tasks import email_tasks
    calls = []
    monkeypatch.setattr(email_tasks, "send_case_created_email", lambda cid: calls.append(("created", cid)))
    monkeypatch.setattr(email_tasks, "send_case_reviewed_email", lambda cid: calls.append(("reviewed", cid)))

    res = client.post("/cases", json={
        "siem_type": "Sentinel", "rule_title": "Mail Rule", "case_type": "정보유출",
        "due_date": "2099-12-31T23:59:59", "related_employee_id": wf["ids"]["owner"],
    }, headers=wf["h"]["admin"])
    assert res.status_code == 201
    cid = res.json()["case_id"]
    res = client.post(f"/cases/{cid}/close", json={"case_result": "오탐", "close_reason": "x"}, headers=wf["h"]["admin"])
    assert res.status_code == 200
    assert calls == [("created", cid), ("reviewed", cid)]


def test_email_link_uses_app_url_setting(wf, monkeypatch):
    from backend.core.config import settings
    from backend.tasks import email_tasks
    monkeypatch.setattr(settings, "APP_URL", "https://sics.example.com")
    sent = {}
    monkeypatch.setattr(email_tasks, "send_template_mail", lambda **kw: sent.update(kw) or True)

    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.UNCLASSIFIED)
    email_tasks.send_case_created_email(cid)
    assert sent["app_url"] == "https://sics.example.com"


def test_frontend_url_falls_back_to_first_cors_origin(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "APP_URL", None)
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://a.example.com/, https://b.example.com")
    assert settings.frontend_url == "https://a.example.com"
    monkeypatch.setattr(settings, "APP_URL", "https://sics.example.com/")
    assert settings.frontend_url == "https://sics.example.com"


# --- 메일 통합: 모든 메일은 core.mail 프로바이더 하나로 발송 ---

class _FakeProvider:
    def __init__(self):
        self.sent = []

    def send_mail(self, to_email, subject, content, is_html=True, attachments=None):
        self.sent.append({"to": to_email, "subject": subject, "content": content})
        return True


@pytest.fixture
def fake_provider(monkeypatch):
    from backend.core.mail.factory import MailFactory
    provider = _FakeProvider()
    monkeypatch.setattr(MailFactory, "_instance", provider)
    return provider


def test_request_notification_escapes_html_and_keeps_line_breaks(fake_provider):
    from backend.core.mail import services as mail_services
    ok = mail_services.send_request_notification(
        to_email="u@example.com", user_name="홍길동", priority="높음", incident_num="77",
        rule_title="<script>alert(1)</script>", due_date=datetime(2099, 1, 2),
        request_reason="첫 줄\n<b>둘째</b>", case_id=5,
    )
    assert ok is True
    html = fake_provider.sent[0]["content"]
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "첫 줄<br>&lt;b&gt;둘째&lt;/b&gt;" in html
    assert "/cases/5" in html and "badge-urgent" in html
    assert fake_provider.sent[0]["subject"] == "[높음] 보안 소명 요청 안내 - #77"


def test_case_task_emails_go_through_provider(wf, fake_provider):
    """생성·검토·마감 알림 메일도 설정된 프로바이더(SMTP/Outlook)로 발송되어야 한다"""
    from backend.tasks import email_tasks
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.APPROVE, models.CaseResult.JUSTIFIED)
    email_tasks.send_case_created_email(cid)
    email_tasks.send_case_reviewed_email(cid)
    email_tasks.send_deadline_reminder_email(cid, 3)

    assert [m["to"] for m in fake_provider.sent] == ["owner@wf.com"] * 3
    subjects = [m["subject"] for m in fake_provider.sent]
    assert "승인 완료" in subjects[1]          # 상태 비교 버그 회귀 방지 (예전엔 항상 '종결')
    assert "마감 3일 전" in subjects[2]
    assert all(f"/cases/{cid}" in m["content"] for m in fake_provider.sent)


def test_mail_factory_selects_provider_by_setting(monkeypatch):
    from backend.core.config import settings
    from backend.core.mail.factory import MailFactory
    from backend.core.mail.graph_provider import GraphMailProvider
    from backend.core.mail.smtp_provider import SMTPProvider
    for sender_type, cls in (("OUTLOOK", GraphMailProvider), ("SMTP", SMTPProvider)):
        monkeypatch.setattr(MailFactory, "_instance", None)
        monkeypatch.setattr(settings, "MAIL_SENDER_TYPE", sender_type)
        assert isinstance(MailFactory.get_provider(), cls)


# --- 선택 연동(Entra ID / SIEM): 설치 직후에는 꺼져 있고 관리자가 설정한 뒤에만 동작 ---

TEST_TENANT = "11111111-2222-3333-4444-555555555555"
TEST_CLIENT = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _sysadmin_headers():
    return {"Authorization": f"Bearer {get_sysadmin_token()}"}


def _enable_entra(secret=None):
    body = {"is_enabled": True, "tenant_id": TEST_TENANT, "client_id": TEST_CLIENT}
    if secret is not None:
        body["client_secret"] = secret
    res = client.put("/integrations/entra", json=body, headers=_sysadmin_headers())
    assert res.status_code == 200, res.text
    return res


@pytest.fixture
def entra_keys(monkeypatch):
    """테스트용 RSA 키로 ID 토큰을 서명하고, JWKS 조회를 해당 공개키로 대체"""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from jose import jwk, jwt
    from backend.modules.integrations import services as integ

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    public_jwk = jwk.construct(public_pem, "RS256").to_dict()
    public_jwk.update({"kid": "test-kid", "use": "sig"})
    monkeypatch.setattr(integ, "_get_jwks", lambda tenant_id, force_refresh=False: {"keys": [public_jwk]})

    def make_token(**overrides):
        import time
        claims = {
            "aud": TEST_CLIENT, "tid": TEST_TENANT,
            "iss": f"https://login.microsoftonline.com/{TEST_TENANT}/v2.0",
            "preferred_username": "SysAdmin@Example.com",
            "iat": int(time.time()), "exp": int(time.time()) + 600,
        }
        claims.update(overrides)
        return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "test-kid"})

    return make_token


def test_auth_config_entra_disabled_by_default():
    res = client.get("/config")
    assert res.status_code == 200
    data = res.json()
    assert data["allow_entra"] is False
    assert data["default_method"] == "LOCAL"
    assert data["entra_client_id"] is None and data["entra_tenant_id"] is None


def test_entra_login_rejected_when_not_configured(entra_keys):
    res = client.post("/login/entra", json={"id_token": entra_keys()})
    assert res.status_code == 401


def test_integration_settings_require_system_admin(wf):
    assert client.get("/integrations/entra", headers=wf["h"]["admin"]).status_code == 403
    assert client.put("/integrations/entra", json={"is_enabled": False}, headers=wf["h"]["owner"]).status_code == 403


def test_integration_save_masks_secret_and_enables_sso():
    res = _enable_entra(secret="super-secret-value")
    data = res.json()
    assert data["client_secret_set"] is True
    assert "super-secret-value" not in res.text

    # 저장된 시크릿은 암호화되어 있고, 감사로그에는 값이 남지 않는다
    db = TestingSessionLocal()
    try:
        row = db.get(models.IntegrationSetting, "ENTRA")
        assert row.client_secret and row.client_secret != "super-secret-value"
        actions = [a.action for a in db.query(models.SystemAuditLog).all()]
        assert any(a.startswith("INTEGRATION_ENTRA_UPDATED") for a in actions)
        assert not any("super-secret-value" in a or TEST_TENANT in a for a in actions)
        encrypted = row.client_secret
    finally:
        db.close()

    # 마스크 값으로 다시 저장하면 기존 시크릿 유지
    _enable_entra(secret="********")
    db = TestingSessionLocal()
    try:
        assert db.get(models.IntegrationSetting, "ENTRA").client_secret == encrypted
    finally:
        db.close()

    config = client.get("/config").json()
    assert config["allow_entra"] is True
    assert config["entra_client_id"] == TEST_CLIENT and config["entra_tenant_id"] == TEST_TENANT


@pytest.mark.parametrize("body", [
    {"is_enabled": True, "tenant_id": "", "client_id": TEST_CLIENT},                  # 활성화인데 테넌트 없음
    {"is_enabled": False, "tenant_id": "evil.com/x?", "client_id": TEST_CLIENT},       # GUID 아님 (URL 주입 방지)
    {"is_enabled": False, "tenant_id": TEST_TENANT, "client_id": "not-a-guid"},
    {"is_enabled": False, "mail_sender": "not-an-email"},
])
def test_integration_save_validates_input(body):
    res = client.put("/integrations/entra", json=body, headers=_sysadmin_headers())
    assert res.status_code == 422


def test_entra_login_with_valid_id_token(entra_keys):
    _enable_entra()
    res = client.post("/login/entra", json={"id_token": entra_keys()})
    assert res.status_code == 200, res.text
    assert res.json()["token_type"] == "bearer"
    db = TestingSessionLocal()
    try:
        assert db.query(models.SystemAuditLog).filter_by(action="LOGIN_ENTRA_SUCCESS").count() == 1
    finally:
        db.close()


@pytest.mark.parametrize("overrides", [
    {"aud": "99999999-9999-9999-9999-999999999999"},                       # 다른 앱용 토큰
    {"tid": "99999999-9999-9999-9999-999999999999"},                       # 다른 테넌트
    {"iss": "https://login.microsoftonline.com/other/v2.0"},
    {"exp": 1},                                                            # 만료
    {"preferred_username": "nobody@example.com"},                          # 미등록 사용자
])
def test_entra_login_rejects_invalid_tokens(entra_keys, overrides):
    _enable_entra()
    res = client.post("/login/entra", json={"id_token": entra_keys(**overrides)})
    assert res.status_code == 401


def test_entra_login_rejects_token_signed_by_other_key(entra_keys):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from jose import jwt
    _enable_entra()
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    good_claims = jwt.get_unverified_claims(entra_keys())
    forged = jwt.encode(good_claims, other, algorithm="RS256", headers={"kid": "test-kid"})
    assert client.post("/login/entra", json={"id_token": forged}).status_code == 401


def test_entra_user_sync_requires_configuration():
    res = client.post("/users/sync-entra", headers=_sysadmin_headers())
    assert res.status_code == 422


def test_graph_mail_not_sent_without_entra(monkeypatch):
    from backend.core import database as core_db
    from backend.core.config import settings
    from backend.core.mail.graph_provider import GraphMailProvider
    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(settings, "ENABLE_EMAIL_NOTIFICATIONS", True)
    assert GraphMailProvider().send_mail("a@example.com", "s", "c") is False


def test_password_change_wrong_old_password_returns_client_error():
    res = client.post("/pwchange", json={"old_password": "wrong", "new_password": "x"}, headers=_sysadmin_headers())
    assert res.status_code == 422


def test_menu_seeding_adds_missing_paths_and_keeps_existing(monkeypatch):
    import asyncio
    from backend.core import database as core_db
    from backend.main import create_initial_menu_permissions
    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    db.add(models.MenuPermission(role=models.UserRole.USER, menu_path="/dashboard", is_visible=False))
    db.commit()
    db.close()

    asyncio.run(create_initial_menu_permissions())

    db = TestingSessionLocal()
    try:
        perms = {(p.role, p.menu_path): p.is_visible for p in db.query(models.MenuPermission).all()}
        assert perms[(models.UserRole.USER, "/dashboard")] is False       # 기존 설정 유지
        assert perms[(models.UserRole.SYSTEM_ADMIN, "/integrations")] is True
        assert perms[(models.UserRole.SECURITY_ADMIN, "/integrations")] is False
    finally:
        db.close()


def test_siem_sync_fails_without_field_mapping(monkeypatch):
    from backend.tasks import siem_tasks
    monkeypatch.setattr(siem_tasks, "SessionLocal", TestingSessionLocal)
    db = TestingSessionLocal()
    cfg = models.SiemConfiguration(siem_type=models.SiemType.SENTINEL, name="t", host_url="", field_mapping=None, is_active=True)
    db.add(cfg)
    db.commit()
    siem_id = cfg.siem_id
    db.close()

    result = siem_tasks.sync_siem_logs(siem_id, is_manual=True)
    assert result["status"] == "error" and "필드 매핑" in result["message"]


# --- 1차: 기한 초과 · 증거 무결성 · 보존/파기 ---

def _set_manager(employee_key, manager_key, wf):
    db = TestingSessionLocal()
    emp = db.get(models.User, wf["ids"][employee_key])
    emp.manager_id = wf["ids"][manager_key]
    db.commit()
    db.close()


def _make_overdue_case(owner_id) -> int:
    cid = _make_case(owner_id, models.CaseStatus.REQUEST)
    db = TestingSessionLocal()
    db.get(models.ClarificationCase, cid).due_date = datetime(2020, 1, 1)
    db.commit()
    db.close()
    return cid


def test_overdue_flag_filter_and_stats(wf):
    overdue_id = _make_overdue_case(wf["ids"]["owner"])
    _make_case(wf["ids"]["owner"], models.CaseStatus.REQUEST)  # 기한 2099년
    assert client.get(f"/cases/{overdue_id}", headers=wf["h"]["owner"]).json()["is_overdue"] is True

    res = client.get("/cases", params={"overdue": True}, headers=wf["h"]["admin"]).json()
    assert [c["case_id"] for c in res["items"]] == [overdue_id]
    assert client.get("/cases/stats", headers=wf["h"]["admin"]).json()["overdue"] == 1


def test_overdue_job_notifies_employee_manager_admins_once(wf, fake_provider, monkeypatch):
    from backend.tasks import batch_tasks
    from backend.modules.integrations import services as integ
    monkeypatch.setattr(batch_tasks, "SessionLocal", TestingSessionLocal)
    teams = []
    monkeypatch.setattr(integ, "send_teams_message", lambda **kw: teams.append(kw) or True)
    _set_manager("owner", "other", wf)
    cid = _make_overdue_case(wf["ids"]["owner"])

    assert batch_tasks.notify_overdue_cases()["overdue_notified"] == 1
    recipients = sorted(m["to"] for m in fake_provider.sent)
    assert recipients == ["admin2@wf.com", "admin@wf.com", "other@wf.com", "owner@wf.com"]
    assert any("기한 초과" in m["subject"] and f"#{cid}" in m["subject"] for m in fake_provider.sent)
    assert len(teams) == 1

    # 같은 케이스는 다시 알리지 않음, 상태는 그대로 '요청'
    fake_provider.sent.clear()
    assert batch_tasks.notify_overdue_cases()["overdue_notified"] == 0
    assert fake_provider.sent == []
    assert _case_status(cid) == models.CaseStatus.REQUEST


def _submit_with_file(case_id, headers, content=b"evidence-bytes"):
    return client.post(
        "/submissions",
        data={"case_id": case_id, "content": "사유", "classification": "업무"},
        files=[("files", ("proof.txt", content, "text/plain"))],
        headers=headers,
    )


def _audit_actions():
    db = TestingSessionLocal()
    try:
        return [a.action for a in db.query(models.SystemAuditLog).all()]
    finally:
        db.close()


def test_attachment_hash_verified_and_tamper_detected(wf, tmp_path, monkeypatch):
    import hashlib
    upload_dir = (tmp_path / "uploads").resolve()
    monkeypatch.setattr(submissions_router, "UPLOAD_DIR", upload_dir)
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.REQUEST)
    assert _submit_with_file(cid, wf["h"]["owner"]).status_code == 201

    att = client.get(f"/cases/{cid}", headers=wf["h"]["admin"]).json()["submissions"][0]["attachments"][0]
    assert att["sha256"] == hashlib.sha256(b"evidence-bytes").hexdigest()

    res = client.get(f"/attachments/{att['file_id']}", headers=wf["h"]["admin"])
    assert res.status_code == 200 and res.headers["X-Integrity"] == "verified"
    assert any(a.startswith(f"ATTACHMENT_DOWNLOADED: Case {cid}") for a in _audit_actions())

    # 저장된 파일을 바꾸면 다운로드 거부 + 감사로그
    stored = next(upload_dir.rglob("*.txt"))
    stored.write_bytes(b"tampered")
    res = client.get(f"/attachments/{att['file_id']}", headers=wf["h"]["admin"])
    assert res.status_code == 409 and b"tampered" not in res.content
    assert any(a.startswith("ATTACHMENT_INTEGRITY_FAILED") for a in _audit_actions())


def test_legacy_attachment_without_hash_is_unverified(tmp_path, monkeypatch):
    upload_dir = (tmp_path / "uploads").resolve()
    (upload_dir / "1").mkdir(parents=True)
    target = upload_dir / "1" / "evidence.txt"
    target.write_text("data")
    monkeypatch.setattr(submissions_router, "UPLOAD_DIR", upload_dir)
    file_id = _create_case_with_attachment(str(target))
    res = client.get(f"/attachments/{file_id}", headers=_sysadmin_headers())
    assert res.status_code == 200 and res.headers["X-Integrity"] == "unverified"


def test_case_view_by_admin_is_audited_but_not_owner(wf):
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.REQUEST)
    client.get(f"/cases/{cid}", headers=wf["h"]["owner"])
    assert not any(a.startswith("CASE_VIEWED") for a in _audit_actions())
    client.get(f"/cases/{cid}", headers=wf["h"]["admin"])
    assert f"CASE_VIEWED: Case {cid}" in _audit_actions()


def test_legal_hold_requires_reason_and_admin(wf):
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.APPROVE, models.CaseResult.JUSTIFIED)
    assert client.post(f"/cases/{cid}/legal-hold", json={"hold": True}, headers=wf["h"]["admin"]).status_code == 422
    assert client.post(f"/cases/{cid}/legal-hold", json={"hold": True, "reason": "x"}, headers=wf["h"]["owner"]).status_code == 403
    res = client.post(f"/cases/{cid}/legal-hold", json={"hold": True, "reason": "징계 진행 중"}, headers=wf["h"]["admin"])
    assert res.status_code == 200 and res.json()["legal_hold"] is True
    assert f"LEGAL_HOLD_SET: Case {cid}" in _audit_actions()


def test_retention_anonymizes_expired_cases_except_legal_hold(wf, tmp_path, monkeypatch):
    from backend.core.config import settings
    from backend.tasks import batch_tasks
    upload_dir = (tmp_path / "uploads").resolve()
    monkeypatch.setattr(submissions_router, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(batch_tasks, "SessionLocal", TestingSessionLocal)

    expired = _make_case(wf["ids"]["owner"], models.CaseStatus.REQUEST)
    assert _submit_with_file(expired, wf["h"]["owner"]).status_code == 201
    held = _make_case(wf["ids"]["owner"], models.CaseStatus.APPROVE, models.CaseResult.JUSTIFIED)
    recent = _make_case(wf["ids"]["owner"], models.CaseStatus.APPROVE, models.CaseResult.JUSTIFIED)
    db = TestingSessionLocal()
    old = datetime(2020, 1, 1)
    for cid, when in ((expired, old), (held, old), (recent, datetime.now())):
        c = db.get(models.ClarificationCase, cid)
        c.case_status, c.case_result, c.final_review_date = models.CaseStatus.APPROVE, models.CaseResult.JUSTIFIED, when
    db.get(models.ClarificationCase, held).legal_hold = True
    db.commit()
    db.close()
    assert any(upload_dir.rglob("*.txt"))

    result = batch_tasks.archive_old_cases()
    assert result == {"anonymized_count": 1, "deleted_files": 1}
    assert not any(upload_dir.rglob("*.txt"))

    db = TestingSessionLocal()
    try:
        c = db.get(models.ClarificationCase, expired)
        assert c.anonymized_at and c.related_employee_id is None and "파기" in c.summary
        assert c.case_result == models.CaseResult.JUSTIFIED            # 통계용 값은 유지
        sub = db.query(models.ClarificationSubmission).filter_by(case_id=expired).one()
        assert "파기" in sub.content and sub.submitter_id is None
        assert db.query(models.ClarificationAttachment).count() == 0
        assert db.get(models.ClarificationCase, held).anonymized_at is None
        assert db.get(models.ClarificationCase, recent).anonymized_at is None
    finally:
        db.close()
    assert f"CASE_ANONYMIZED: Case {expired}" in " ".join(_audit_actions())

    # 다시 실행해도 같은 케이스를 또 처리하지 않음
    assert batch_tasks.archive_old_cases()["anonymized_count"] == 0


# --- 2차: 부서장 참조 · 직원 이력 · 내보내기 ---

def test_submission_sends_cc_to_manager_without_content(wf, fake_provider):
    _set_manager("owner", "other", wf)
    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.REQUEST)
    res = client.post("/submissions", data={"case_id": cid, "content": "개인적인 비밀 사유", "classification": "업무"},
                      headers=wf["h"]["owner"])
    assert res.status_code == 201
    assert [m["to"] for m in fake_provider.sent] == ["other@wf.com"]
    assert "참조" in fake_provider.sent[0]["subject"]
    assert "개인적인 비밀 사유" not in fake_provider.sent[0]["content"]


def test_manager_assignment_rules(wf):
    sys_h = _sysadmin_headers()
    owner_id, other_id = wf["ids"]["owner"], wf["ids"]["other"]
    base = {"user_email": "owner@wf.com", "user_name": "owner", "role": "일반"}
    res = client.put(f"/users/{owner_id}", json={**base, "manager_id": other_id}, headers=sys_h)
    assert res.status_code == 200 and res.json()["manager_id"] == other_id
    assert client.put(f"/users/{owner_id}", json={**base, "manager_id": owner_id}, headers=sys_h).status_code == 422
    # manager_id를 보내지 않으면 유지
    assert client.put(f"/users/{owner_id}", json=base, headers=sys_h).json()["manager_id"] == other_id


def test_user_cannot_escalate_own_role_or_change_manager(wf):
    owner_id = wf["ids"]["owner"]
    base = {"user_email": "owner@wf.com", "user_name": "owner"}
    res = client.put(f"/users/{owner_id}", json={**base, "role": "시스템관리자"}, headers=wf["h"]["owner"])
    assert res.status_code == 403
    res = client.put(f"/users/{owner_id}", json={**base, "role": "일반", "manager_id": wf["ids"]["other"]}, headers=wf["h"]["owner"])
    assert res.status_code == 403
    db = TestingSessionLocal()
    try:
        assert db.get(models.User, owner_id).role == models.UserRole.USER
    finally:
        db.close()


def test_entra_sync_links_managers(monkeypatch):
    from backend.modules.users import services as user_services
    monkeypatch.setattr(user_services.entra_service, "get_all_users", lambda entra: [
        {"userPrincipalName": "boss@corp.com", "displayName": "Boss"},
        {"userPrincipalName": "staff@corp.com", "displayName": "Staff", "manager": {"userPrincipalName": "boss@corp.com"}},
    ])
    db = TestingSessionLocal()
    try:
        result = user_services.sync_users_from_entra(db)
        assert result["created"] == 2 and result["managers_linked"] == 1
        staff = db.query(models.User).filter_by(user_email="staff@corp.com").one()
        boss = db.query(models.User).filter_by(user_email="boss@corp.com").one()
        assert staff.manager_id == boss.user_id
    finally:
        db.close()


def test_employee_history_summarizes_other_cases(wf):
    owner = wf["ids"]["owner"]
    current = _make_case(owner, models.CaseStatus.SUBMIT)
    _make_case(owner, models.CaseStatus.REJECT, models.CaseResult.DISCIPLINARY_ACTION)
    _make_case(owner, models.CaseStatus.REJECT, models.CaseResult.INSUFFICIENT)
    _make_case(owner, models.CaseStatus.APPROVE, models.CaseResult.JUSTIFIED)
    _make_case(wf["ids"]["other"], models.CaseStatus.REJECT, models.CaseResult.INSUFFICIENT)  # 다른 직원

    res = client.get(f"/cases/{current}/employee-history", headers=wf["h"]["admin"])
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3 and data["rejected"] == 2 and data["disciplinary"] == 1
    assert current not in [c["case_id"] for c in data["recent"]]
    assert client.get(f"/cases/{current}/employee-history", headers=wf["h"]["owner"]).status_code == 403


def test_case_export_csv_escapes_formulas_and_is_audited(wf):
    import csv, io
    db = TestingSessionLocal()
    db.add(models.ClarificationCase(rule_title="=HYPERLINK(\"http://evil\")", case_type=models.CaseType.INFO_LEAK,
                                    related_employee_id=wf["ids"]["owner"], due_date=datetime(2099, 1, 1),
                                    case_status=models.CaseStatus.REQUEST))
    db.commit()
    db.close()

    assert client.get("/cases/export", headers=wf["h"]["owner"]).status_code == 403
    res = client.get("/cases/export", headers=wf["h"]["admin"])
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/csv")
    assert res.text.startswith("﻿")
    rows = list(csv.reader(io.StringIO(res.text.lstrip("﻿"))))
    assert rows[0][0] == "케이스번호" and len(rows) == 2
    assert rows[1][2].startswith("'=")
    assert any(a.startswith("CASE_EXPORTED: 1 rows") for a in _audit_actions())


def test_audit_log_export(wf):
    res = client.get("/audit-logs/export", params={"start_date": "2020-01-01"}, headers=wf["h"]["admin"])
    assert res.status_code == 200 and "행위" in res.text
    assert client.get("/audit-logs/export", headers=wf["h"]["owner"]).status_code == 403
    assert client.get("/audit-logs/export", params={"start_date": "bad"}, headers=wf["h"]["admin"]).status_code == 422
    assert any(a.startswith("AUDIT_LOG_EXPORTED") for a in _audit_actions())


# --- 3차: 알림 템플릿 편집 · Teams 웹훅 ---

def test_template_list_and_custom_subject_used(wf, fake_provider):
    from backend.tasks import email_tasks
    res = client.get("/notifications/templates", headers=wf["h"]["admin"])
    assert res.status_code == 200
    keys = {t["template_key"] for t in res.json()}
    assert {"case_created.html", "overdue_notice.html", "submission_cc.html"} <= keys
    assert client.get("/notifications/templates", headers=wf["h"]["owner"]).status_code == 403

    res = client.put("/notifications/templates/case_created.html",
                     json={"subject": "맞춤 제목 #{{ case_id }}", "body_html": "<p>{{ employee_name }} / {{ app_url }}/cases/{{ case_id }}</p>"},
                     headers=wf["h"]["admin"])
    assert res.status_code == 200 and res.json()["is_customized"] is True

    cid = _make_case(wf["ids"]["owner"], models.CaseStatus.UNCLASSIFIED)
    email_tasks.send_case_created_email(cid)
    assert fake_provider.sent[-1]["subject"] == f"맞춤 제목 #{cid}"
    assert "<p>owner /" in fake_provider.sent[-1]["content"]

    # 초기화하면 기본 템플릿으로
    assert client.delete("/notifications/templates/case_created.html", headers=wf["h"]["admin"]).json()["is_customized"] is False
    email_tasks.send_case_created_email(cid)
    assert "새로운 소명 케이스" in fake_provider.sent[-1]["subject"]


@pytest.mark.parametrize("body", [
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",   # 샌드박스 위반 (템플릿 주입)
    "{% if %}",                                          # 문법 오류
])
def test_template_rejects_unsafe_or_invalid(wf, body):
    res = client.put("/notifications/templates/case_created.html", json={"subject": "s", "body_html": body}, headers=wf["h"]["admin"])
    assert res.status_code == 422


def test_template_preview_escapes_html(wf):
    res = client.post("/notifications/templates/case_created.html/preview",
                      json={"subject": "제목 {{ case_id }}", "body_html": "<b>{{ rule_title }}</b>{{ '<script>' }}"},
                      headers=wf["h"]["admin"])
    assert res.status_code == 200
    assert res.json()["subject"] == "제목 1024"
    assert "&lt;script&gt;" in res.json()["body_html"]


def test_teams_webhook_settings_and_message(wf, monkeypatch):
    from backend.modules.integrations import services as integ
    sys_h = _sysadmin_headers()
    assert client.put("/integrations/teams", json={"is_enabled": True}, headers=sys_h).status_code == 422
    assert client.put("/integrations/teams", json={"is_enabled": True, "webhook_url": "http://insecure"}, headers=sys_h).status_code == 422
    assert client.put("/integrations/teams", json={"is_enabled": True}, headers=wf["h"]["admin"]).status_code == 403

    url = "https://example.webhook.office.com/workflows/abc?sig=secret"
    res = client.put("/integrations/teams", json={"is_enabled": True, "webhook_url": url}, headers=sys_h)
    assert res.status_code == 200 and res.json()["webhook_url_set"] is True and "secret" not in res.text

    posted = []

    class _Resp:
        status_code = 202

    monkeypatch.setattr(integ.requests, "post", lambda u, json, timeout: posted.append((u, json)) or _Resp())
    assert integ.send_teams_message(title="T", text="본문", facts=[("케이스", "#1")], link_url="https://sics/x") is True
    assert posted[0][0] == url
    card = posted[0][1]["attachments"][0]
    assert card["contentType"] == "application/vnd.microsoft.card.adaptive"
    assert card["content"]["body"][0]["text"] == "T"

    # 끄면 보내지 않음
    client.put("/integrations/teams", json={"is_enabled": False}, headers=sys_h)
    assert integ.send_teams_message(title="T", text="x") is False and len(posted) == 1
