import json
import io
from datetime import datetime

import streamlit as st
from openai import OpenAI

# =========================
# 0) 페이지 기본 정보
# =========================
st.set_page_config(page_title="💬 엘도라도 UNIERP Chatbot", page_icon="💬", layout="centered")

st.title("💬 Chatbot")
st.write(
    "이 앱은 OpenAI GPT 모델을 이용한 간단한 챗봇입니다. "
    "OpenAI API 키를 입력하면 바로 사용할 수 있습니다. "
    "API 키는 [여기서 발급](https://platform.openai.com/account/api-keys) 가능합니다."
)

# =========================
# 1) 사이드바: 설정 UI
# =========================
with st.sidebar:
    st.subheader("⚙️ 설정")
    openai_api_key = st.text_input("🔑 OpenAI API Key", type="password")
    model = st.selectbox(
        "🧠 모델 선택",
        options=[
            "gpt-3.5-turbo",
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-5"  # 계정/리전에 따라 사용 불가할 수 있음
        ],
        index=0,
        help="더 높은 모델일수록 품질이 좋지만 비용이 높을 수 있습니다."
    )
    temperature = st.slider("🌡️ Temperature", 0.0, 1.2, 0.7, 0.1)

# =========================
# 2) 세션 상태 초기화
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role":"user|assistant","content":"..."}]
if "summary" not in st.session_state:
    st.session_state.summary = ""   # 최근 요약 캐시

# =========================
# 3) 상단 기능 버튼들
# =========================
col1, col2, col3 = st.columns([1,1,1])

with col1:
    if st.button("🧹 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.summary = ""
        st.success("대화가 초기화되었습니다.")
        st.stop()

with col2:
    # 대화 저장(다운로드) 버튼 — JSON 파일로 내려받기
    if st.session_state.messages:
        # 파일명: chat_YYYYMMDD_HHMMSS.json
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"chat_{ts}.json"
        json_bytes = json.dumps(st.session_state.messages, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            label="💾 대화 저장 (JSON)",
            data=json_bytes,
            file_name=file_name,
            mime="application/json",
            use_container_width=True
        )
    else:
        st.button("💾 대화 저장 (JSON)", disabled=True, use_container_width=True)

with col3:
    # 대화 요약 버튼
    summarize_clicked = st.button("🧠 대화 요약", use_container_width=True)

# =========================
# 4) 기존 대화 출력
# =========================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# =========================
# 5) API 키 검사
# =========================
if not openai_api_key:
    st.info("계속하려면 OpenAI API 키를 입력하세요.", icon="🗝️")
else:
    client = OpenAI(api_key=openai_api_key)

    # -------------------------
    # (A) 대화 요약 실행
    # -------------------------
    if summarize_clicked:
        if not st.session_state.messages:
            st.warning("요약할 대화가 없습니다. 먼저 대화를 시작하세요.")
        else:
            with st.spinner("요약 중입니다..."):
                # 요약 프롬프트
                system_prompt = {
                    "role": "system",
                    "content": (
                        "당신은 전문 요약가입니다. 사용자의 전체 대화를 읽고 "
                        "핵심 요점(불릿), 결정/액션 아이템(체크박스), "
                        "추가 질문/리스크(불릿)으로 간결한 한국어 요약을 제공하세요."
                    )
                }
                # 대화 맥락을 그대로 투입
                msgs = [system_prompt] + st.session_state.messages

                try:
                    # 요약은 스트리밍이 아닌 단건 호출로
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
                    st.error(f"요약 중 오류가 발생했습니다: {e}")

    # -------------------------
    # (B) 사용자 입력 → 모델 스트리밍 응답
    # -------------------------
    if prompt := st.chat_input("무엇을 도와드릴까요?"):
        # 사용자 메시지 기록/표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 시스템 프롬프트로 어시스턴트 톤/역할 지정 (선택)
        system_prompt = {
            "role": "system",
            "content": (
                "너는 친절하고 정확한 한국어 어시스턴트야. "
                "답변은 간결한 문단과 필요한 경우 목록/코드로 정리해줘."
            )
        }

        try:
            # 지금까지의 대화 + 시스템 프롬프트를 모델에 투입
            stream = client.chat.completions.create(
                model=model,
                messages=[system_prompt] + [
                    {"role": m["role"], "content": m["content"]}
