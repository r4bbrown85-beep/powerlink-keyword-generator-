# -*- coding: utf-8 -*-
import streamlit as st
import os, hashlib, time, datetime
from pathlib import Path

_TIMEOUT = 7200   # 세션 타임아웃: 2시간
_LOG_DIR = Path(__file__).parent.parent / "logs"


def _get_pw_hash() -> str:
    raw = os.environ.get("APP_PASSWORD", "")
    if not raw:
        try:
            raw = st.secrets.get("APP_PASSWORD", "")
        except Exception:
            pass
    return hashlib.sha256(str(raw).encode()).hexdigest()


def _get_ip() -> str:
    try:
        hdrs = st.context.headers
        return hdrs.get("X-Forwarded-For", hdrs.get("X-Real-Ip", "unknown"))
    except Exception:
        return "unknown"


def _log(event: str, detail: str = ""):
    _LOG_DIR.mkdir(exist_ok=True)
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    day = datetime.date.today().strftime("%Y%m%d")
    line = f"[{ts}] {event}"
    if detail:
        line += f" | {detail}"
    with open(_LOG_DIR / f"access_{day}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check_auth():
    """앱 최상단에서 호출 — 미인증 시 로그인 화면 표시 후 st.stop()"""
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
        st.session_state.last_ts = 0.0

    if st.session_state.auth_ok:
        if time.time() - st.session_state.last_ts > _TIMEOUT:
            st.session_state.auth_ok = False
            _log("SESSION_TIMEOUT", f"ip={_get_ip()}")
        else:
            st.session_state.last_ts = time.time()
            return   # 인증 유효 → 앱 계속 실행

    # ── 로그인 화면 ──────────────────────────────────────────────────────
    st.markdown("""
<div style="max-width:380px;margin:80px auto;text-align:center;">
  <div style="font-size:2.2rem;margin-bottom:8px;">⚡</div>
  <div style="font-size:1.3rem;font-weight:700;color:#111827;margin-bottom:4px;">
    PowerLink Planner
  </div>
  <div style="font-size:0.85rem;color:#6B7280;margin-bottom:28px;">
    팀 비밀번호를 입력하세요
  </div>
</div>
""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("_auth_form", clear_on_submit=True):
            pw = st.text_input(
                "비밀번호", type="password",
                label_visibility="collapsed",
                placeholder="비밀번호 입력"
            )
            ok = st.form_submit_button("로그인", use_container_width=True, type="primary")

        if ok:
            ip = _get_ip()
            if pw and hashlib.sha256(pw.encode()).hexdigest() == _get_pw_hash():
                st.session_state.auth_ok = True
                st.session_state.last_ts = time.time()
                _log("LOGIN_SUCCESS", f"ip={ip}")
                st.rerun()
            else:
                _log("LOGIN_FAIL", f"ip={ip}")
                st.error("비밀번호가 틀렸습니다.")

    st.stop()


def log_action(event: str, detail: str = ""):
    """다운로드·주요 액션 기록 (외부에서 호출)"""
    _log(event, f"ip={_get_ip()} | {detail}" if detail else f"ip={_get_ip()}")
