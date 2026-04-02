import streamlit as st
import google.generativeai as genai
import re
import json
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="MagicQuill: Logic Lab", layout="centered", page_icon="🖋️")

# --- 세션 상태 초기화 (데이터 유지용) ---
if "history" not in st.session_state:
    st.session_state.history = []  # 파싱된 내역 리스트
if "logic_db" not in st.session_state:
    st.session_state.logic_db = []  # 저장된 정규표현식 로직 리스트

# --- UI 타이틀 ---
st.title("🖋️ MagicQuill: Logic Stack")
st.caption("알림을 입력하면 마법 깃펜이 로직을 찾아내고 기록합니다.")

# --- 사이드바: API 설정 ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    if st.button("🗑️ 모든 데이터 초기화"):
        st.session_state.history = []
        st.session_state.logic_db = []
        st.rerun()

# --- 1단: 텍스트 입력 섹션 ---
with st.container():
    input_text = st.text_input("📩 새로운 알림 문구를 입력하세요 (Enter)", key="input_field")
    add_btn = st.button("MagicQuill 실행 ✨", use_container_width=True)

# --- 파싱 및 로직 처리 ---
if add_btn and input_text:
    if not api_key:
        st.error("API Key가 필요합니다.")
    else:
        # 1. 기존 로직 검사 (Local Match)
        matched_logic = None
        for logic in st.session_state.logic_db:
            if re.search(logic['regex'], input_text):
                matched_logic = logic
                break
        
        if matched_logic:
            # 기존 로직에 걸린 경우
            match = re.search(matched_logic['regex'], input_text)
            new_entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "raw": input_text,
                "data": match.groups(), # 정규식 그룹 데이터 추출
                "method": "✅ 기존 로직 매칭",
                "color": "green"
            }
            st.session_state.history.insert(0, new_entry)
        else:
            # 2. AI로 새로운 로직 생성 (AI Generation)
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-3-flash-preview")
                
                prompt = f"""
                너는 'MagicQuill'의 로직 생성기야. 아래 문구를 분석해서 정보를 추출하고 정규표현식을 짜줘.
                [원문]: {input_text}
                응답은 반드시 JSON으로만 해:
                1. 'store': 상호명
                2. 'amount': 숫자금액 (마이너스 포함)
                3. 'regex': 이 문구의 상호명과 금액 부분을 (.*)와 (\d+)로 그룹화한 Python 정규표현식
                """
                
                response = model.generate_content(prompt)
                res_json = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                
                # 결과 저장
                new_entry = {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "raw": input_text,
                    "data": f"{res_json['store']} | {res_json['amount']}원",
                    "method": "✨ AI 신규 로직 발견",
                    "color": "orange"
                }
                st.session_state.history.insert(0, new_entry)
                
                # 새로운 로직 리스트에 누적
                st.session_state.logic_db.insert(0, {
                    "regex": res_json['regex'],
                    "source": res_json['store']
                })
            except Exception as e:
                st.error(f"마법 실패: {e}")

# --- 2단: 파싱 리스트 누적 (최신순) ---
st.subheader("📋 파싱 히스토리")
if not st.session_state.history:
    st.info("아직 처리된 내역이 없습니다.")
else:
    for entry in st.session_state.history:
        with st.expander(f"[{entry['time']}] {entry['method']}", expanded=True):
            st.markdown(f"**원문:** {entry['raw']}")
            st.markdown(f"**추출:** :{entry['color']}[{entry['data']}]")

# --- 3단: 저장된 로직 리스트 ---
st.divider()
st.subheader("🔮 마법 잉크병 (저장된 로직)")
if not st.session_state.logic_db:
    st.write("아직 학습된 로직이 없습니다.")
else:
    for i, logic in enumerate(st.session_state.logic_db):
        st.code(f"Pattern {len(st.session_state.logic_db)-i}: {logic['regex']} ({logic['source']})")
