#!/usr/bin/env python3
"""server.py —— 官网站点服务（FastAPI：静态托管 + 独立注册/登录体系 + 图形验证码 + 个人资料 + 受限资源守卫）。

职责：
  · 静态托管 site/（纯静态产物）
  · /api/auth/captcha 图形验证码生成（SVG，防刷短信与防暴力破解）
  · /api/auth/send-code 发送阿里云号码认证短信验证码（需先过图形验证码 + 区分 login/register 场景）
  · /api/auth/register 手机号 + 短信验证码 + 密码 + 个人资料注册
  · /api/auth/login 手机号 + 短信验证码登录（仅限已注册用户）
  · /api/auth/login-password 手机号/昵称 + 密码 + 图形验证码登录
  · /api/auth/me & PUT /api/auth/profile 获取与编辑个人资料（昵称、部门、职业、公司、邮箱）
  · /api/resources/* 登录受限资源接口
  · /api/counter/hit 浏览量统计
  · /api/health 健康检查
"""
from __future__ import annotations

import base64
from datetime import date, datetime, timezone
import hashlib
import hmac
import html as html_mod
import json
import os
from pathlib import Path
import random
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
SITE = BASE / "site"


def _load_dotenv(env_path: Path) -> None:
    """零依赖加载仓库根目录 .env（不覆盖已有环境变量）。"""
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        if k:
            os.environ.setdefault(k, v)


_load_dotenv(BASE / ".env")

AUTH_DB = Path(os.environ.get("AUTH_DB_PATH", str(BASE / "auth.db")))
HITS_DB = Path(os.environ.get("HITS_DB_PATH", str(BASE / "tools" / "hits.db")))
SESSION_COOKIE = "cf_site_session"
SESSION_TTL_SEC = 30 * 86400
SMS_COOLDOWN_SEC = 60
SMS_MAX_ATTEMPTS = 5
CAPTCHA_TTL_SEC = 300
CAPTCHA_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
CODE_RE = re.compile(r"^\d{4,8}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_AUTH_SALT = "codeflow-website-auth-v1"
_COUNTER_SALT = "site-counter-v1"

_db_lock = threading.Lock()
_hits_lock = threading.Lock()

USER_PROFILE_COLUMNS = {
    "password_hash": "TEXT NOT NULL DEFAULT ''",
    "nickname": "TEXT NOT NULL DEFAULT ''",
    "department": "TEXT NOT NULL DEFAULT ''",
    "profession": "TEXT NOT NULL DEFAULT ''",
    "company": "TEXT NOT NULL DEFAULT ''",
    "email": "TEXT NOT NULL DEFAULT ''",
    "vip_type": "TEXT NOT NULL DEFAULT '普通用户'",
    "vip_expire_at": "TEXT NOT NULL DEFAULT '--'",
}


def _init_auth_db() -> sqlite3.Connection:
    AUTH_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUTH_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      phone         TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL DEFAULT '',
      nickname      TEXT NOT NULL DEFAULT '',
      department    TEXT NOT NULL DEFAULT '',
      profession    TEXT NOT NULL DEFAULT '',
      company       TEXT NOT NULL DEFAULT '',
      email         TEXT NOT NULL DEFAULT '',
      vip_type      TEXT NOT NULL DEFAULT '普通用户',
      vip_expire_at TEXT NOT NULL DEFAULT '--',
      created_at    TEXT NOT NULL,
      last_login_at TEXT NOT NULL,
      login_count   INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS captchas (
      id         TEXT PRIMARY KEY,
      code_hash  TEXT NOT NULL,
      ip         TEXT,
      created_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sms_codes (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      phone      TEXT NOT NULL,
      scene      TEXT NOT NULL DEFAULT 'login',
      code_hash  TEXT NOT NULL,
      ip         TEXT,
      created_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL,
      attempts   INTEGER NOT NULL DEFAULT 0,
      used       INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_sms_phone_created ON sms_codes(phone, created_at DESC);
    CREATE TABLE IF NOT EXISTS sessions (
      token_hash TEXT PRIMARY KEY,
      user_id    INTEGER NOT NULL,
      phone      TEXT NOT NULL,
      ip         TEXT,
      user_agent TEXT,
      created_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS trial_applications (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id    INTEGER NOT NULL,
      phone      TEXT NOT NULL,
      company    TEXT NOT NULL,
      scenario   TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    """)
    existing_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    for col, ddl in USER_PROFILE_COLUMNS.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
    sms_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(sms_codes)").fetchall()
    }
    if "scene" not in sms_cols:
        conn.execute("ALTER TABLE sms_codes ADD COLUMN scene TEXT NOT NULL DEFAULT 'login'")
    conn.commit()
    return conn


def _init_hits_db() -> sqlite3.Connection:
    HITS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(HITS_DB, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS hits(
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      day    TEXT DEFAULT (date('now','localtime')),
      iphash TEXT,
      path   TEXT);
    CREATE INDEX IF NOT EXISTS idx_hits_day  ON hits(day);
    CREATE INDEX IF NOT EXISTS idx_hits_path ON hits(path);
    """)
    return conn


_auth_conn = _init_auth_db()
_hits_conn = _init_hits_db()


def _hash_value(val: str) -> str:
    return hashlib.sha256((_AUTH_SALT + ":" + val).encode("utf-8")).hexdigest()


def hash_password(password: str, salt: str | None = None) -> str:
    s = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), s.encode("utf-8"), 100_000).hex()
    return f"pbkdf2_sha256${s}${dk}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    parts = stored.split("$")
    if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
        return False
    expected = hash_password(password, parts[1])
    return hmac.compare_digest(expected, stored)


def mask_phone(phone: str) -> str:
    if len(phone) == 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone


def default_nickname(phone: str) -> str:
    return f"q{phone[-4:]}" if len(phone) >= 4 else "q_user"


def serialize_user(row: sqlite3.Row | dict) -> dict:
    phone = str(row["phone"])
    nick = str(row["nickname"] or "").strip() or default_nickname(phone)
    return {
        "id": int(row["id"]),
        "phone": mask_phone(phone),
        "nickname": nick,
        "department": str(row["department"] or "").strip(),
        "profession": str(row["profession"] or "").strip(),
        "company": str(row["company"] or "").strip(),
        "email": str(row["email"] or "").strip(),
        "vipType": str(row["vip_type"] or "普通用户").strip() or "普通用户",
        "vipExpireAt": str(row["vip_expire_at"] or "--").strip() or "--",
        "hasPassword": bool(str(row["password_hash"] or "").strip()),
    }


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def generate_captcha_svg(code: str) -> str:
    """生成带干扰线、噪点与字符旋转的 SVG 图形验证码（零第三方图像库依赖）。"""
    rng = random.SystemRandom()
    width, height = 116, 40
    palette = ["#60a5fa", "#34d399", "#a78bfa", "#f472b6", "#fbbf24", "#38bdf8"]
    lines = []
    for _ in range(4):
        x1, y1 = rng.randint(4, width - 4), rng.randint(4, height - 4)
        x2, y2 = rng.randint(4, width - 4), rng.randint(4, height - 4)
        c = rng.choice(palette)
        lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{c}" stroke-width="1.2" stroke-opacity="0.42"/>'
        )
    dots = []
    for _ in range(18):
        cx, cy = rng.randint(4, width - 4), rng.randint(4, height - 4)
        c = rng.choice(palette)
        dots.append(f'<circle cx="{cx}" cy="{cy}" r="1.1" fill="{c}" fill-opacity="0.45"/>')
    chars = []
    for i, ch in enumerate(code):
        x = 16 + i * 24 + rng.randint(-2, 2)
        y = 26 + rng.randint(-3, 3)
        rot = rng.randint(-16, 16)
        c = rng.choice(palette)
        esc = html_mod.escape(ch)
        chars.append(
            f'<text x="{x}" y="{y}" fill="{c}" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
            f'font-size="20" font-weight="700" transform="rotate({rot} {x} {y})">{esc}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="图形验证码">'
        f'<rect width="100%" height="100%" rx="7" fill="#131926"/>'
        + "".join(lines)
        + "".join(dots)
        + "".join(chars)
        + "</svg>"
    )


def verify_and_consume_captcha(captcha_id: str, captcha_code: str, *, consume_on_match: bool = True) -> bool:
    cid = (captcha_id or "").strip()
    ccode = (captcha_code or "").strip().upper()
    if not cid or not ccode:
        return False
    now = int(time.time())
    expected = _hash_value(f"captcha:{cid}:{ccode}")
    with _db_lock:
        _auth_conn.execute("DELETE FROM captchas WHERE expires_at < ?", (now,))
        row = _auth_conn.execute(
            "SELECT code_hash, expires_at FROM captchas WHERE id=?",
            (cid,),
        ).fetchone()
        if not row or int(row["expires_at"]) < now:
            _auth_conn.execute("DELETE FROM captchas WHERE id=?", (cid,))
            _auth_conn.commit()
            return False
        matched = hmac.compare_digest(str(row["code_hash"]), expected)
        if not matched or consume_on_match:
            _auth_conn.execute("DELETE FROM captchas WHERE id=?", (cid,))
            _auth_conn.commit()
        return matched


def consume_captcha(captcha_id: str) -> None:
    cid = (captcha_id or "").strip()
    if not cid:
        return
    with _db_lock:
        _auth_conn.execute("DELETE FROM captchas WHERE id=?", (cid,))
        _auth_conn.commit()


def _pop_quote(val: str) -> str:
    return urllib.parse.quote(str(val), safe="~")


def build_dypns_signed_body(
    *,
    access_key_id: str,
    access_key_secret: str,
    phone: str,
    sign_name: str,
    template_code: str,
    template_param: str,
    timestamp: str | None = None,
    nonce: str | None = None,
) -> tuple[bytes, dict[str, str]]:
    """构造阿里云号码认证服务 SendSmsVerifyCode POP RPC 签名请求体。"""
    params = {
        "AccessKeyId": access_key_id,
        "Action": "SendSmsVerifyCode",
        "CountryCode": "86",
        "Format": "JSON",
        "PhoneNumber": phone,
        "SignName": sign_name,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": nonce or uuid.uuid4().hex,
        "SignatureVersion": "1.0",
        "TemplateCode": template_code,
        "TemplateParam": template_param,
        "Timestamp": timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    canonical = "&".join(f"{_pop_quote(k)}={_pop_quote(v)}" for k, v in sorted(params.items()))
    string_to_sign = f"POST&%2F&{_pop_quote(canonical)}"
    sig = base64.b64encode(
        hmac.new((access_key_secret + "&").encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")
    full_params = {**params, "Signature": sig}
    body = f"Signature={_pop_quote(sig)}&{canonical}".encode("utf-8")
    return body, full_params


def _sms_expire_minutes() -> int:
    raw = os.environ.get("DYPNS_TEMPLATE_PARAM_EXTRA", "{}").strip() or "{}"
    try:
        extra = json.loads(raw)
        return max(1, min(30, int(extra.get("min", 5))))
    except Exception:  # noqa: BLE001
        return 5


def send_dypns_verify_code(phone: str, code: str) -> dict:
    """调用阿里云 dypnsapi SendSmsVerifyCode 发送短信验证码。"""
    if os.environ.get("AUTH_SMS_MOCK") == "1":
        return {"Code": "OK", "Message": "MOCK_OK"}

    ak_id = os.environ.get("DYPNS_ACCESS_KEY_ID", "").strip()
    ak_secret = os.environ.get("DYPNS_ACCESS_KEY_SECRET", "").strip()
    sign_name = os.environ.get("DYPNS_SIGN_NAME", "").strip()
    template_code = os.environ.get("DYPNS_TEMPLATE_CODE", "").strip()
    extra_raw = os.environ.get("DYPNS_TEMPLATE_PARAM_EXTRA", "{}").strip() or "{}"

    if not (ak_id and ak_secret and sign_name and template_code):
        raise RuntimeError("短信服务未完成配置（缺少 DYPNS_* 环境变量）")

    try:
        extra = json.loads(extra_raw)
        if not isinstance(extra, dict):
            extra = {}
    except json.JSONDecodeError:
        extra = {}

    template_param = json.dumps({"code": str(code), **extra}, ensure_ascii=False, separators=(",", ":"))
    body, _ = build_dypns_signed_body(
        access_key_id=ak_id,
        access_key_secret=ak_secret,
        phone=phone,
        sign_name=sign_name,
        template_code=template_code,
        template_param=template_param,
    )
    endpoint = os.environ.get("DYPNS_ENDPOINT", "https://dypnsapi.aliyuncs.com/")
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw_err = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_err)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"短信网关请求失败 (HTTP {e.code})") from exc
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"短信服务网络异常：{e}") from e

    res_code = str(payload.get("Code") or "")
    if res_code != "OK":
        msg = payload.get("Message") or res_code or "未知错误"
        if "BUSINESS_LIMIT_CONTROL" in res_code or "触发流控" in str(msg):
            raise RuntimeError("验证码发送过于频繁，请稍后再试")
        raise RuntimeError(f"短信发送失败：{msg}")
    return payload


def _create_session_response(user_row: sqlite3.Row, ip: str, ua: str, message: str = "登录成功") -> JSONResponse:
    now = int(time.time())
    raw_token = secrets.token_urlsafe(32)
    user_id = int(user_row["id"])
    phone = str(user_row["phone"])
    with _db_lock:
        _auth_conn.execute(
            "INSERT INTO sessions(token_hash, user_id, phone, ip, user_agent, created_at, expires_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (_hash_value(raw_token), user_id, phone, ip, ua, now, now + SESSION_TTL_SEC),
        )
        _auth_conn.commit()
    resp = JSONResponse({
        "ok": True,
        "message": message,
        "user": serialize_user(user_row),
    })
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=raw_token,
        max_age=SESSION_TTL_SEC,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return resp


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE, "").strip()
    if not token:
        return None
    now = int(time.time())
    thash = _hash_value(token)
    with _db_lock:
        srow = _auth_conn.execute(
            "SELECT user_id, phone, expires_at FROM sessions WHERE token_hash=?",
            (thash,),
        ).fetchone()
        if not srow:
            return None
        if int(srow["expires_at"]) < now:
            _auth_conn.execute("DELETE FROM sessions WHERE token_hash=?", (thash,))
            _auth_conn.commit()
            return None
        urow = _auth_conn.execute(
            "SELECT * FROM users WHERE id=?",
            (int(srow["user_id"]),),
        ).fetchone()
        if not urow:
            return None
        info = serialize_user(urow)
        info["raw_phone"] = str(urow["phone"])
        return info


app = FastAPI(title="CodeFlow 官网（含 TestOps 子站）", docs_url=None, redoc_url=None)


def repo_url() -> str:
    """开源仓库地址只存在于部署环境（.env），不写进代码、不出现在任何静态产物里。
    未登录的访客拿不到本值——需登录后由 /api/auth/repo 下发。"""
    return os.environ.get("CODEFLOW_REPO_URL", "").strip().rstrip("/")


def repo_info() -> dict:
    url = repo_url()
    if not url:
        return {}
    return {
        "repo_url": url,
        "clone_url": url + ".git",
        "host": url.split("//")[-1],
    }


@app.get("/api/health")
async def health() -> JSONResponse:
    """部署探活：站点产物是否就位。"""
    index = SITE / "index.html"
    return JSONResponse({
        "status": "up" if index.exists() else "degraded",
        "site": str(SITE),
        "pages": len(list(SITE.rglob("*.html"))),
    })


@app.get("/api/counter/hit")
@app.get("/api/hit")
async def counter_hit(request: Request, path: str = "/") -> JSONResponse:
    clean_path = (path or "/")[:120]
    ip = _client_ip(request)
    iphash = hashlib.sha256((_COUNTER_SALT + ip).encode()).hexdigest()[:16]
    today = date.today().isoformat()
    with _hits_lock:
        _hits_conn.execute("INSERT INTO hits(iphash,path) VALUES(?,?)", (iphash, clean_path))
        total = _hits_conn.execute("SELECT COUNT(*) FROM hits").fetchone()[0]
        td = _hits_conn.execute("SELECT COUNT(*) FROM hits WHERE day=?", (today,)).fetchone()[0]
        uv = _hits_conn.execute("SELECT COUNT(DISTINCT iphash) FROM hits").fetchone()[0]
        _hits_conn.commit()
    return JSONResponse({"total": total, "today": td, "visitors": uv})


@app.get("/api/auth/captcha")
async def auth_captcha(request: Request) -> JSONResponse:
    """生成 4 位 SVG 图形验证码（点击可刷新）。"""
    rng = random.SystemRandom()
    code = "".join(rng.choice(CAPTCHA_CHARS) for _ in range(4))
    cid = secrets.token_urlsafe(16)
    now = int(time.time())
    ip = _client_ip(request)
    with _db_lock:
        _auth_conn.execute("DELETE FROM captchas WHERE expires_at < ?", (now,))
        _auth_conn.execute(
            "INSERT INTO captchas(id, code_hash, ip, created_at, expires_at) VALUES(?,?,?,?,?)",
            (cid, _hash_value(f"captcha:{cid}:{code}"), ip, now, now + CAPTCHA_TTL_SEC),
        )
        _auth_conn.commit()
    return JSONResponse({
        "ok": True,
        "captchaId": cid,
        "svg": generate_captcha_svg(code),
    })


@app.post("/api/auth/send-code")
async def auth_send_code(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    phone = str((body or {}).get("phone") or "").strip()
    scene = str((body or {}).get("scene") or "login").strip().lower()
    if scene not in ("login", "register", "reset"):
        scene = "login"
    captcha_id = str((body or {}).get("captchaId") or "").strip()
    captcha_code = str((body or {}).get("captchaCode") or "").strip()

    if not PHONE_RE.match(phone):
        return JSONResponse({"ok": False, "message": "请输入有效的 11 位中国大陆手机号"}, status_code=400)
    if not verify_and_consume_captcha(captcha_id, captcha_code, consume_on_match=False):
        return JSONResponse(
            {"ok": False, "code": "CAPTCHA_INVALID", "message": "图形验证码错误或已过期，请刷新后重试"},
            status_code=400,
        )

    now = int(time.time())
    ip = _client_ip(request)
    with _db_lock:
        existing_user = _auth_conn.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
        if scene in ("login", "reset") and not existing_user:
            return JSONResponse(
                {"ok": False, "code": "USER_NOT_FOUND", "message": "该手机号尚未注册，请先切换到「注册账号」"},
                status_code=404,
            )
        if scene == "register" and existing_user:
            return JSONResponse(
                {"ok": False, "code": "USER_EXISTS", "message": "该手机号已注册，请直接切换到「登录」"},
                status_code=409,
            )

        recent = _auth_conn.execute(
            "SELECT created_at FROM sms_codes WHERE phone=? ORDER BY created_at DESC LIMIT 1",
            (phone,),
        ).fetchone()
        if recent and now - int(recent["created_at"]) < SMS_COOLDOWN_SEC:
            wait_sec = SMS_COOLDOWN_SEC - (now - int(recent["created_at"]))
            return JSONResponse(
                {"ok": False, "message": f"发送过于频繁，请 {wait_sec} 秒后再试", "retryAfter": wait_sec},
                status_code=429,
            )
        ip_cnt = _auth_conn.execute(
            "SELECT COUNT(*) FROM sms_codes WHERE ip=? AND created_at>?",
            (ip, now - 3600),
        ).fetchone()[0]
        if ip_cnt >= 20:
            return JSONResponse({"ok": False, "message": "当前网络请求过于频繁，请稍后再试"}, status_code=429)

    consume_captcha(captcha_id)
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    expire_min = _sms_expire_minutes()
    try:
        send_dypns_verify_code(phone, code)
    except RuntimeError as e:
        return JSONResponse({"ok": False, "message": str(e)}, status_code=502)

    expires_at = now + expire_min * 60
    with _db_lock:
        _auth_conn.execute(
            "INSERT INTO sms_codes(phone, scene, code_hash, ip, created_at, expires_at) VALUES(?,?,?,?,?,?)",
            (phone, scene, _hash_value(f"{phone}:{code}"), ip, now, expires_at),
        )
        _auth_conn.commit()

    return JSONResponse({
        "ok": True,
        "message": "短信验证码已发送，请注意查收",
        "cooldown": SMS_COOLDOWN_SEC,
        "expiresIn": expire_min * 60,
        "maskedPhone": mask_phone(phone),
    })


def _verify_sms_code(phone: str, code: str) -> tuple[bool, str]:
    now = int(time.time())
    expected_hash = _hash_value(f"{phone}:{code}")
    row = _auth_conn.execute(
        "SELECT id, code_hash, expires_at, attempts, used FROM sms_codes "
        "WHERE phone=? ORDER BY created_at DESC, id DESC LIMIT 1",
        (phone,),
    ).fetchone()
    if not row or int(row["used"]) == 1:
        return False, "请先获取短信验证码"
    if int(row["expires_at"]) < now:
        return False, "短信验证码已过期，请重新获取"
    if int(row["attempts"]) >= SMS_MAX_ATTEMPTS:
        return False, "短信验证码尝试次数过多，请重新获取"
    if not hmac.compare_digest(str(row["code_hash"]), expected_hash):
        _auth_conn.execute("UPDATE sms_codes SET attempts=attempts+1 WHERE id=?", (int(row["id"]),))
        _auth_conn.commit()
        return False, "短信验证码错误，请核对后重试"
    _auth_conn.execute("UPDATE sms_codes SET used=1 WHERE id=?", (int(row["id"]),))
    _auth_conn.commit()
    return True, ""


@app.post("/api/auth/register")
async def auth_register(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    phone = str((body or {}).get("phone") or "").strip()
    code = str((body or {}).get("code") or "").strip()
    password = str((body or {}).get("password") or "")
    confirm_password = str((body or {}).get("confirmPassword") or "")
    nickname = str((body or {}).get("nickname") or "").strip()[:32]
    department = str((body or {}).get("department") or "").strip()[:48]
    profession = str((body or {}).get("profession") or "").strip()[:48]
    company = str((body or {}).get("company") or "").strip()[:80]
    email = str((body or {}).get("email") or "").strip()[:80]

    if not PHONE_RE.match(phone):
        return JSONResponse({"ok": False, "message": "请输入有效的 11 位手机号"}, status_code=400)
    if not CODE_RE.match(code):
        return JSONResponse({"ok": False, "message": "请输入短信中的数字验证码"}, status_code=400)
    if len(password) < 6:
        return JSONResponse({"ok": False, "message": "请设置至少 6 位登录密码"}, status_code=400)
    if password != confirm_password:
        return JSONResponse({"ok": False, "message": "两次输入的密码不一致，请重新核对"}, status_code=400)
    if email and not EMAIL_RE.match(email):
        return JSONResponse({"ok": False, "message": "邮箱格式不正确"}, status_code=400)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ip = _client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:250]

    with _db_lock:
        exists = _auth_conn.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
        if exists:
            return JSONResponse(
                {"ok": False, "code": "USER_EXISTS", "message": "该手机号已注册，请直接登录"},
                status_code=409,
            )
        ok, err_msg = _verify_sms_code(phone, code)
        if not ok:
            return JSONResponse({"ok": False, "message": err_msg}, status_code=400)

        final_nick = nickname or default_nickname(phone)
        pwd_hash = hash_password(password)
        cur = _auth_conn.execute(
            "INSERT INTO users(phone, password_hash, nickname, department, profession, company, email, "
            "vip_type, vip_expire_at, created_at, last_login_at, login_count) "
            "VALUES(?,?,?,?,?,?,?,'普通用户','--',?,?,1)",
            (phone, pwd_hash, final_nick, department, profession, company, email, now_iso, now_iso),
        )
        user_id = int(cur.lastrowid)
        _auth_conn.commit()
        user_row = _auth_conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    return _create_session_response(user_row, ip, ua, message="注册成功，已自动登录")


@app.post("/api/auth/login")
async def auth_login(request: Request) -> JSONResponse:
    """手机号 + 短信验证码登录（要求手机号已完成注册）。"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    phone = str((body or {}).get("phone") or "").strip()
    code = str((body or {}).get("code") or "").strip()
    if not PHONE_RE.match(phone):
        return JSONResponse({"ok": False, "message": "请输入有效的 11 位手机号"}, status_code=400)
    if not CODE_RE.match(code):
        return JSONResponse({"ok": False, "message": "请输入短信中的数字验证码"}, status_code=400)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ip = _client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:250]

    with _db_lock:
        user_row = _auth_conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        if not user_row:
            return JSONResponse(
                {"ok": False, "code": "USER_NOT_FOUND", "message": "该手机号尚未注册，请先切换到「注册账号」"},
                status_code=404,
            )
        ok, err_msg = _verify_sms_code(phone, code)
        if not ok:
            return JSONResponse({"ok": False, "message": err_msg}, status_code=400)

        user_id = int(user_row["id"])
        _auth_conn.execute(
            "UPDATE users SET last_login_at=?, login_count=login_count+1 WHERE id=?",
            (now_iso, user_id),
        )
        _auth_conn.commit()
        user_row = _auth_conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    return _create_session_response(user_row, ip, ua, message="登录成功")


@app.post("/api/auth/login-password")
async def auth_login_password(request: Request) -> JSONResponse:
    """手机号/昵称 + 密码 + 图形验证码登录。"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    account = str((body or {}).get("account") or "").strip()
    password = str((body or {}).get("password") or "")
    captcha_id = str((body or {}).get("captchaId") or "").strip()
    captcha_code = str((body or {}).get("captchaCode") or "").strip()

    if not account or not password:
        return JSONResponse({"ok": False, "message": "请输入账号（手机号/昵称）和密码"}, status_code=400)
    if not verify_and_consume_captcha(captcha_id, captcha_code):
        return JSONResponse(
            {"ok": False, "code": "CAPTCHA_INVALID", "message": "图形验证码错误或已过期，请刷新后重试"},
            status_code=400,
        )

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ip = _client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:250]

    with _db_lock:
        user_row = _auth_conn.execute(
            "SELECT * FROM users WHERE phone=? OR nickname=? LIMIT 1",
            (account, account),
        ).fetchone()
        if not user_row:
            return JSONResponse(
                {"ok": False, "code": "USER_NOT_FOUND", "message": "账号不存在，请先注册"},
                status_code=404,
            )
        if not verify_password(password, str(user_row["password_hash"] or "")):
            return JSONResponse({"ok": False, "message": "账号或密码错误"}, status_code=400)
        user_id = int(user_row["id"])
        _auth_conn.execute(
            "UPDATE users SET last_login_at=?, login_count=login_count+1 WHERE id=?",
            (now_iso, user_id),
        )
        _auth_conn.commit()
        user_row = _auth_conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    return _create_session_response(user_row, ip, ua, message="登录成功")


@app.get("/api/auth/me")
async def auth_me(request: Request) -> JSONResponse:
    user = get_current_user(request)
    if not user:
        return JSONResponse({"authenticated": False, "user": None})
    out = {k: v for k, v in user.items() if k != "raw_phone"}
    return JSONResponse({"authenticated": True, "user": out})


@app.put("/api/auth/profile")
async def auth_update_profile(request: Request) -> JSONResponse:
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "message": "请先登录"}, status_code=401)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}

    nickname = str((body or {}).get("nickname") or "").strip()[:32]
    department = str((body or {}).get("department") or "").strip()[:48]
    profession = str((body or {}).get("profession") or "").strip()[:48]
    company = str((body or {}).get("company") or "").strip()[:80]
    email = str((body or {}).get("email") or "").strip()[:80]

    if not nickname:
        return JSONResponse({"ok": False, "message": "昵称不能为空"}, status_code=400)
    if email and not EMAIL_RE.match(email):
        return JSONResponse({"ok": False, "message": "邮箱格式不正确"}, status_code=400)

    with _db_lock:
        _auth_conn.execute(
            "UPDATE users SET nickname=?, department=?, profession=?, company=?, email=? WHERE id=?",
            (nickname, department, profession, company, email, user["id"]),
        )
        _auth_conn.commit()
        urow = _auth_conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()

    return JSONResponse({
        "ok": True,
        "message": "个人资料已保存",
        "user": serialize_user(urow),
    })


@app.post("/api/auth/password")
async def auth_set_or_change_password(request: Request) -> JSONResponse:
    """已登录用户设置初始密码（无旧密码时）或修改密码。"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "message": "请先登录"}, status_code=401)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}

    old_password = str((body or {}).get("oldPassword") or "")
    new_password = str((body or {}).get("newPassword") or "")
    confirm_password = str((body or {}).get("confirmPassword") or "")

    if len(new_password) < 6:
        return JSONResponse({"ok": False, "message": "新密码长度至少为 6 位"}, status_code=400)
    if new_password != confirm_password:
        return JSONResponse({"ok": False, "message": "两次输入的新密码不一致，请重新核对"}, status_code=400)

    with _db_lock:
        urow = _auth_conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        if not urow:
            return JSONResponse({"ok": False, "message": "用户不存在"}, status_code=404)
        stored_hash = str(urow["password_hash"] or "").strip()
        if stored_hash and not verify_password(old_password, stored_hash):
            return JSONResponse({"ok": False, "message": "原密码不正确"}, status_code=400)
        _auth_conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(new_password), user["id"]),
        )
        _auth_conn.commit()
        urow = _auth_conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()

    return JSONResponse({
        "ok": True,
        "message": "密码修改成功" if stored_hash else "密码设置成功，后续可使用账号密码登录",
        "user": serialize_user(urow),
    })


@app.post("/api/auth/reset-password")
async def auth_reset_password(request: Request) -> JSONResponse:
    """未登录用户通过手机号 + 短信验证码设置/重置密码并自动登录。"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    phone = str((body or {}).get("phone") or "").strip()
    code = str((body or {}).get("code") or "").strip()
    new_password = str((body or {}).get("newPassword") or "")
    confirm_password = str((body or {}).get("confirmPassword") or "")

    if not PHONE_RE.match(phone):
        return JSONResponse({"ok": False, "message": "请输入有效的 11 位手机号"}, status_code=400)
    if not CODE_RE.match(code):
        return JSONResponse({"ok": False, "message": "请输入短信中的数字验证码"}, status_code=400)
    if len(new_password) < 6:
        return JSONResponse({"ok": False, "message": "新密码长度至少为 6 位"}, status_code=400)
    if new_password != confirm_password:
        return JSONResponse({"ok": False, "message": "两次输入的新密码不一致，请重新核对"}, status_code=400)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ip = _client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:250]

    with _db_lock:
        urow = _auth_conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        if not urow:
            return JSONResponse(
                {"ok": False, "code": "USER_NOT_FOUND", "message": "该手机号尚未注册，请先切换到「注册账号」"},
                status_code=404,
            )
        ok, err_msg = _verify_sms_code(phone, code)
        if not ok:
            return JSONResponse({"ok": False, "message": err_msg}, status_code=400)

        user_id = int(urow["id"])
        _auth_conn.execute(
            "UPDATE users SET password_hash=?, last_login_at=?, login_count=login_count+1 WHERE id=?",
            (hash_password(new_password), now_iso, user_id),
        )
        _auth_conn.commit()
        urow = _auth_conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    return _create_session_response(urow, ip, ua, message="密码已设置并自动登录")


@app.post("/api/auth/logout")
async def auth_logout(request: Request) -> JSONResponse:
    token = request.cookies.get(SESSION_COOKIE, "").strip()
    if token:
        with _db_lock:
            _auth_conn.execute("DELETE FROM sessions WHERE token_hash=?", (_hash_value(token),))
            _auth_conn.commit()
    resp = JSONResponse({"ok": True, "message": "已退出登录"})
    resp.delete_cookie(key=SESSION_COOKIE, path="/")
    return resp


@app.get("/api/auth/repo")
async def auth_repo(request: Request):
    """登录后返回开源仓库地址（未登录一律 401，不泄露任何片段）。"""
    user = get_current_user(request)
    if not user:
        return JSONResponse(
            {"ok": False, "code": "AUTH_REQUIRED", "message": "请先登录官网账号后再查看开源仓库地址"},
            status_code=401,
        )
    info = repo_info()
    if not info:
        return JSONResponse(
            {"ok": False, "code": "REPO_NOT_OPEN", "message": "开源仓库地址尚未开放，请稍后再试"},
            status_code=503,
        )
    return JSONResponse({"ok": True, **info})


# ── 媒体门禁：视频文件在站点目录之外，仅凭短时效令牌经 nginx internal 转发 ──
MEDIA_SECRET = os.environ.get("MEDIA_TOKEN_SECRET", "").strip() or secrets.token_hex(32)
MEDIA_DIR = Path(os.environ.get("MEDIA_DIR", "/opt/codeflow-app/media"))
# 名称 → 文件白名单（路径不可拼接，只允许枚举键）
MEDIA_FILES = {"demo": "demo.mp4", "ecom": "ecom.mp4", "perf": "perf.mp4"}
MEDIA_TTL_SEC = 30 * 60


def _media_token(now: int) -> str:
    # 通配令牌：一个窗口内对所有白名单媒体有效（30 分钟换一次）
    msg = f"media:*:{now // MEDIA_TTL_SEC * MEDIA_TTL_SEC}".encode()
    return hmac.new(MEDIA_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def _media_check(name: str, token: str) -> bool:
    if name not in MEDIA_FILES or not token:
        return False
    now = int(time.time())
    return hmac.compare_digest(token, _media_token(now)) or \
        hmac.compare_digest(token, _media_token(now - MEDIA_TTL_SEC))


@app.get("/api/media/token")
async def media_token(request: Request):
    """发短时效视频令牌（浏览器 <video> 取流用；直链文件已在站点目录外，404）。"""
    return JSONResponse({"ok": True, "t": _media_token(int(time.time())), "ttl": MEDIA_TTL_SEC})


@app.get("/api/media/v/{name}")
async def media_stream(name: str, request: Request):
    token = request.query_params.get("t", "")
    if not _media_check(name, token):
        return JSONResponse(
            {"ok": False, "code": "MEDIA_FORBIDDEN", "message": "视频链接已过期，请刷新页面后重试"},
            status_code=403,
        )
    path = MEDIA_DIR / MEDIA_FILES[name]
    if not path.exists():
        return JSONResponse({"ok": False, "message": "媒体文件缺失"}, status_code=404)
    # nginx internal：由 X-Accel-Redirect 转发，自动支持 Range 拖动进度条
    return Response(
        status_code=200,
        headers={"X-Accel-Redirect": f"/_media/{MEDIA_FILES[name]}",
                 "Content-Type": "video/mp4", "Accept-Ranges": "bytes",
                 "Cache-Control": "no-store"},
    )




@app.get("/api/resources/deploy-bundle")
async def resource_deploy_bundle(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse(
            {"ok": False, "code": "AUTH_REQUIRED", "message": "请先登录官网账号后再下载部署脚本包"},
            status_code=401,
        )
    clone_url = repo_info().get("clone_url", "")
    script = f"""#!/usr/bin/env bash
# CodeFlow 全栈自部署与执行器接入快速启动脚本
# 适用：Linux / macOS (4C8G 全栈 / 2C2G 执行器)
set -euo pipefail

echo "==> [1/3] 克隆 CodeFlow 开源仓库"
if [ ! -d "CodeFlow" ]; then
  git clone {clone_url}
fi
cd CodeFlow/platform

echo "==> [2/3] 构建平台镜像并拉起全栈依赖"
bash build.sh
bash bootstrap.sh

echo "==> [3/3] 平台已就绪：请访问 http://localhost:7001/register 注册首个管理员账号"
"""
    return PlainTextResponse(
        script,
        media_type="application/x-sh; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="codeflow-deploy-quickstart.sh"'},
    )


@app.post("/api/resources/trial-apply")
async def resource_trial_apply(request: Request) -> JSONResponse:
    user = get_current_user(request)
    if not user:
        return JSONResponse(
            {"ok": False, "code": "AUTH_REQUIRED", "message": "请先登录官网账号后再提交申请"},
            status_code=401,
        )
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    company = str((body or {}).get("company") or "").strip()[:120]
    scenario = str((body or {}).get("scenario") or "").strip()[:500]
    if not company:
        return JSONResponse({"ok": False, "message": "请填写团队或企业名称"}, status_code=400)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _db_lock:
        _auth_conn.execute(
            "INSERT INTO trial_applications(user_id, phone, company, scenario, created_at) VALUES(?,?,?,?,?)",
            (user["id"], user["raw_phone"], company, scenario or "私有化部署与技术支持咨询", now_iso),
        )
        _auth_conn.commit()
    return JSONResponse({
        "ok": True,
        "message": f"已登记申请（联系号码：{user['phone']}），技术团队将尽快与您对接",
    })


# 静态托管（必须最后挂载：mount("/") 会吞掉之后声明的路由）
app.mount("/", StaticFiles(directory=str(SITE), html=True), name="site")


@app.exception_handler(404)
async def not_found(request: Request, exc) -> FileResponse:
    """静态托管下未匹配路径 → 站点自己的 404 页，而不是框架默认 JSON。"""
    return FileResponse(SITE / "404.html", status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8899)
