import streamlit as st
import google.generativeai as genai
import re
import json
from datetime import datetime

st.set_page_config(page_title="MagicQuill: Logic Lab", layout="centered", page_icon="🖋️")

# --- 세션 상태 초기화 ---
if "history" not in st.session_state:
    st.session_state.history = []
if "logic_db" not in st.session_state:
    st.session_state.logic_db = []
if "temp_logic" not in st.session_state:
    st.session_state.temp_logic = None # AI가 새로 찾은 임시 로직

# --- 타이틀 ---
st.title("🖋️ MagicQuill: Logic Stack v2.1")
st.markdown("---")

# --- 사이드바: API 설정 ---
with st.sidebar:
    api_key = st.sidebar.text_input("Gemini API Key", type="password")
    st.divider()
    if st.button("🗑️ 전체 데이터 초기화"):
        st.session_state.clear()
        st.rerun()

# --- [추가] 신규 로직 발견 시 확인창 (가장 상단) ---
if st.session_state.temp_logic:
    with st.container(border=True):
        st.warning("✨ **MagicQuill이 새로운 마법(로직)을 써냈습니다!**")
        st.write(f"**대상:** {st.session_state.temp_logic['source']}")
        st.code(st.session_state.temp_logic['regex'], language="regex")
        
        col_ok, col_no = st.columns(2)
        if col_ok.button("✅ 로직 저장 및 적용", use_container_width=True):
            # 로직 DB에 저장
            st.session_state.logic_db.insert(0, st.session_state.temp_logic)
            # 히스토리 업데이트 (방금 입력한 항목에 로직 번호 부여)
            if st.session_state.history:
                st.session_state.history[0]['pattern_id'] = 1 # 가장 최근 추가된 로직
                st.session_state.history[0]['method'] = "✅ 신규 로직 학습됨"
            
            st.session_state.temp_logic = None
            st.toast("로직이 마법 잉크병에 저장되었습니다!")
            st.rerun()
            
        if col_no.button("❌ 이번만 처리 (저장 안 함)", use_container_width=True):
            st.session_state.temp_logic = None
            st.rerun()

# --- 1단: 텍스트 입력 ---
input_text = st.text_input("📩 새로운 알림 문구를 입력하세요", key="input_text")
if st.button("MagicQuill 실행 ✨", use_container_width=True):
    if not api_key:
        st.error("API Key를 입력해주세요.")
    elif input_text:
        # 1. 기존 로직 매칭 시도
        matched_idx = -1
        for i, logic in enumerate(st.session_state.logic_db):
            if re.search(logic['regex'], input_text):
                matched_idx = len(st.session_state.logic_db) - i
                matched_regex = logic['regex']
                break
        
        if matched_idx != -1:
            match = re.search(matched_regex, input_text)
            new_entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "raw": input_text,
                "data": match.groups(),
                "method": "✅ 기존 로직 매칭",
                "pattern_id": matched_idx,
                "color": "green"
            }
            st.session_state.history.insert(0, new_entry)
        else:
            # 2. AI 분석 및 임시 로직 생성
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-3-flash-preview")
                prompt = f"가계부 파싱용 JSON만 출력: 1.store 2.amount 3.regex(그룹핑 포함). 원문: {input_text}"
                
                response = model.generate_content(prompt)
                res_json = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                
                # 히스토리 우선 기록 (패턴번호는 아직 미정)
                new_entry = {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "raw": input_text,
                    "data": f"{res_json['store']} | {res_json['amount']}원",
                    "method": "❓ 신규 로직 검토 중",
                    "pattern_id": "NEW",
                    "color": "orange"
                }
                st.session_state.history.insert(0, new_entry)
                
                # 확인창을 띄우기 위해 temp_logic에 저장
                st.session_state.temp_logic = {
                    "regex": res_json['regex'],
                    "source": res_json['store']
                }
                st.rerun()
            except Exception as e:
                st.error(f"분석 실패: {e}")

# --- 2단: 파싱 히스토리 ---
st.subheader("📋 파싱 히스토리")
for entry in st.session_state.history:
    pid = entry.get('pattern_id', '-')
    with st.expander(f"[{entry['time']}] {entry['method']} (Pattern #{pid})"):
        st.write(f"**원문:** {entry['raw']}")
        st.write(f"**추출:** :{entry['color']}[{entry['data']}]")

# --- 3단: 로직 리스트 (삭제 버튼 추가) ---
st.divider()
st.subheader("🔮 마법 잉크병 (로직 리스트)")
for i, logic in enumerate(st.session_state.logic_db):
    logic_idx = len(st.session_state.logic_db) - i
    col_code, col_del = st.columns([0.85, 0.15])
    
    with col_code:
        st.code(f"#{logic_idx} | {logic['source']}\n{logic['regex']}", language="regex")
    
    with col_del:
        if st.button("🗑️", key=f"del_{logic_idx}"):
            st.session_state.logic_db.pop(i)
            st.toast(f"Pattern #{logic_idx} 로직이 삭제되었습니다.")
            st.rerun()
