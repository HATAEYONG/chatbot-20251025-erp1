import json
from datetime import datetime
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="💬 Chatbot", page_icon="💬")

st.title("💬 엘도라도 Chatbot with Memory, Summary & Reset")
st.write(
    "이 앱은 OpenAI GPT 모델을 이용한 간단한 챗봇입니다. "
    "API 키를 입력 후 대화를 시작하세요."
)

with st.sidebar:
    st.subheader("⚙️ 설정")
    openai_api_key = st.text_input("🔑 OpenAI API Key", type="password")
    model = st.selectbox("🧠 모델 선택", ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o", "gpt-5"], index=0)
    temperature = st.slider("🌡️ Temperature", 0.0, 1.2, 0.7, 0.1)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "summary" not in st.session_state:
    st.session_state.summary = ""

col1, col2, col3 = st.columns([1,1,1])

with col1:
    if st.button("🧹 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.summary = ""
        st.success("대화가 초기화되었습니다.")
        st.stop()

with col2:
    if st.session_state.messages:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"chat_{ts}.json"
        st.download_button(
            label="💾 대화 저장 (JSON)",
            data=json.dumps(st.session_state.messages, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=fname,
            mime="application/json",
            use_container_width=True
        )
    else:
        st.button("💾 대화 저장 (JSON)", disabled=True, use_container_width=True)

with col3:
    summarize_clicked = st.button("🧠 대화 요약", use_container_width=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if not openai_api_key:
    st.info("OpenAI API 키를 입력하세요.", icon="🗝️")
else:
    client = OpenAI(api_key=openai_api_key)

    if summarize_clicked:
        if not st.session_state.messages:
            st.warning("요약할 대화가 없습니다.")
        else:
            with st.spinner("요약 중..."):
                sys_prompt = {
                    "role": "system",
                    "content": "너는 대화를 요약하는 전문가야. 핵심 내용과 결론을 간결히 요약해줘."
                }
                msgs = [sys_prompt] + st.session_state.messages
                comp = client.chat.completions.create(
                    model=model,
                    messages=msgs,
                    temperature=temperature,
                )
                summary_text = comp.choices[0].message.content.strip()
                st.session_state.summary = summary_text
                with st.expander("🧾 요약 결과", expanded=True):
                    st.markdown(summary_text)

    if prompt := st.chat_input("무엇을 도와드릴까요?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        system_prompt = {
            "role": "system",
            "content": "너는 친절한 한국어 어시스턴트야. 간결하고 이해하기 쉽게 대답해줘."
        }

        stream = client.chat.completions.create(
            model=model,
            messages=[system_prompt] + [   # ✅ 괄호 완전히 닫음
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],                             # ✅ 닫는 대괄호 추가
            temperature=temperature,
            stream=True,
        )

        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
