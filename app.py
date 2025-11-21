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
    page_title="Nguyễn Huy Dũng",
    layout="wide",
    page_icon="",
    initial_sidebar_state="expanded"
)

# --- 2. CSS MAGIC ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&display=swap');
    .stApp { background-color: #0e1117; }
    .gradient-text {
        background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5, #ff00ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3em; padding-bottom: 10px;
    }
    .stTextArea textarea {
        font-family: 'Fira Code', monospace !important;
        background-color: #161b22 !important; color: #e6edf3 !important;
        border: 1px solid #30363d; border-radius: 8px;
    }
    .stButton>button { border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #1f2937; border-radius: 6px; }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; color: white !important; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
try:
    # Kiểm tra xem đang chạy trên Streamlit Cloud hay Local có secrets.toml
    if "GOOGLE_API_KEY" in st.secrets:
        # Lấy chuỗi key từ secrets, tách bằng dấu phẩy
        raw_keys = st.secrets["GOOGLE_API_KEY"]
        API_KEYS = [k.strip() for k in raw_keys.split(',') if k.strip()]
    else:
        # Nếu chạy local mà chưa tạo file secrets, để trống (sẽ báo lỗi trên UI)
        API_KEYS = []
except FileNotFoundError:
    API_KEYS = []

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
if 'logic_status' not in st.session_state: st.session_state['logic_status'] = "AI chưa hoạt động"
if 'failed_cases' not in st.session_state: st.session_state['failed_cases'] = []
if 'cpp_code_content' not in st.session_state:
    st.session_state['cpp_code_content'] = """#include <iostream>
using namespace std;
int main() {
    ios_base::sync_with_stdio(false); cin.tie(NULL);
    // Code here
    return 0;
}"""
if 'reference_code' not in st.session_state: st.session_state['reference_code'] = ""
if 'ai_fix_result' not in st.session_state: st.session_state['ai_fix_result'] = ""

# --- 4. CÁC HÀM GỌI AI (STREAMING ENGINE) ---
def configure_ai():
    key = get_random_key()
    if not key: return False
    genai.configure(api_key=key)
    return True

# Hàm wrapper để stream dữ liệu
def stream_ai_response(prompt_text):
    if not configure_ai(): 
        yield "❌ Lỗi: Chưa nhập API Key hợp lệ."
        return
    try:
        model = genai.GenerativeModel('gemini-2.0-flash') # Flash cho tốc độ tối đa
        response = model.generate_content(prompt_text, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"❌ Lỗi kết nối AI: {str(e)}"

def get_ai_test_logic(problem_text):
    if not configure_ai(): return None
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Role: Senior QA Engineer. Task: Write Python test generator for: {problem_text}
        RULES:
        1. `generate_input()`: Global `used_inputs`, while loop check duplicates.
           - 15% Tiny (Edge cases), 15% Max (Stress test), 70% Random.
        2. `solve_reference(input_str)`: Return string. Force type casting.
        3. OUTPUT: ONLY PYTHON CODE. NO MARKDOWN.
        """
        response = model.generate_content(prompt)
        return response.text.replace("```python", "").replace("```", "").strip()
    except: return None

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 class='sub-gradient'>🎛️ Bảng điều khiển</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        num_tests = st.slider("Số Test:", 10, 1000, 50, step=10)
        time_limit = st.slider("Time Limit (s):", 0.1, 5.0, 1.0, step=0.1)
    st.write("###")
    with st.container(border=True):
        st.info(st.session_state['logic_status'])
        active_keys = len([k for k in API_KEYS if "PASTE" not in k and len(k) > 10])
        st.caption(f"🔑 Keys: {active_keys} | ⚡ Model: Gemini 2.0 Flash")

# --- 6. GIAO DIỆN CHÍNH ---
st.markdown("<h1 class='gradient-text'> BOT CHECK SỐ 1 VIỆT NAM <span style='font-size:0.5em'> </span></h1>", unsafe_allow_html=True)

# INPUT PROBLEM
with st.expander("📝 ĐỀ BÀI ", expanded=True):
    c1, c2 = st.columns([4, 1])
    with c1:
        problem = st.text_area("Input Problem", height=100, placeholder="đề bài...", label_visibility="collapsed")
    with c2:
        if st.button("✨ Gửi đề", type="primary", use_container_width=True):
            if not problem: st.toast("Thiếu đề!", icon="⚠️")
            else:
                with st.spinner("AI đang thiết lập logic..."):
                    nc = get_ai_test_logic(problem)
                    if nc:
                        st.session_state['python_logic'] = nc
                        st.session_state['logic_status'] = "✅ Logic sẵn sàng"
                        st.session_state['failed_cases'] = []
                        st.session_state['reference_code'] = ""
                        st.session_state['ai_fix_result'] = ""
                        st.toast("Đã nạp xong!", icon="✅")
                    else: st.toast("Lỗi AI", icon="❌")
        
        # NÚT GIẢI ĐỀ (STREAMING)
        if st.button("📖 Gợi ý code", type="secondary", use_container_width=True):
            if not problem: st.toast("Chưa có đề!", icon="⚠️")
            else:
                st.session_state['reference_code'] = "" # Reset cũ
                st.session_state['show_solution_stream'] = True # Kích hoạt stream

# KHUNG HIỂN THỊ CODE MẪU (STREAMING)
if st.session_state.get('show_solution_stream'):
    st.info("💡 **AI đang viết lời giải...**")
    prompt_sol = f"Role: Competitive Programmer. Task: Solve C++: {problem}. Rules: Optimize O2, Commented. CODE ONLY."
    
    # Container để hứng text stream
    solution_container = st.empty()
    full_response = ""
    
    # Bắt đầu stream
    for chunk in stream_ai_response(prompt_sol):
        full_response += chunk
        # Hiển thị realtime (làm sạch markdown để code đẹp)
        clean_view = full_response.replace("```cpp", "").replace("```c++", "").replace("```", "")
        solution_container.code(clean_view, language='cpp')
    
    # Lưu kết quả cuối cùng
    st.session_state['reference_code'] = full_response.replace("```cpp", "").replace("```c++", "").replace("```", "").strip()
    st.session_state['show_solution_stream'] = False # Tắt chế độ stream
    st.rerun() # Làm mới để đưa vào expander gọn gàng

# Hiển thị kết quả tĩnh (sau khi stream xong)
if st.session_state['reference_code'] and not st.session_state.get('show_solution_stream'):
    with st.expander("💡 Code Mẫu Tham Khảo (Đã xong)", expanded=True):
        st.code(st.session_state['reference_code'], language='cpp')

# CODE EDITOR
st.write("###")
code_cpp = st.text_area("C++ Editor", height=400, key="cpp_code_content", label_visibility="collapsed")

# --- 7. TABS CHỨC NĂNG ---
tab1, tab2, tab3 = st.tabs(["Tự động chấm", "Custom test", "Phân tích"])

# === TAB 1: AUTO JUDGE ===
with tab1:
    st.write("###")
    if st.button("Submit", type="primary", use_container_width=True):
        st.session_state['ai_fix_result'] = "" # Reset fix cũ
        
        with open(CPP_FILENAME, "w", encoding="utf-8") as f: f.write(st.session_state['cpp_code_content'])
        cmd = ["g++", "-O2", CPP_FILENAME, "-o", "solution"]
        
        with st.status("Đang xử lý...", expanded=True) as status:
            ret = subprocess.run(cmd, capture_output=True, text=True)
            if ret.returncode != 0:
                status.update(label="Lỗi biên dịch!", state="error"); st.error(ret.stderr)
            else:
                exec_env = {"random": random, "math": math, "sys": sys, "used_inputs": set()}
                try:
                    exec(st.session_state['python_logic'], exec_env)
                    gen_in = exec_env['generate_input']; solve_ref = exec_env['solve_reference']
                    exec_env['used_inputs'] = set()
                    
                    results = []; correct = 0; failed_log = []; start_t = time.time(); p_bar = st.progress(0)
                    
                    for i in range(num_tests):
                        inp, exp, got, stat = "N/A", "N/A", "ERR", "ERR"
                        try:
                            inp = str(gen_in()); exp = str(solve_ref(inp)).strip()
                            p = subprocess.Popen([EXE_FILENAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            out, err = p.communicate(input=inp, timeout=time_limit)
                            got = out.strip()
                            if got == exp: stat = "✅ PASS"; correct += 1
                            else: stat = "❌ FAIL"; failed_log.append(f"Case {i+1}: In='{inp}' | Exp='{exp}' | Got='{got}'")
                        except subprocess.TimeoutExpired: p.kill(); stat = "⏳ TLE"; failed_log.append(f"Case {i+1}: TLE")
                        except Exception as e: got = f"Err: {e}"
                        
                        results.append({"Test": i+1, "Input": inp, "Exp": exp, "Got": got, "Status": stat})
                        if i % (max(1, num_tests // 20)) == 0: p_bar.progress((i+1)/num_tests)
                    
                    p_bar.progress(100); status.update(label="Hoàn tất!", state="complete", expanded=False)
                    st.session_state['failed_cases'] = failed_log
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Score", f"{correct}/{num_tests}")
                    m2.metric("Accuracy", f"{correct/num_tests*100:.1f}%")
                    m3.metric("Time", f"{time.time()-start_t:.2f}s")
                    
                    if correct == num_tests: st.balloons(); st.success("🎉 PERFECT!")
                    else: st.error(f"⚠️ Sai {num_tests-correct} câu.")

                    df = pd.DataFrame(results)
                    try:
                        def hl(r): return ['background-color: rgba(40,167,69,0.15)']*len(r) if 'PASS' in r['Status'] else ['background-color: rgba(220,53,69,0.25)']*len(r)
                        st.dataframe(df.style.apply(hl, axis=1), use_container_width=True, height=500)
                    except: st.dataframe(df, use_container_width=True, height=500)
                                
                except Exception as e: st.error(f"Logic Error: {e}")

# === TAB 2: CUSTOM TEST ===
with tab2:
    st.write("###")
    c_in, c_out = st.columns(2)
    with c_in: custom_input = st.text_area("Nhập Input:", height=200, placeholder="Huy Dũng")
    with c_out:
        st.write("Output:"); custom_out_placeholder = st.empty()
    if st.button("Submit"):
        with open(CPP_FILENAME, "w", encoding="utf-8") as f: f.write(st.session_state['cpp_code_content'])
        subprocess.run(["g++", "-O2", CPP_FILENAME, "-o", "solution"])
        try:
            p = subprocess.Popen([EXE_FILENAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = p.communicate(input=custom_input, timeout=time_limit); custom_out_placeholder.code(out)
        except Exception as e: custom_out_placeholder.error(f"Error: {e}")

# === TAB 3: PHÂN TÍCH (STREAMING) ===
with tab3:
    st.write("###")
    if st.button("🔍 Phân tích Code"):
        st.session_state['analysis_result'] = ""
        container = st.empty()
        prompt = f"Analyze Time & Space Complexity (Big-O) for this C++ code. Explain briefly. Markdown.\n{st.session_state['cpp_code_content']}"
        full_text = ""
        for chunk in stream_ai_response(prompt):
            full_text += chunk
            container.markdown(full_text)
        st.session_state['analysis_result'] = full_text

# --- 8. AI FIXER (STREAMING) ---
if st.session_state.get('failed_cases'):
    st.markdown("---")
    st.subheader("🆘 Trợ lý AI")
    
    if st.button("🤖 Sửa Code", type="primary"):
        prompt_fix = f"Problem: {problem}\nCode: {st.session_state['cpp_code_content']}\nFailures: {' '.join(st.session_state['failed_cases'][:3])}\nTask: Explain fix & provide Correct Code."
        
        fix_container = st.empty()
        full_fix = ""
        
        for chunk in stream_ai_response(prompt_fix):
            full_fix += chunk
            fix_container.markdown(full_fix)
            
        st.session_state['ai_fix_result'] = full_fix

if st.session_state.get('ai_fix_result'):
    st.info("✅ Kết quả phân tích:")
    st.markdown(st.session_state['ai_fix_result'])