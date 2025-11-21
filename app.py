import streamlit as st
import subprocess
import os
import sys
import pandas as pd
import time
import google.generativeai as genai
import random
import math

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="BOT CHECK SỐ 1 VIỆT NAM",
    layout="wide",
    page_icon="🤖",
    initial_sidebar_state="expanded"
)

# --- 2. CSS SIÊU CẤP (NEON STYLE) ---
st.markdown("""
<style>
    /* Import Font xịn */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    /* Nền chung */
    .stApp {
        background-color: #09090b;
        background-image: radial-gradient(circle at 50% 0%, #1f1f2e 0%, #09090b 70%);
    }

    /* Tiêu đề Gradient Neon */
    h1 {
        font-family: 'JetBrains Mono', monospace;
        background: linear-gradient(to right, #00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(0, 198, 255, 0.5);
        font-weight: 800 !important;
    }

    /* Khung chứa (Containers) */
    [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: #121217;
        border: 1px solid #2d2d3a;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        padding: 15px;
    }

    /* Ô nhập liệu code */
    .stTextArea textarea {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #000000 !important;
        color: #00ff9d !important; /* Chữ code màu xanh hacker */
        border: 1px solid #333;
        border-radius: 8px;
    }
    .stTextArea textarea:focus {
        border-color: #0072ff;
        box-shadow: 0 0 10px rgba(0, 114, 255, 0.3);
    }

    /* Nút bấm đẹp */
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    /* Nút Primary (Màu cam đỏ nổi bật) */
    div[data-testid="stVerticalBlock"] button[kind="primary"] {
        background: linear-gradient(45deg, #ff416c, #ff4b2b);
        color: white;
        box-shadow: 0 4px 15px rgba(255, 65, 108, 0.4);
    }
    div[data-testid="stVerticalBlock"] button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 65, 108, 0.6);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0e0e12;
        border-right: 1px solid #2d2d3a;
    }
    
    /* Bảng kết quả */
    .dataframe {
        font-family: 'JetBrains Mono', monospace;
        border: 1px solid #333 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 👇 CẤU HÌNH API KEY TỰ ĐỘNG TỪ SECRETS (KHÔNG SỬA) 👇
# ==============================================================================
try:
    if "GOOGLE_API_KEY" in st.secrets:
        raw_keys = st.secrets["GOOGLE_API_KEY"]
        API_KEYS = [k.strip() for k in raw_keys.split(',') if k.strip()]
    else: API_KEYS = []
except FileNotFoundError: API_KEYS = []

def get_random_key():
    if not API_KEYS: return None
    return random.choice(API_KEYS)

CPP_FILENAME = "solution.cpp"
EXE_FILENAME = "solution.exe" if os.name == 'nt' else "./solution"

# --- 3. KHỞI TẠO BỘ NHỚ ---
if 'python_logic' not in st.session_state:
    st.session_state['python_logic'] = """used_inputs = set()
def generate_input(): return "10 20"
def solve_reference(s): return "30" """
if 'logic_status' not in st.session_state: st.session_state['logic_status'] = "💤 Chờ lệnh..."
if 'failed_cases' not in st.session_state: st.session_state['failed_cases'] = []
if 'cpp_code_content' not in st.session_state:
    st.session_state['cpp_code_content'] = """#include <iostream>
using namespace std;
int main() {
    ios_base::sync_with_stdio(false); cin.tie(NULL);
    long long n;
    // Viết code tại đây...
    return 0;
}"""
if 'reference_code' not in st.session_state: st.session_state['reference_code'] = ""
if 'ai_fix_result' not in st.session_state: st.session_state['ai_fix_result'] = ""
if 'selected_model_name' not in st.session_state: st.session_state['selected_model_name'] = "gemini-2.0-flash"

# --- 4. AI FUNCTIONS ---
def configure_ai():
    key = get_random_key()
    if not key: return False
    genai.configure(api_key=key)
    return True

def get_model_id(): return st.session_state.get('selected_model_name', 'gemini-2.0-flash')

def stream_ai_response(prompt_text):
    if not configure_ai(): yield "❌ Lỗi: Chưa cấu hình API Key trong Secrets."; return
    try:
        model = genai.GenerativeModel(get_model_id())
        response = model.generate_content(prompt_text, stream=True)
        for chunk in response:
            if chunk.text: yield chunk.text
    except Exception as e: yield f"⚠️ Lỗi AI: {str(e)}"

def get_ai_test_logic(problem_text):
    if not configure_ai(): return None
    try:
        model = genai.GenerativeModel(get_model_id())
        prompt = f"""Role: Senior QA. Task: Python test generator for: {problem_text}. 
        RULES: `generate_input()` using global `used_inputs`, check dup. 15% Tiny, 15% Max, 70% Random. 
        `solve_reference(input_str)` return string. CODE ONLY."""
        response = model.generate_content(prompt)
        return response.text.replace("```python", "").replace("```", "").strip()
    except Exception as e: st.error(f"Lỗi: {e}"); return None

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🎛️ BẢNG ĐIỀU KHIỂN")
    
    if not API_KEYS:
        st.error("⚠️ Chưa nạp Key vào Secrets!")
    else:
        st.success(f"🔑 {len(API_KEYS)} Key hoạt động")

    with st.container():
        st.write("**🧠 Bộ não AI**")
        model_option = st.selectbox("Model:", 
            ["gemini-2.0-flash", "models/gemini-2.5-flash-preview"], 
            index=0, label_visibility="collapsed")
        st.session_state['selected_model_name'] = model_option
        
        st.divider()
        st.write("**⚙️ Cài đặt Test**")
        num_tests = st.slider("Số lượng Test:", 10, 1000, 50, step=10)
        time_limit = st.slider("Time Limit (s):", 0.1, 5.0, 1.0, step=0.1)
        
        st.divider()
        st.info(f"Trạng thái: {st.session_state['logic_status']}")

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<h1>BOT CHECK SỐ 1 VIỆT NAM 🇻🇳</h1>", unsafe_allow_html=True)

# INPUT
with st.container():
    c1, c2 = st.columns([3, 1])
    with c1:
        problem = st.text_area("📝 ĐỀ BÀI", height=120, placeholder="Dán đề bài vào đây...", label_visibility="visible")
    with c2:
        st.write("") # Spacer
        st.write("") 
        if st.button("✨ NẠP ĐỀ BÀI", type="primary", use_container_width=True):
            if not problem: st.toast("Chưa có đề!", icon="⚠️")
            else:
                with st.spinner("AI đang suy nghĩ..."):
                    nc = get_ai_test_logic(problem)
                    if nc:
                        st.session_state['python_logic'] = nc
                        st.session_state['logic_status'] = "✅ Đã có Logic"
                        st.session_state['failed_cases'] = []
                        st.toast("Đã nạp xong!", icon="✅")
        
        if st.button("📖 GIẢI MẪU", type="secondary", use_container_width=True):
            if not problem: st.toast("Chưa có đề!", icon="⚠️")
            else:
                st.session_state['reference_code'] = ""
                st.session_state['show_solution_stream'] = True

# STREAM SOL
if st.session_state.get('show_solution_stream'):
    st.info("💡 AI đang viết code...")
    container = st.empty()
    full_res = ""
    for chunk in stream_ai_response(f"Solve C++: {problem}. Optimize. CODE ONLY."):
        full_res += chunk
        container.code(full_res.replace("```cpp","").replace("```",""), language='cpp')
    st.session_state['reference_code'] = full_res.replace("```cpp","").replace("```","").strip()
    st.session_state['show_solution_stream'] = False
    st.rerun()

if st.session_state['reference_code']:
    with st.expander("💡 Code Mẫu (Click để xem)"):
        st.code(st.session_state['reference_code'], language='cpp')

# EDITOR
st.write("###")
col_editor, col_action = st.columns([4, 1])
with col_editor:
    st.markdown("#### 💻 Code C++ Của Bạn")
    code_cpp = st.text_area("Editor", height=450, key="cpp_code_content", label_visibility="collapsed")

with col_action:
    st.write("")
    st.write("")
    st.write("")
    if st.button("🚀 CHẤM BÀI\n(RUN)", type="primary", use_container_width=True):
        st.session_state['run_judge'] = True

# JUDGE LOGIC
if st.session_state.get('run_judge'):
    st.session_state['run_judge'] = False
    st.session_state['ai_fix_result'] = ""
    
    with open(CPP_FILENAME, "w", encoding="utf-8") as f: f.write(st.session_state['cpp_code_content'])
    cmd = ["g++", "-O2", CPP_FILENAME, "-o", "solution"]
    
    with st.status("🚀 Đang chấm bài...", expanded=True) as status:
        st.write("🔨 Compiling...")
        ret = subprocess.run(cmd, capture_output=True, text=True)
        if ret.returncode != 0:
            status.update(label="Lỗi biên dịch!", state="error")
            st.error(ret.stderr)
        else:
            st.write("🐍 Testing...")
            exec_env = {"random": random, "math": math, "sys": sys, "used_inputs": set()}
            try:
                exec(st.session_state['python_logic'], exec_env)
                gen_in = exec_env['generate_input']; solve_ref = exec_env['solve_reference']
                exec_env['used_inputs'] = set()
                
                results = []; correct = 0; failed_log = []
                p_bar = st.progress(0)
                
                for i in range(num_tests):
                    inp, exp, got, stat = "N/A", "N/A", "ERR", "ERR"
                    try:
                        inp = str(gen_in()); exp = str(solve_ref(inp)).strip()
                        p = subprocess.Popen([EXE_FILENAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        out, err = p.communicate(input=inp, timeout=time_limit)
                        got = out.strip()
                        if got == exp: stat = "PASS"; correct += 1
                        else: stat = "FAIL"; failed_log.append(f"Case {i+1}: In='{inp}' | Exp='{exp}' | Got='{got}'")
                    except subprocess.TimeoutExpired: p.kill(); stat = "TLE"; failed_log.append(f"Case {i+1}: TLE")
                    except Exception as e: got = f"Err: {e}"
                    
                    results.append({"Test": i+1, "Input": inp, "Exp": exp, "Got": got, "Status": stat})
                    if i % (max(1, num_tests // 20)) == 0: p_bar.progress((i+1)/num_tests)
                
                p_bar.progress(100); status.update(label="Hoàn tất!", state="complete", expanded=False)
                st.session_state['failed_cases'] = failed_log
                
                # Metrics
                c1, c2, c3 = st.columns(3)
                c1.metric("Total", num_tests)
                c2.metric("Score", f"{correct}/{num_tests}")
                c3.metric("Accuracy", f"{int(correct/num_tests*100)}%")
                
                if correct == num_tests: st.balloons(); st.success("🏆 TUYỆT VỜI! ĐÚNG HẾT!")
                else: st.error(f"⚠️ Sai {num_tests-correct} câu.")
                
                # Table
                df = pd.DataFrame(results)
                def hl(row):
                    return ['background-color: rgba(0, 255, 127, 0.1)'] * len(row) if row['Status'] == 'PASS' else ['background-color: rgba(255, 65, 108, 0.15)'] * len(row)
                try: st.dataframe(df.style.apply(hl, axis=1), use_container_width=True, height=500)
                except: st.dataframe(df, use_container_width=True, height=500)
                
            except Exception as e: st.error(f"Lỗi Logic: {e}")

# AI FIXER
if st.session_state.get('failed_cases'):
    st.markdown("---")
    c_fix_1, c_fix_2 = st.columns([1, 4])
    with c_fix_2:
        if st.button("🚑 AI CHỮA BÀI (STREAM)", type="primary"):
            prompt = f"Prob: {problem}\nCode: {st.session_state['cpp_code_content']}\nFailures: {' '.join(st.session_state['failed_cases'][:3])}\nFix it."
            cont = st.empty(); full = ""
            for chunk in stream_ai_response(prompt):
                full += chunk; cont.markdown(full)
            st.session_state['ai_fix_result'] = full

if st.session_state.get('ai_fix_result'):
    st.success("Phân tích xong:")
    st.markdown(st.session_state['ai_fix_result'])
