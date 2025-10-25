import json
from datetime import datetime

import streamlit as st
from openai import OpenAI

# =========================
# 0) 페이지 기본 정보
# =========================
st.set_page_config(page_title="💬 Chatbot", page_icon="💬", layout="centered")

st.title("💬 Chatbot with Reset · Save · Summary · Restore")
st.write(
    "OpenAI GPT 모델로 동작하는 간단한 챗봇입니다. "
    "API 키 입력 후 대화를 시작하세요. "
    "대화를 JSON으로 저장/복원할 수 있습니다."
)

# ---------- 유틸: 메시지 형식 검증 ----------
def _is_valid_messages(data) -> bool:
    """messages 구조 유효성 검사: List[{'role': 'user'|'assistant'|'system', 'content': str}]"""
    if not isinstance(data, list):
        return False
    for i, m in enumerate(data):
        if not isinstance(m, dict):
            return False
        if "role" not in m or "content" not in m:
            return False
        if m["role"] not in {"user", "assistant", "system"}:
            return False
        if not isinstance(m["content"], str):
            return False
    return True

# =========================
# 1) 사이드바: 설정 & 복원
# =========================
with st.sidebar:
    st.subheader("⚙️ 설정")
    openai_api_key = st.text_input("🔑 OpenAI API Key", type="password")
    model = st.selectbox(
        "🧠 모델 선택",
        ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o", "gpt-5"],
        index=0,
        help="상위 모델일수록 품질↑ (비용 주의)"
    )
    temperature = st.slider("🌡️ Temperature", 0.0, 1.2, 0.7, 0.1)

    st.markdown("---")
    st.subheader("📤 대화 복원 (JSON 업로드)")
    uploaded = st.file_uploader("JSON 파일 선택", type=["json"], help="이전에 저장한 chat_*.json 파일")
    restore_mode = st.radio(
        "복원 방식",
        ["▶ 교체(현재 대화 덮어쓰기)", "➕ 병합(현재 뒤에 이어붙이기)"],
        index=0,
        help="교체: 현재 대화가 모두 대체됨 / 병합: 업로드 내용이 뒤에 추가됨"
    )
    if uploaded is not None:
        try:
            loaded_data = json.load(uploaded)
            preview_count = len(loaded_data) if isinstance(loaded_data, list) else 0
            st.caption(f"미리보기: {preview_count}개 메시지 감지")
            do_restore = st.button("⏪ 이 JSON으로 복원")
        except Exception as e:
            st.error(f"JSON 파싱 실패: {e}")
            loaded_data, do_restore = None, False
    else:
        loaded_data, do_restore = None, False

# =========================
# 2) 세션 상태
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []   # [{"role": "...", "content": "..."}]
if "summary" not in st.session_state:
    st.session_state.summary = ""    # 요약 캐시

# ----- 업로드 복원 처리 -----
if do_restore:
    if not _is_valid_messages(loaded_data):
        st.error("올바른 messages 형식이 아닙니다. [{'role':..., 'content':...}, ...] 리스트여야 합니다.")
    else:
        if restore_mode.startswith("▶"):
            st.session_state.messages = loaded_data
            st.success("✅ 업로드한 JSON으로 **교체** 복원했습니다.")
        else:
            st.session_state.messages.extend(loaded_data)
            st.success("✅ 업로드한 JSON을 **병합**했습니다.")
        st.session_state.summary = ""  # 복원 후 요약은 초기화
        st.experimental_rerun()

# =========================
# 3) 상단 기능 버튼들
# =========================
col1, col2, col3, col4 = st.columns([1,1,1,1])

with col1:
    if st.button("🧹 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.summary = ""
        st.success("대화가 초기화되었습니다.")
        st.stop()

with col2:
    # 저장(다운로드)
    if st.session_state.messages:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"chat_{ts}.json"
        data_bytes = json.dumps(st.session_state.messages, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            label="💾 대화 저장 (JSON)",
            data=data_bytes,
            file_name=fname,
            mime="application/json",
            use_container_width=True
        )
    else:
        st.button("💾 대화 저장 (JSON)", disabled=True, use_container_width=True)

with col3:
    summarize_clicked = st.button("🧠 대화 요약", use_container_width=True)

with col4:
    if st.session_state.summary:
        st.button("🧾 요약 보기", disabled=True, use_container_width=True)
    else:
        st.button("🧾 요약 보기", disabled=True, use_container_width=True)

# =========================
# 4) 기존 대화 출력
# =========================
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# =========================
# 5) API 키 검사 & 기능 동작
# =========================
if not openai_api_key:
    st.info("계속하려면 OpenAI API 키를 입력하세요.", icon="🗝️")
else:
    client = OpenAI(api_key=openai_api_key)

    # (A) 요약
    if summarize_clicked:
        if not st.session_state.messages:
            st.warning("요약할 대화가 없습니다. 먼저 대화를 시작하세요.")
        else:
            with st.spinner("요약 중입니다..."):
                system_prompt = {
                    "role": "system",
                    "content": (
                        "당신은 전문 요약가입니다. 사용자의 전체 대화를 읽고 "
                        "핵심 요점(불릿), 결정/액션 아이템(체크박스), "
                        "추가 질문/리스크(불릿)으로 간결한 한국어 요약을 제공하세요."
                    )
                }
                msgs = [system_prompt] + st.session_state.messages
                try:
                    comp = client.chat.completions.create(
                        model=model,
                        messages=msgs,
                        temperature=temperature,
                    )
                    summary_text = comp.choices[0].message.content.strip()
                    st.session_state.summary = summary_text
                    with st.expander("🧾 요약 결과 펼치기", expanded=True):
                        st.markdown(summary_text)
                except Exception as e:
                    st.error(f"요약 중 오류: {e}")

    # (B) 사용자 입력 → 스트리밍 응답
    if prompt := st.chat_input("무엇을 도와드릴까요?"):
        # 사용자 메시지 기록/표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 시스템 프롬프트(선택)
        system_prompt = {
            "role": "system",
            "content": (
                "너는 친절하고 정확한 한국어 어시스턴트야. "
                "답변은 간결한 문단과 필요한 경우 목록/코드로 정리해줘."
            )
        }

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[system_prompt] + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                temperature=temperature,
                stream=True,
            )
            with st.chat_message("assistant"):
                response_text = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
        except Exception as e:
            st.error(f"응답 생성 중 오류: {e}")
