import streamlit as st
import subprocess
import os
import sys
import pandas as pd
import time
import google.generativeai as genai
import random
import math
from PIL import Image
import io

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Ultimate Code Judge",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS MAGIC (GIAO DIỆN) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap');
    .stApp { background-color: #09090b; color: #e4e4e7; font-family: 'Inter', sans-serif; }
    .gradient-text {
        background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 900; font-size: 3.5rem; text-align: center;
        letter-spacing: -2px; margin-bottom: 10px;
        text-shadow: 0 0 30px rgba(79, 172, 254, 0.3);
    }
    .stTextArea textarea {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #18181b !important; color: #a1a1aa !important;
        border: 1px solid #27272a !important; border-radius: 12px;
    }
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        color: white; border: none; height: 45px; font-weight: bold;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; background-color: #18181b; border-radius: 8px;
        border: 1px solid #27272a; color: #a1a1aa; flex-grow: 1;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(37, 99, 235, 0.1) !important;
        border: 1px solid #3b82f6 !important; color: #60a5fa !important;
    }
    .ticker-wrap {
        width: 100%; background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 50px;
        overflow: hidden; margin-bottom: 20px; height: 40px;
        display: flex; align-items: center;
        box-shadow: 0 0 10px rgba(0, 210, 255, 0.1);
    }
    .ticker {
        display: inline-block; white-space: nowrap; padding-left: 100%;
        animation: ticker-scroll 30s linear infinite;
    }
    .ticker-item {
        display: inline-block; padding: 0 2rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.9rem;
        color: #00d2ff; text-shadow: 0 0 5px #00d2ff;
    }
    @keyframes ticker-scroll {
        0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 👇👇👇 CẤU HÌNH API KEY 👇👇👇
try:
    if "GEMINI_KEYS" in st.secrets:
        API_KEYS = st.secrets["GEMINI_KEYS"]
    else:
        API_KEYS = ["AIzaSyCmcoftGYbQIYo7itPnUyoJQscOSVHgvYI", "AIzaSyDFrOOQAyUFqENMyVoZ8gEeis_-9VYpxDw"]
except FileNotFoundError:
    API_KEYS = ["AIzaSyCmcoftGYbQIYo7itPnUyoJQscOSVHgvYI", "AIzaSyDFrOOQAyUFqENMyVoZ8gEeis_-9VYpxDw"]
# ==============================================================================

def get_random_key():
    valid_keys = [k for k in API_KEYS if "PASTE" not in k and len(k) > 10]
    if not valid_keys: return None
    return random.choice(valid_keys)

CPP_FILENAME = "solution.cpp"
EXE_FILENAME = "solution.exe" if os.name == 'nt' else "./solution"

# --- 3. KHỞI TẠO BỘ NHỚ ---
if 'python_logic' not in st.session_state:
    st.session_state['python_logic'] = """used_inputs = set()
def generate_input(): return "10 20"
def solve_reference(s): return "30" """
if 'logic_status' not in st.session_state: st.session_state['logic_status'] = "Chưa khởi tạo"
if 'failed_cases' not in st.session_state: st.session_state['failed_cases'] = []
if 'cpp_code_content' not in st.session_state:
    st.session_state['cpp_code_content'] = """#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false); 
    cin.tie(NULL);
    
    // Code của bạn tại đây...
    
    return 0;
}"""
if 'reference_code' not in st.session_state: st.session_state['reference_code'] = ""
if 'ai_fix_result' not in st.session_state: st.session_state['ai_fix_result'] = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "Chào Sếp! Cần hỗ trợ gì về C++ không ạ?"}]
if 'current_image' not in st.session_state: st.session_state['current_image'] = None
if 'problem_text_input' not in st.session_state: st.session_state['problem_text_input'] = ""
if 'chat_pasted_image' not in st.session_state: st.session_state['chat_pasted_image'] = None
if 'refine_request' not in st.session_state: st.session_state['refine_request'] = ""

# --- 4. HÀM XỬ LÝ AI ---
def configure_ai():
    key = get_random_key()
    if not key: return False
    genai.configure(api_key=key)
    return True

def stream_ai_response(prompt_text, image=None):
    if not configure_ai(): 
        yield "❌ Lỗi: Chưa nhập API Key."
        return
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        content = [prompt_text]
        if image: content.append(image)
        response = model.generate_content(content, stream=True)
        for chunk in response:
            if chunk.text: yield chunk.text
    except Exception as e: yield f"❌ Lỗi kết nối AI: {str(e)}"

def get_ai_test_logic(problem_text, image=None):
    if not configure_ai(): 
        st.error("❌ Chưa cấu hình API Key!")
        return None
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Role: Senior QA Engineer. Task: Write Python test generator for: {problem_text}.
        STRICT DATA DISTRIBUTION RULE (50/50 SPLIT):
        1. Roll a random chance `r = random.random()`.
        2. **IF r < 0.5 (50% Chance)**: Generate input strictly in Range **[1, 9999]**.
        3. **ELSE (50% Chance)**: Generate input strictly in Range **[10000, 1000000]**.
        General Rules: Ensure `used_inputs` is global. Return strictly valid inputs.
        FUNCTION SIGNATURES: `generate_input()` -> str, `solve_reference(input_str)` -> str.
        OUTPUT: ONLY PYTHON CODE. NO MARKDOWN.
        """
        content = [prompt]
        if image: content.append(image)
        response = model.generate_content(content)
        return response.text.replace("```python", "").replace("```", "").strip()
    except Exception as e:
        st.error(f"🔥 LỖI CHI TIẾT TỪ GOOGLE: {str(e)}")
        return None

def extract_text_from_image(image):
    if not configure_ai(): return None
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = "Extract all text from this image exactly. Output text only."
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except: return None

# --- 5. CALLBACK HANDLERS ---
def on_click_solve():
    uploaded_file = st.session_state.get('img_uploader')
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.session_state['current_image'] = img
        extracted_text = extract_text_from_image(img)
        if extracted_text and "Error" not in extracted_text:
            st.session_state['problem_text_input'] = extracted_text
            st.toast("Đã đọc xong đề bài!", icon="📝")
    
    final_text = st.session_state.get('problem_text_input', "")
    cur_img = st.session_state.get('current_image')

    if not final_text and not cur_img:
        st.toast("Thiếu đề bài (Text/Ảnh)!", icon="⚠️")
        return

    nc = get_ai_test_logic(final_text if final_text else "", cur_img)
    if nc:
        st.session_state['python_logic'] = nc
        st.session_state['logic_status'] = "✅ Đã nạp Logic"
        st.session_state['failed_cases'] = []
        st.session_state['reference_code'] = ""
        st.session_state['ai_fix_result'] = ""
        st.toast("Sẵn sàng chiến đấu!", icon="🔥")
    else:
        st.toast("Lỗi AI Logic", icon="❌")

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ Cấu hình")
    with st.container(border=True):
        num_tests = st.slider("Số lượng Test:", 10, 500, 50)
        time_limit = st.slider("Giới hạn thời gian (s):", 0.1, 3.0, 1.0)
    
    st.write("###")
    with st.container(border=True):
        status = st.session_state.get('logic_status', 'Chưa khởi tạo')
        if "sẵn" in status or "Logic" in status: st.success(status, icon="✅")
        else: st.info(status, icon="ℹ️")
        active_keys = len([k for k in API_KEYS if "PASTE" not in k and len(k) > 10])
        st.caption(f"🔑 Phím: **{active_keys}** | ⚡ Model: **Gemini 2.0**")

    st.write("---") 
    
    # CHATBOT (VIỆT HÓA 100%)
    with st.popover("💬 Trợ lý ảo (Click để chat)", use_container_width=True):
        st.markdown("### 🤖 Trợ lý Lập trình")
        messages_container = st.container(height=300)
        with messages_container:
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
        st.write("---")
        
        up_chat = st.file_uploader("📂 Tải ảnh lên (để hỏi AI)", type=["png","jpg"], key="chat_up")
        if up_chat: st.session_state['chat_pasted_image'] = Image.open(up_chat)

        if st.session_state['chat_pasted_image']:
            st.image(st.session_state['chat_pasted_image'], width=150, caption="Ảnh đính kèm")
            if st.button("❌ Xóa ảnh", key="del_chat_img"): 
                st.session_state['chat_pasted_image'] = None; st.rerun()

        if prompt := st.chat_input("Hỏi AI...", key="chat_popover_input"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with messages_container:
                st.chat_message("user").write(prompt)
                if st.session_state['chat_pasted_image']: st.image(st.session_state['chat_pasted_image'], width=200)
            
            curr_prob = st.session_state.get('problem_text_input', "")
            curr_code = st.session_state.get('cpp_code_content', "")
            curr_ref = st.session_state.get('reference_code', "")
            
            # --- PROMPT VIỆT HÓA ---
            full_prompt = f"""
            Role: C++ Tutor (Vietnamese Speaker).
            CONTEXT:
            1. PROBLEM: {curr_prob}
            2. USER CODE: {curr_code}
            3. REFERENCE CODE: {curr_ref}
            USER QUESTION: {prompt}
            INSTRUCTION: Answer strictly in VIETNAMESE (Tiếng Việt). Explain clearly.
            """
            
            with messages_container:
                with st.chat_message("assistant"):
                    res = st.empty(); full = ""
                    for ch in stream_ai_response(full_prompt, image=st.session_state['chat_pasted_image']):
                        full += ch; res.write(full)
            st.session_state.chat_history.append({"role": "assistant", "content": full})
            st.session_state['chat_pasted_image'] = None; st.rerun()

# --- 7. GIAO DIỆN CHÍNH ---
st.markdown("<div class='gradient-text'>ULTIMATE CODE JUDGE</div>", unsafe_allow_html=True)

st.markdown("""
<div class="ticker-wrap">
    <div class="ticker">
        <div class="ticker-item">🚀 SYSTEM READY: Gemini 2.0 Flash Connected</div>
        <div class="ticker-item">⚡ TIPS: Kéo thả ảnh vào khung Upload để nạp đề nhanh</div>
        <div class="ticker-item">🛡️ STATUS: Auto Judge Online</div>
        <div class="ticker-item">🤖 DEV: Nguyen Huy Dung</div>
    </div>
</div>
""", unsafe_allow_html=True)

# === KHUNG NHẬP LIỆU CHÍNH ===
with st.container(border=True):
    c1, c2 = st.columns([4, 1]) 
    with c1:
        st.markdown("#### 📝 Nội dung đề bài")
        st.text_area("Input", height=250, placeholder="Nhập đề bài hoặc Kéo thả ảnh bên phải ->", 
                     label_visibility="collapsed", key="problem_text_input")
    
    with c2:
        st.markdown("#### 🖼️ Ảnh đề bài")
        st.file_uploader("Chọn file ảnh", type=["png", "jpg"], label_visibility="collapsed", key="img_uploader")

        if st.session_state.get('current_image'):
            st.image(st.session_state['current_image'], width=200, caption="Đề bài đang chọn")
            if st.button("🗑️ Xóa ảnh", use_container_width=True):
                st.session_state['current_image'] = None
                st.rerun()

    st.write("") 
    b1, b2, b3 = st.columns([1, 1, 2])
    
    with b1:
        st.button("🚀 NẠP ĐỀ BÀI", type="primary", use_container_width=True, on_click=on_click_solve)
            
    with b2:
        if st.button("💡 Gợi ý Code", type="secondary", use_container_width=True):
            if st.session_state.get('problem_text_input') or st.session_state.get('current_image'):
                st.session_state['reference_code'] = ""
                st.session_state['show_solution_stream'] = True
                st.rerun()
            else: st.toast("Chưa có đề!", icon="⚠️")
    with b3:
        status = st.session_state.get('logic_status', 'Chưa khởi tạo')
        st.markdown(f"<div style='text-align: right; padding-top: 10px; opacity: 0.7;'>Status: <b>{status}</b></div>", unsafe_allow_html=True)

# --- STREAMING SOLUTION (VIỆT HÓA) ---
if st.session_state.get('show_solution_stream'):
    st.info("💡 **AI đang viết code mẫu...**")
    sol_text = st.session_state.get('problem_text_input', "")
    sol_img = st.session_state.get('current_image')
    
    refine_req = st.session_state.get('refine_request', "")
    
    # --- PROMPT VIỆT HÓA ---
    if refine_req:
        prompt_sol = f"""
        Role: CP Expert (Vietnamese). 
        Task: REWRITE the solution for this C++ problem.
        Problem: {sol_text}
        USER REQUIREMENT: {refine_req}
        Rules: 
        1. Optimize O2. 
        2. Add comments in VIETNAMESE. 
        3. Output only Code.
        """
    else:
        prompt_sol = f"Role: CP Expert. Solve C++: {sol_text}. Optimize O2. Comments in VIETNAMESE. Code only."
    
    container = st.empty(); full_res = ""
    for chunk in stream_ai_response(prompt_sol, image=sol_img):
        full_res += chunk
        container.code(full_res.replace("```cpp","").replace("```",""), language='cpp')
    
    st.session_state['reference_code'] = full_res.replace("```cpp","").replace("```","").strip()
    st.session_state['show_solution_stream'] = False
    st.session_state['refine_request'] = ""
    st.rerun()

if st.session_state['reference_code'] and not st.session_state.get('show_solution_stream'):
    with st.expander("💡 Code Tham Khảo (Click để xem)", expanded=False):
        st.code(st.session_state['reference_code'], language='cpp')
        
        st.markdown("---")
        st.markdown("#### 🛠️ Tùy chỉnh Code mẫu")
        c_refine_1, c_refine_2 = st.columns([3, 1])
        with c_refine_1:
            user_refine = st.text_input("Nhập yêu cầu (VD: Dùng vòng lặp while, Dùng đệ quy...)", key="input_refine")
        with c_refine_2:
            st.write("")
            st.write("")
            if st.button("✨ Viết lại ngay"):
                if user_refine:
                    st.session_state['refine_request'] = user_refine
                    st.session_state['show_solution_stream'] = True
                    st.rerun()
                else:
                    st.toast("Hãy nhập yêu cầu trước!", icon="⚠️")

# --- EDITOR & TABS ---
st.write("###")
st.markdown("### 💻 Code Editor")
st.text_area("Editor", height=450, key="cpp_code_content", label_visibility="collapsed")

tab1, tab2, tab3, tab4 = st.tabs(["🚀 CHẤM TỰ ĐỘNG", "🧪 TEST TÙY CHỈNH", "📊 PHÂN TÍCH", "🧩 SƠ ĐỒ & REVIEW"])

# === TAB 1: AUTO JUDGE ===
with tab1:
    if st.button("🔥 CHẤM BÀI NGAY", type="primary", use_container_width=True):
        st.session_state['ai_fix_result'] = ""
        with open(CPP_FILENAME, "w", encoding="utf-8") as f: f.write(st.session_state['cpp_code_content'])
        
        cmd = ["g++", "-O2", CPP_FILENAME, "-o", "solution"]
        with st.status("⚙️ Đang biên dịch & chạy test...", expanded=True) as status:
            ret = subprocess.run(cmd, capture_output=True, text=True)
            if ret.returncode != 0:
                status.update(label="Lỗi biên dịch!", state="error")
                st.error(ret.stderr)
            else:
                exec_env = {"random": random, "math": math, "sys": sys, "used_inputs": set()}
                try:
                    exec(st.session_state['python_logic'], exec_env)
                    gen_in = exec_env['generate_input']; solve_ref = exec_env['solve_reference']
                    exec_env['used_inputs'] = set()
                    
                    results = []; correct = 0; failed_log = []
                    p_bar = st.progress(0); start_t = time.time()
                    
                    for i in range(num_tests):
                        inp = str(gen_in()); exp = str(solve_ref(inp)).strip()
                        try:
                            p = subprocess.Popen([EXE_FILENAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            out, err = p.communicate(input=inp, timeout=time_limit)
                            got = out.strip()
                            stat = "✅" if got == exp else "❌"
                            if stat == "✅": correct += 1
                            else: failed_log.append(f"Case {i+1}: In='{inp}' | Exp='{exp}' | Got='{got}'")
                        except subprocess.TimeoutExpired: 
                            p.kill(); stat = "⏳"; failed_log.append(f"Case {i+1}: TLE")
                        except Exception as e: stat = "⚠️"
                        
                        results.append({"Test": i+1, "Input": inp, "Exp": exp, "Got": got, "Status": stat})
                        if i % 5 == 0: p_bar.progress((i+1)/num_tests)
                    
                    p_bar.progress(100)
                    status.update(label="Hoàn tất!", state="complete", expanded=False)
                    st.session_state['failed_cases'] = failed_log
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Kết quả", f"{correct}/{num_tests}", delta_color="normal")
                    acc = correct/num_tests*100
                    m2.metric("Độ chính xác", f"{acc:.1f}%", delta=f"{acc-100:.1f}%" if acc<100 else "Perfect")
                    m3.metric("Thời gian", f"{time.time()-start_t:.2f}s")
                    
                    if correct == num_tests: st.balloons(); st.success("TUYỆT VỜI! FULL AC! 🎉")
                    else: st.error(f"Sai {num_tests-correct} test. Kiểm tra lại nhé!")

                    df = pd.DataFrame(results)
                    st.dataframe(df, use_container_width=True, height=400, hide_index=True)
                except Exception as e: st.error(f"Lỗi Logic Python: {e}")

# === TAB 2: CUSTOM TEST ===
with tab2:
    c_in, c_out = st.columns(2)
    with c_in: cust_in = st.text_area("Input Tùy chỉnh", height=150)
    with c_out: 
        st.write("Output:"); cust_out = st.empty()
    
    if st.button("Kiểm tra thử"):
        with open(CPP_FILENAME, "w", encoding="utf-8") as f: f.write(st.session_state['cpp_code_content'])
        subprocess.run(["g++", "-O2", CPP_FILENAME, "-o", "solution"])
        try:
            p = subprocess.Popen([EXE_FILENAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = p.communicate(input=cust_in, timeout=time_limit)
            cust_out.code(out)
        except Exception as e: cust_out.error(e)

# === TAB 3: PHÂN TÍCH (VIỆT HÓA) ===
with tab3:
    if st.button("🔍 Phân tích Độ phức tạp"):
        # --- PROMPT VIỆT HÓA ---
        prompt = f"Analyze Big-O complexity briefly in VIETNAMESE:\n{st.session_state['cpp_code_content']}"
        cont = st.empty(); full=""
        for ch in stream_ai_response(prompt): full+=ch; cont.markdown(full)

# === TAB 4: CÔNG CỤ MỞ RỘNG (VIỆT HÓA) ===
with tab4:
    st.write("###")
    c_t4_1, c_t4_2, c_t4_3 = st.columns(3)
    
    # --- 1. VẼ SƠ ĐỒ ---
    with c_t4_1:
        st.markdown("#### 🗺️ Sơ đồ luồng")
        btn_chart = st.button("🎨 Vẽ Flowchart", use_container_width=True)

    # --- 2. REVIEW CODE ---
    with c_t4_2:
        st.markdown("#### ⚔️ Review Code")
        btn_review = st.button("🧐 Chấm điểm", use_container_width=True)

    # --- 3. CHUYỂN ĐỔI NGÔN NGỮ ---
    with c_t4_3:
        st.markdown("#### 🔄 Chuyển Ngôn ngữ")
        target_lang = st.selectbox("Đích:", ["Python", "Java", "JavaScript", "Go"], label_visibility="collapsed")
        btn_convert = st.button(f"⚡ Chuyển sang {target_lang}", use_container_width=True)

    # 1. XỬ LÝ VẼ SƠ ĐỒ
    if btn_chart:
        st.markdown("---")
        if not st.session_state['cpp_code_content']:
            st.warning("Thiếu code!")
        else:
            with st.spinner("🎨 Đang vẽ sơ đồ..."):
                prompt_chart = f"""
                Generate Graphviz DOT code for this C++ code.
                Labels must be concise.
                Code:
                {st.session_state['cpp_code_content']}
                Output only DOT code inside ```dot block.
                """
                dot_code = ""
                for chunk in stream_ai_response(prompt_chart): dot_code += chunk
                try: 
                    st.graphviz_chart(dot_code.replace("```dot", "").replace("```", "").strip())
                except: st.error("Lỗi hiển thị.")

    # 2. XỬ LÝ REVIEW CODE (ĐÃ SỬA LỖI LẶP)
    # 2. XỬ LÝ REVIEW CODE (GIAO DIỆN ĐẸP + KHÔNG LẶP)
    if btn_review:
        st.markdown("---")
        if not st.session_state['cpp_code_content']:
            st.warning("Thiếu code!")
        else:
            with st.spinner("🧐 Đang soi code..."):
                # 👇👇👇 PROMPT NÂNG CẤP GIAO DIỆN 👇👇👇
                prompt_rev = f"""
                Role: Senior C++ Developer.
                Task: Review code strictly in VIETNAMESE.
                
                REQUIREMENTS:
                - Use clear Markdown formatting.
                - Use Emojis (✅, ⚠️, 💡, 🚀) for bullet points.
                - Add horizontal rules (---) to separate sections.
                - NO conversational filler.
                
                Code:
                {st.session_state['cpp_code_content']}
                
                OUTPUT FORMAT:
                ## 📊 KẾT QUẢ ĐÁNH GIÁ: [Điểm số]/100
                
                ### ✅ Ưu điểm
                - (Liệt kê...)
                
                ### ⚠️ Vấn đề & Rủi ro
                - (Liệt kê...)
                
                ### 💡 Đề xuất tối ưu
                (Giải thích ngắn gọn...)
                
                ### 🚀 Code mẫu (Clean Code)
                ```cpp
                // Code đã sửa
                ```
                """
                
                # Tạo container có viền để làm nổi bật phần Review
                cont_rev = st.container(border=True)
                review_placeholder = cont_rev.empty()
                
                full_rev = ""
                for chunk in stream_ai_response(prompt_rev):
                    full_rev += chunk
                    review_placeholder.markdown(full_rev)
    # 3. XỬ LÝ CHUYỂN ĐỔI NGÔN NGỮ (VIỆT HÓA)
    if btn_convert:
        st.markdown("---")
        if not st.session_state['cpp_code_content']:
            st.warning("Thiếu code nguồn!")
        else:
            st.subheader(f"🚀 Kết quả chuyển đổi sang {target_lang}")
            with st.spinner(f"Đang dịch sang {target_lang}..."):
                prompt_conv = f"""
                Role: Polyglot Programmer.
                Task: Convert this C++ code to {target_lang}.
                REQUIREMENTS:
                1. Keep the same logic.
                2. Add comments explaining the changes in VIETNAMESE (Tiếng Việt).
                3. Output ONLY the code block.
                Code:
                {st.session_state['cpp_code_content']}
                """
                cont_conv = st.container()
                full_conv = ""
                for chunk in stream_ai_response(prompt_conv):
                    full_conv += chunk
                    clean_view = full_conv.replace(f"```{target_lang.lower()}", "").replace("```", "")
                    cont_conv.code(clean_view, language=target_lang.lower())

# --- 8. AI FIXER (VIỆT HÓA) ---
if st.session_state.get('failed_cases'):
    st.markdown("---")
    st.subheader("🆘 Trợ lý Debug (AI Fixer)")
    
    with st.container(border=True):
        user_hint = st.text_input("💡 Gợi ý cho AI (nếu bạn nghi ngờ lỗi ở đâu):", 
                                  placeholder="Ví dụ: Sai ở vòng lặp for, hoặc tràn số...")
        
        detail_mode = st.checkbox("✅ Giải thích chi tiết nguyên nhân", value=True)

        if st.button("🤖 Phân tích & Sửa Code", type="primary", use_container_width=True):
            curr_txt = st.session_state.get('problem_text_input', "")
            prob = curr_txt if curr_txt else "Check context image"
            
            instruction = "Explain the bug briefly in VIETNAMESE."
            if detail_mode:
                instruction = """
                Analyze deeply. 
                1. Identify the EXACT cause of the error.
                2. Point out the specific line numbers.
                3. Explain WHY your fix works.
                4. Provide the FULL corrected code.
                Strictly in VIETNAMESE.
                """
            
            hint_prompt = f"USER HINT: {user_hint}" if user_hint else ""

            prompt_fix = f"""
            Role: Expert C++ Debugger.
            CONTEXT:
            - PROBLEM: {prob}
            - CURRENT CODE:
            {st.session_state['cpp_code_content']}
            - FAILED TEST CASES:
            {' '.join(st.session_state['failed_cases'][:3])}
            {hint_prompt}
            TASK: {instruction}
            OUTPUT: Markdown Vietnamese. Code in cpp block.
            """
            
            fix_container = st.empty()
            full_fix = ""
            img = st.session_state.get('current_image')
            
            for ch in stream_ai_response(prompt_fix, image=img):
                full_fix += ch
                fix_container.markdown(full_fix)
                
            st.session_state['ai_fix_result'] = full_fix

if st.session_state.get('ai_fix_result'):
    with st.container(border=True):
        st.info("Kết quả sửa lỗi:")
        st.markdown(st.session_state['ai_fix_result'])
