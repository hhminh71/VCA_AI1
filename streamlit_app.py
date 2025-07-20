import streamlit as st
import google.generativeai as genai
import os

# --- CÁC HÀM TIỆN ÍCH ---

def rfile(name_file):
    """Hàm đọc nội dung từ file văn bản."""
    try:
        with open(name_file, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Lỗi: Không tìm thấy file '{name_file}'. Vui lòng kiểm tra lại đường dẫn.")
        return "" # Trả về chuỗi rỗng nếu file không tồn tại

# --- CẤU HÌNH VÀ GIAO DIỆN ---

# Cấu hình trang
st.set_page_config(page_title="Trợ lý AI", page_icon="🤖")

# Hiển thị logo (nếu có)
if os.path.exists("logo.png"):
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        st.image("logo.png", use_container_width=True)

# Hiển thị tiêu đề
title_content = rfile("00.xinchao.txt")
st.markdown(
    f"""<h1 style="text-align: center; font-size: 24px;">{title_content}</h1>""",
    unsafe_allow_html=True
)

# --- CẤU HÌNH API GEMINI ---

# Lấy Gemini API key từ st.secrets và cấu hình
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)
except (KeyError, AttributeError):
    st.error("Lỗi: Vui lòng thiết lập 'GEMINI_API_KEY' trong mục Secrets của Streamlit.")
    st.stop()


# --- KHỞI TẠO LỊCH SỬ CHAT ---

# Đọc nội dung huấn luyện từ các file
system_prompt = rfile("01.system_trainning.txt")
initial_assistant_message_content = rfile("02.assistant.txt")

# Cấu hình an toàn để giảm khả năng bị chặn
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_ONLY_HIGH",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_ONLY_HIGH",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_ONLY_HIGH",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_ONLY_HIGH",
    },
]

# Khởi tạo model Gemini với system prompt và cấu hình an toàn
model_name = 'gemini-1.5-pro' # Sử dụng model 1.5 Pro ổn định

try:
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
        safety_settings=safety_settings
    )
except Exception as e:
    st.error(f"Lỗi khởi tạo model Gemini: {e}")
    st.stop()


# Khởi tạo session state để lưu lịch sử chat
if "messages" not in st.session_state:
    # Bắt đầu lịch sử với tin nhắn chào mừng của trợ lý
    st.session_state.messages = [{"role": "assistant", "content": initial_assistant_message_content}]

# --- GIAO DIỆN CHAT ---

# CSS để tùy chỉnh giao diện tin nhắn
st.markdown(
    """
    <style>
        .assistant {
            padding: 10px;
            border-radius: 10px;
            max-width: 75%;
            background: none;
            text-align: left;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }
        .user {
            padding: 10px;
            border-radius: 10px;
            max-width: 75%;
            background: none;
            text-align: right;
            margin-left: auto;
        }
        .assistant-icon {
            font-size: 20px;
            line-height: 1.5;
        }
        .message-content {
            flex: 1;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Hiển thị lịch sử tin nhắn đã lưu
for message in st.session_state.messages:
    if message["role"] == "assistant":
        st.markdown(f'<div class="assistant"><span class="assistant-icon">🤖</span> <span class="message-content">{message["content"]}</span></div>', unsafe_allow_html=True)
    elif message["role"] == "user":
        st.markdown(f'<div class="user">{message["content"]}</div>', unsafe_allow_html=True)

# --- XỬ LÝ INPUT CỦA NGƯỜI DÙNG ---

if prompt := st.chat_input("Sếp nhập nội dung cần trao đổi ở đây nhé?"):
    # Thêm tin nhắn của người dùng vào lịch sử và hiển thị
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f'<div class="user">{prompt}</div>', unsafe_allow_html=True)

    # Chuyển đổi lịch sử sang định dạng Gemini yêu cầu (user/model)
    gemini_history = []
    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    # Bắt đầu chat session và gửi tin nhắn
    try:
        chat = model.start_chat(history=gemini_history[:-1])
        response_stream = chat.send_message(gemini_history[-1]['parts'][0], stream=True)

        # Hiển thị phản hồi của trợ lý (dạng streaming)
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                for chunk in response_stream:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            except ValueError:
                # Bắt lỗi nếu phản hồi bị chặn
                message_placeholder.markdown("⚠️ Xin lỗi, phản hồi đã bị chặn do chính sách an toàn. Vui lòng thử lại với một câu hỏi khác.")
                full_response = "⚠️ Phản hồi bị chặn." # Lưu tin nhắn lỗi vào lịch sử

        # Chỉ lưu vào lịch sử nếu phản hồi không rỗng
        if full_response:
             st.session_state.messages.append({"role": "assistant", "content": full_response})

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi gọi API của Gemini: {e}")
