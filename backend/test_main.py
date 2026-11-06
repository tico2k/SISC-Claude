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
    monkeypatch.setattr(settings, "ENABLE_EMAIL_NOTIFICATIONS", False)
    monkeypatch.setattr(email_tasks, "SessionLocal", TestingSessionLocal)

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
    monkeypatch.setattr(email_tasks.email_service, "send_template_email", lambda **kw: sent.update(kw) or True)

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
