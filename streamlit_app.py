import streamlit as st
from openai import OpenAI

# -----------------------------
# 1️⃣ 페이지 제목 및 설명
# -----------------------------
st.title("💬  UNIERP Chatbot")
st.write(
    "이 앱은 OpenAI의 GPT 모델을 이용한 간단한 챗봇입니다. "
    "OpenAI API 키를 입력하면 바로 사용할 수 있습니다. "
    "API 키는 [여기서 발급](https://platform.openai.com/account/api-keys) 가능합니다."
)

# -----------------------------
# 2️⃣ API Key 입력 받기
# -----------------------------
openai_api_key = st.text_input("🔑 OpenAI API Key", type="password")

if not openai_api_key:
    st.info("계속하려면 OpenAI API 키를 입력하세요.", icon="🗝️")

else:
    # -----------------------------
    # 3️⃣ OpenAI 클라이언트 생성
    # -----------------------------
    client = OpenAI(api_key=openai_api_key)

    # -----------------------------
    # 4️⃣ 세션 상태 초기화
    # -----------------------------
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # -----------------------------
    # 5️⃣ 🧹 대화 초기화 버튼 추가
    # -----------------------------
    if st.button("🧹 대화 초기화"):
        st.session_state.messages = []
        st.success("대화가 초기화되었습니다!")
        st.stop()  # 이후 코드 실행 중지 (화면 새로고침처럼 작동)

    # -----------------------------
    # 6️⃣ 이전 대화 출력
    # -----------------------------
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # -----------------------------
    # 7️⃣ 사용자 입력 처리
    # -----------------------------
    if prompt := st.chat_input("무엇을 도와드릴까요?"):
        # 사용자 입력 저장 및 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # -----------------------------
        # 8️⃣ GPT 응답 생성
        # -----------------------------
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )

        # 응답 출력 및 저장
        with st.chat_message("assistant"):
            response = st.write_stream(stream)

        st.session_state.messages.append({"role": "assistant", "content": response})
