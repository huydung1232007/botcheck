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
import datetime
import json

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Nguyễn Huy Dũng",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 👇 CẤU HÌNH API KEY 👇
try:
    if "GEMINI_KEYS" in st.secrets: API_KEYS = st.secrets["GEMINI_KEYS"]
    else: API_KEYS = [""]
except: API_KEYS = [""]

def get_random_key(): return random.choice([k for k in API_KEYS if "PASTE" not in k])

CPP_FILENAME = "solution.cpp"; EXE_FILENAME = "solution.exe" if os.name == 'nt' else "./solution"

# --- 2. QUẢN LÝ LỊCH SỬ ---
HISTORY_FILE = "history.json"

def load_history_from_disk():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_history_to_disk(history_data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)
    except: pass

# --- 3. KHỞI TẠO BỘ NHỚ ---
if 'history' not in st.session_state:
    st.session_state['history'] = load_history_from_disk()

defaults = {
    'python_logic': """used_inputs = set()\ndef generate_input(): return "10 20"\ndef solve_reference(s): return "30" """,
    'logic_status': "Chưa khởi tạo", 'failed_cases': [],
    'cpp_code_content': """#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios_base::sync_with_stdio(false); cin.tie(NULL);\n    // Code here\n    return 0;\n}""",
    'reference_code': "", 'ai_fix_result': "",
    'chat_history': [{"role": "assistant", "content": "Chào Sếp! Cần hỗ trợ gì về C++ không ạ?"}],
    'current_image': None, 'problem_text_input': "", 'chat_pasted_image': None, 'refine_request': "",
    'quiz_data': None
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 4. AI FUNCTIONS ---
def configure_ai():
    key = get_random_key()
    if not key: return False
    genai.configure(api_key=key); return True

def stream_ai_response(prompt, image=None):
    if not configure_ai(): yield "❌ Lỗi Key"; return
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        content = [prompt]; 
        if image: content.append(image)
        response = model.generate_content(content, stream=True)
        for chunk in response: 
            if chunk.text: yield chunk.text
    except Exception as e: yield f"❌ Lỗi AI: {str(e)}"

def extract_text_from_image(image):
    if not configure_ai(): return None
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        res = model.generate_content(["Extract text exactly.", image])
        return res.text.strip()
    except: return None

def get_ai_test_logic(problem, image=None):
    if not configure_ai(): return None
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""Role: Senior QA. Task: Write Python test generator for: {problem}.
        CRITICAL REQUIREMENTS:
        1. You MUST define a function `def generate_input(): -> str`.
        2. You MUST define a function `def solve_reference(s): -> str`.
        3. STRICT: 50% Tiny Input, 50% Large Input.
        Output: ONLY RAW PYTHON CODE. NO MARKDOWN."""
        res = model.generate_content([prompt, image] if image else [prompt])
        return res.text.replace("```python", "").replace("```", "").strip()
    except Exception as e: st.error(f"Lỗi Logic: {e}"); return None

# --- 5. HANDLERS ---
def on_click_solve():
    if st.session_state.get('img_uploader'):
        st.session_state['current_image'] = Image.open(st.session_state['img_uploader'])
    
    if st.session_state.get('current_image'):
        with st.spinner("👁️ Đang đọc ảnh..."):
            txt = extract_text_from_image(st.session_state['current_image'])
            if txt: st.session_state['problem_text_input'] = txt; st.toast("Đã đọc đề!", icon="📝")
    
    txt = st.session_state.get('problem_text_input', "")
    img = st.session_state.get('current_image')
    
    if not txt and not img: st.toast("Thiếu đề!", icon="⚠️"); return
    
    nc = get_ai_test_logic(txt, img)
    if nc:
        st.session_state['python_logic'] = nc
        st.session_state['logic_status'] = "✅ Đã hiểu đề"
        st.session_state['failed_cases'] = []
        st.session_state['reference_code'] = ""
        st.session_state['ai_fix_result'] = ""
        st.toast("Đã xong!", icon="🔥")
    else: st.toast("Lỗi AI", icon="❌")

def save_to_history():
    if not st.session_state['problem_text_input'] and not st.session_state['cpp_code_content']:
        st.toast("Không có gì để lưu!", icon="⚠️"); return
    timestamp = datetime.datetime.now().strftime("%d/%m %H:%M")
    entry = {
        "time": timestamp,
        "problem": st.session_state['problem_text_input'],
        "code": st.session_state['cpp_code_content'],
        "logic": st.session_state['python_logic'],
        "status": st.session_state['logic_status']
    }
    st.session_state['history'].insert(0, entry)
    save_history_to_disk(st.session_state['history'])
    st.toast("Đã lưu !", icon="💾")

def load_from_history(entry):
    st.session_state['problem_text_input'] = entry['problem']
    st.session_state['cpp_code_content'] = entry['code']
    st.session_state['python_logic'] = entry['logic']
    st.session_state['logic_status'] = entry.get('status', "Đã tải lại")
    st.toast("Đã tải lại bài cũ!", icon="📂")

def clear_history():
    st.session_state['history'] = []
    if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
    st.rerun()

# --- 2. CSS MAGIC ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap');
    .stApp { background-color: #09090b; color: #e4e4e7; font-family: 'Inter', sans-serif; }
    .gradient-text { background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 3.5rem; text-align: center; }
    .stTextArea textarea { font-family: 'JetBrains Mono', monospace !important; background-color: #18181b !important; color: #a1a1aa !important; border: 1px solid #27272a; }
    div[data-testid="stButton"] > button[kind="primary"] { background: linear-gradient(90deg, #2563eb, #3b82f6); color: white; border: none; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { height: 40px; background-color: #18181b; border: 1px solid #27272a; flex-grow: 1; }
    .stTabs [aria-selected="true"] { background-color: rgba(37, 99, 235, 0.1) !important; border: 1px solid #3b82f6 !important; color: #60a5fa !important; }
    
    .ticker-wrap { width: 100%; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 50px; overflow: hidden; margin-bottom: 20px; height: 40px; display: flex; align-items: center; box-shadow: 0 0 10px rgba(0, 210, 255, 0.1); }
    .ticker { display: inline-block; white-space: nowrap; padding-left: 100%; animation: ticker-scroll 30s linear infinite; }
    .ticker-item { display: inline-block; padding: 0 2rem; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: #00d2ff; text-shadow: 0 0 5px #00d2ff; }
    @keyframes ticker-scroll { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
</style>
""", unsafe_allow_html=True)

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    with st.container(border=True):
        num_tests = st.slider("Số lượng Test:", 10, 500, 50)
        time_limit = st.slider("Giới hạn thời gian (s):", 0.1, 3.0, 1.0)
    
    st.write("###")
    with st.container(border=True):
        status = st.session_state.get('logic_status', 'Chưa khởi tạo')
        if "sẵn" in status or "Logic" in status: st.success(status, icon="✅")
        else: st.info(status, icon="ℹ️")
        active_keys = len([k for k in API_KEYS if "PASTE" not in k and len(k) > 10])
        st.caption(f"🔑 API KEYS: **{active_keys}** | ⚡ Model: **dungGPT**")
    
    st.write("---")
    
    # HISTORY
    with st.expander("📂 Lịch sử ", expanded=False):
        c_h1, c_h2 = st.columns([3, 1])
        with c_h1:
            if st.button("💾 ", use_container_width=True): save_to_history()
        with c_h2:
            if st.button("🗑️", help="Xóa hết", use_container_width=True): clear_history()
            
        st.write("---")
        if not st.session_state['history']:
            st.caption("Chưa có lịch sử.")
        else:
            for i, item in enumerate(st.session_state['history']):
                label = f"📅 {item['time']} - {item['problem'][:15]}..." if item['problem'] else f"📅 {item['time']} - (No Name)"
                if st.button(label, key=f"hist_{i}", use_container_width=True):
                    load_from_history(item); st.rerun()
    
    st.write("---")
    # CHATBOT (DÙNG ST.WRITE_STREAM)
    with st.popover("💬 dungGPT", use_container_width=True):
        msgs = st.container(height=300)
        for m in st.session_state.chat_history: msgs.chat_message(m["role"]).write(m["content"])
        
        up = st.file_uploader("Tải ảnh", type=["png","jpg"], key="chat_up", label_visibility="collapsed")
        if up: st.session_state['chat_pasted_image'] = Image.open(up)
        if st.session_state['chat_pasted_image']: 
            st.image(st.session_state['chat_pasted_image'], width=100)
            if st.button("Xóa ảnh"): st.session_state['chat_pasted_image']=None; st.rerun()

        if p := st.chat_input("Hỏi AI..."):
            st.session_state.chat_history.append({"role":"user","content":p})
            msgs.chat_message("user").write(p)
            ctx = f"Context: Prob: {st.session_state['problem_text_input']}. Code: {st.session_state['cpp_code_content']}. VNese."
            with msgs.chat_message("assistant"):
                # FIX LỖI: Dùng write_stream thay vì loop
                full = st.write_stream(stream_ai_response(ctx + f" User: {p}", st.session_state['chat_pasted_image']))
            st.session_state.chat_history.append({"role":"assistant","content":full})
            st.session_state['chat_pasted_image']=None; st.rerun()

# --- 7. MAIN UI ---
st.markdown("<div class='gradient-text'> BOT CODE SỐ 1 HCMUT </div>", unsafe_allow_html=True)

st.markdown("""
<div class="ticker-wrap">
    <div class="ticker">
        <div class="ticker-item">🚀 AI: dungGPT Plus </div>
        <div class="ticker-item">⚡ HCMUT </div>
        <div class="ticker-item">🛡️ STATUS: Online</div>
        <div class="ticker-item">🤖 DEV: Nguyen Huy Dung</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    c1, c2 = st.columns([4, 1])
    with c1: st.markdown("#### 📝 Đề bài"); st.text_area("In", height=200, placeholder="Nhập đề...", key="problem_text_input", label_visibility="collapsed")
    with c2: 
        st.markdown("#### 🖼️ Ảnh"); st.file_uploader("Up", type=["png","jpg"], key="img_uploader", label_visibility="collapsed")
        if st.session_state.get('current_image'): 
            st.image(st.session_state['current_image'], width=150)
            if st.button("Xóa"): st.session_state['current_image']=None; st.rerun()
            
    b1, b2, b3 = st.columns([1, 1, 2])
    with b1: st.button("🚀 SEND ", type="primary", on_click=on_click_solve, use_container_width=True)
    with b2: 
        if st.button("💡 Gợi ý", type="secondary", use_container_width=True):
            st.session_state['show_solution_stream']=True; st.rerun()
    with b3: st.markdown(f"<div style='text-align:right;padding-top:10px;opacity:0.7;'><b>{st.session_state['logic_status']}</b></div>", unsafe_allow_html=True)

# STREAMING SOLUTION (FIX LỖI DÙNG WRITE_STREAM)
if st.session_state.get('show_solution_stream'):
    st.info("💡 AI đang code...")
    req = st.session_state.get('refine_request', "")
    prompt = f"Role: CP Expert. Task: REWRITE solution. Req: {req}. Rules: O2, VNese comments." if req else f"Role: CP Expert. Solve: {st.session_state['problem_text_input']}. Rules: O2, VNese comments."
    
    # FIX LỖI: Dùng write_stream
    full = st.write_stream(stream_ai_response(prompt, st.session_state.get('current_image')))
    st.session_state['reference_code'] = full.replace("```cpp","").replace("```","").strip()
    st.session_state['show_solution_stream'] = False; st.session_state['refine_request']=""; st.rerun()

if st.session_state['reference_code'] and not st.session_state.get('show_solution_stream'):
    with st.expander("💡 Tham Khảo", expanded=False):
        st.code(st.session_state['reference_code'], language='cpp')
        c_rf1, c_rf2 = st.columns([3,1])
        with c_rf1: u_refine = st.text_input("Yêu cầu AI", key="ir")
        with c_rf2: 
            st.write(""); st.write("")
            if st.button("✨ Sửa "): 
                st.session_state['refine_request']=u_refine; st.session_state['show_solution_stream']=True; st.rerun()

st.write("###")
st.markdown("### 💻 Code Editor")
st.text_area("Ed", height=400, key="cpp_code_content", label_visibility="collapsed")

# --- TABS ---
t1, t2, t3, t4 = st.tabs(["🚀 TỰ ĐỘNG", "🧪 TEST", "🧩 CÔNG CỤ", "🎮 GAME"])

# T1: AUTO JUDGE
with t1:
    if st.button("🔥 SUBMIT", type="primary", use_container_width=True):
        if os.path.exists(EXE_FILENAME):
            try: os.remove(EXE_FILENAME)
            except: pass 

        with open(CPP_FILENAME, "w", encoding="utf-8") as f: f.write(st.session_state['cpp_code_content'])
        cmd = ["g++", "-O2", CPP_FILENAME, "-o", "solution"]
        with st.status("⚙️ Đang chạy trình biên dịch & tests ...", expanded=True) as s:
            ret = subprocess.run(cmd, capture_output=True, text=True)
            if ret.returncode != 0: s.update(label="Lỗi biên dịch!", state="error"); st.error(ret.stderr)
            else:
                env = {"random": random, "math": math, "sys": sys, "used_inputs": set()}
                try:
                    exec(st.session_state['python_logic'], env)
                    if 'generate_input' not in env or 'solve_reference' not in env:
                        s.update(label="Lỗi AI!", state="error")
                        st.error("⚠️ AI sinh logic bị thiếu hàm. Bấm '🚀 SEND' lại!")
                        st.stop()

                    gen = env['generate_input']; solv = env['solve_reference']; env['used_inputs'] = set()
                    res = []; corr = 0; fails = []
                    pb = st.progress(0)
                    start_t = time.time()
                    
                    for i in range(num_tests):
                        inp = str(gen()); exp = str(solv(inp)).strip()
                        try:
                            p = subprocess.Popen([EXE_FILENAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                            o, e = p.communicate(input=inp, timeout=time_limit); got = o.strip()
                            stt = "✅" if got==exp else "❌"
                            if stt=="✅": corr+=1
                            else: fails.append(f"Case {i+1}: In='{inp}' | Exp='{exp}' | Got='{got}'")
                        except: p.kill(); stt="⏳"; fails.append(f"Case {i+1}: TLE")
                        res.append({"Test":i+1, "In":inp, "Exp":exp, "Got":got, "Stt":stt})
                        pb.progress((i+1)/num_tests)
                    
                    end_t = time.time()
                    s.update(label="Xong!", state="complete", expanded=False)
                    st.session_state['failed_cases'] = fails
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Kết quả", f"{corr}/{num_tests}")
                    acc = corr/num_tests*100 if num_tests > 0 else 0
                    m2.metric("Độ chính xác", f"{acc:.1f}%")
                    m3.metric("Thời gian", f"{end_t - start_t:.2f}s")
                    
                    if corr==num_tests: st.balloons()
                    st.dataframe(pd.DataFrame(res), use_container_width=True, height=300)
                except Exception as e: st.error(f"Lỗi Logic: {e}")

# T2: CUSTOM TEST
with t2:
    st.markdown("#### 🧪 Test Tùy chỉnh")
    cust_in = st.text_area("Nhập Input:", height=150)
    if st.button("⚡ RUN ", type="primary", use_container_width=True):
        with open(CPP_FILENAME, "w", encoding="utf-8") as f: f.write(st.session_state['cpp_code_content'])
        res_build = subprocess.run(["g++", "-O2", CPP_FILENAME, "-o", "solution"], capture_output=True, text=True)
        if res_build.returncode != 0: st.error("Lỗi biên dịch!"); st.code(res_build.stderr)
        else:
            try:
                p = subprocess.Popen([EXE_FILENAME], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out, err = p.communicate(input=cust_in, timeout=time_limit)
                st.success("Output:"); st.code(out)
            except Exception as e: st.error(f"Lỗi: {e}")

# T3: CÔNG CỤ (FIX LỖI STREAM)
with t3:
    st.write("###")
    with st.container(border=True):
        c3_1, c3_2, c3_3 = st.columns(3)
        with c3_1: btn_chart = st.button("🎨 Flowchart", use_container_width=True)
        with c3_2: btn_review = st.button("🧐 Review Code", use_container_width=True)
        with c3_3: 
            lang_dest = st.selectbox("Đích:", ["Python", "Java", "JS", "Go"], label_visibility="collapsed")
            btn_convert = st.button(f"⚡ Convert ", use_container_width=True)

    if btn_chart:
        st.markdown("---")
        if not st.session_state['cpp_code_content']: st.warning("Thiếu code!")
        else:
            with st.status("🎨 Đang vẽ sơ đồ...", expanded=True):
                p = f"Generate Graphviz DOT code for this C++ code:\n{st.session_state['cpp_code_content']}\nOutput only DOT code inside ```dot block."
                d = ""; 
                for c in stream_ai_response(p): d+=c
                try: st.graphviz_chart(d.replace("```dot","").replace("```","").strip())
                except: st.error("Lỗi hiển thị sơ đồ.")

    if btn_review:
        st.markdown("---")
        if not st.session_state['cpp_code_content']: st.warning("Thiếu code!")
        else:
            with st.status("🧐 Đang soi code...", expanded=True):
                curr_prob = st.session_state.get('problem_text_input', "Chưa có đề bài")
                p = f"""
                Role: Senior Competitive Programming Coach.
                Task: Review this C++ code based on the PROBLEM.
                CONTEXT:
                1. PROBLEM: {curr_prob}
                2. CODE: {st.session_state['cpp_code_content']}
                STRICT INSTRUCTIONS:
                - Review in VIETNAMESE.
                - Focus on Algorithm Complexity (Big-O) and Corner Cases.
                - NO redundant small talk.
                OUTPUT FORMAT:
                ## 📊 ĐIỂM: [Score]/100
                ### ✅ Ưu điểm
                ...
                ### ⚠️ Vấn đề
                ...
                ### 🚀 Code Tối ưu
                ```cpp
                ...
                ```
                """
                # FIX LỖI: Dùng write_stream
                st.write_stream(stream_ai_response(p))

    if btn_convert:
        st.markdown("---")
        if not st.session_state['cpp_code_content']: st.warning("Thiếu code!")
        else:
            with st.status(f"⚡ Đang dịch sang {lang_dest}...", expanded=True):
                p = f"Convert C++ to {lang_dest}. VN comments.\n{st.session_state['cpp_code_content']}"
                # FIX LỖI: Dùng write_stream
                st.write_stream(stream_ai_response(p))

# T4: GAME
with t4:
    st.markdown("#### 🎮 Đố vui Code (Quiz)")
    if st.button("🎲 Tạo câu hỏi mới", use_container_width=True):
        with st.spinner("Thinking..."):
            prompt_quiz = f"""
            Role: Quiz Master.
            Task: Generate 1 multiple-choice question about this C++ code.
            Code: {st.session_state['cpp_code_content']}
            Output STRICT JSON format:
            {{
                "question": "Question in VN",
                "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
                "answer": "A",
                "explanation": "Explanation in VN"
            }}
            NO MARKDOWN.
            """
            try:
                model = genai.GenerativeModel('gemini-2.0-flash')
                res = model.generate_content(prompt_quiz)
                clean_json = res.text.replace("```json", "").replace("```", "").strip()
                st.session_state['quiz_data'] = json.loads(clean_json)
            except: st.error("Lỗi tạo câu hỏi")

    if st.session_state.get('quiz_data'):
        q_data = st.session_state['quiz_data']
        st.info(f"❓ **{q_data['question']}**")
        user_choice = st.radio("Chọn đáp án:", q_data['options'], key="quiz_radio")
        if st.button("Kiểm tra"):
            if user_choice.split(".")[0].strip() == q_data['answer'].strip():
                st.success("🎉 Chính xác!"); st.balloons()
            else: st.error(f"❌ Sai! Đáp án là **{q_data['answer']}**")
            st.warning(f"💡 {q_data['explanation']}")

# --- AI FIXER (FIX LỖI STREAM) ---
if st.session_state.get('failed_cases'):
    st.markdown("---"); st.subheader("🆘 FIX ")
    hint = st.text_input("Gợi ý:")
    if st.button(" SỬA ĐI ", type="primary"):
        p = f"""
        Role: Expert C++ Debugger.
        Context:
        - Problem: {st.session_state['problem_text_input']}
        - Code: {st.session_state['cpp_code_content']}
        - Error Log: {st.session_state['failed_cases'][:3]}
        - User Hint: {hint}
        Task: Explain the error STRICTLY in VIETNAMESE and provide fix.
        """
        # FIX LỖI: Dùng write_stream
        f = st.write_stream(stream_ai_response(p))
        st.session_state['ai_fix_result'] = f
    if st.session_state.get('ai_fix_result'): st.markdown(st.session_state['ai_fix_result'])
