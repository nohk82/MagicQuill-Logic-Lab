import streamlit as st
import google.generativeai as genai
import re
import json
import csv
import io
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="MagicQuill: Logic Lab", layout="centered", page_icon="🖋️")

# --- 세션 상태(메모리) 초기화 ---
if "history" not in st.session_state:
    st.session_state.history = []
if "logic_db" not in st.session_state:
    st.session_state.logic_db = []
if "temp_logic" not in st.session_state:
    st.session_state.temp_logic = None

st.title("🖋️ MagicQuill: Logic Stack v2.3")
st.markdown("---")

# --- 사이드바: 설정 및 백업 ---
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password")
    
    st.divider()
    st.subheader("💾 데이터 백업")
    
    # 1. 히스토리 다운로드 (CSV 엑셀용)
    if st.session_state.history:
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["date", "time", "card", "store", "amount", "method", "pattern_id", "raw", "color"])
        writer.writeheader()
        writer.writerows(st.session_state.history)
        csv_data = csv_buffer.getvalue().encode('utf-8-sig') # 한글 깨짐 방지
        
        st.download_button(
            label="📊 히스토리 엑셀로 받기 (.csv)",
            data=csv_data,
            file_name=f"magicquill_history_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    # 2. 로직 DB 다운로드 (JSON용)
    if st.session_state.logic_db:
        logic_json = json.dumps(st.session_state.logic_db, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="🔮 잉크병 로직 백업하기 (.json)",
            data=logic_json,
            file_name=f"magicquill_logic_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )

    st.divider()
    if st.button("🗑️ 전체 데이터 초기화 (Memory Clear)"):
        st.session_state.clear()
        st.rerun()

# --- [0단] 신규 로직 발견 시 승인창 ---
if st.session_state.temp_logic:
    with st.container(border=True):
        st.warning("✨ **새로운 패턴을 발견했습니다! 저장할까요?**")
        
        tl = st.session_state.temp_logic
        st.write(f"**추출 결과:** 💳 {tl['card']} | 🏪 {tl['store']} | 💸 {tl['amount']}원")
        st.code(tl['regex'], language="regex")
        
        col_ok, col_no = st.columns(2)
        if col_ok.button("✅ 로직 저장 및 적용", use_container_width=True):
            st.session_state.logic_db.insert(0, st.session_state.temp_logic)
            
            # 패턴 ID 부여 및 히스토리 업데이트
            new_pattern_id = len(st.session_state.logic_db)
            if st.session_state.history:
                st.session_state.history[0]['pattern_id'] = new_pattern_id
                st.session_state.history[0]['method'] = "✅ 신규 로직 학습됨"
            
            st.session_state.temp_logic = None
            st.toast(f"Pattern #{new_pattern_id} 저장 완료!")
            st.rerun()
            
        if col_no.button("❌ 무시 (저장 안 함)", use_container_width=True):
            st.session_state.temp_logic = None
            st.rerun()

# --- [1단] 텍스트 입력 및 엔진 가동 ---
input_text = st.text_input("📩 새로운 금융 알림 문구를 입력하세요 (Enter)", key="input_text")
if st.button("MagicQuill 실행 ✨", use_container_width=True):
    if not api_key:
        st.error("좌측 사이드바에 API Key를 먼저 입력해주세요.")
    elif input_text:
        now_date = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M:%S")
        
        # 1. 기존 로직 매칭 시도
        matched_idx = -1
        for i, logic in enumerate(st.session_state.logic_db):
            if re.search(logic['regex'], input_text):
                matched_idx = len(st.session_state.logic_db) - i
                matched_logic = logic
                break
        
        if matched_idx != -1: # 기존 로직에 걸렸을 때
            match = re.search(matched_logic['regex'], input_text)
            groups = match.groups()
            
            amount_val = next((g for g in groups if any(c.isdigit() for c in g)), "금액확인")
            store_val = next((g for g in groups if not any(c.isdigit() for c in g)), matched_logic['store'])

            new_entry = {
                "date": now_date,
                "time": now_time,
                "raw": input_text,
                "card": matched_logic['card'], 
                "store": store_val,
                "amount": amount_val,
                "method": "✅ 기존 로직 매칭",
                "pattern_id": matched_idx,
                "color": "green"
            }
            st.session_state.history.insert(0, new_entry)
        else: # 새로운 로직일 때 (AI 호출)
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-3-flash-preview")
                
                prompt = f"""
                가계부 파싱용 JSON만 출력해줘: 
                1.card (결제수단/카드사/은행명)
                2.store (상호명/사용처) 
                3.amount (숫자금액) 
                4.regex (사용처와 금액은 (.*)나 (\d+) 등으로 반드시 그룹화할 것). 
                원문: {input_text}
                """
                
                response = model.generate_content(prompt)
                res_json = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                
                new_entry = {
                    "date": now_date,
                    "time": now_time,
                    "raw": input_text,
                    "card": res_json.get('card', '결제수단 불명'),
                    "store": res_json.get('store', '사용처 불명'),
                    "amount": res_json.get('amount', '0'),
                    "method": "❓ 신규 로직 검토 중",
                    "pattern_id": "NEW",
                    "color": "orange"
                }
                st.session_state.history.insert(0, new_entry)
                
                st.session_state.temp_logic = {
                    "regex": res_json['regex'],
                    "card": res_json.get('card', '알수없음'),
                    "store": res_json.get('store', '알수없음'),
                    "amount": res_json.get('amount', '0') 
                }
                st.rerun()
            except Exception as e:
                st.error(f"분석 실패: {e}")

# --- [2단] 파싱 히스토리 ---
st.subheader("📋 파싱 히스토리")
if not st.session_state.history:
    st.info("아직 처리된 내역이 없습니다.")
else:
    for entry in st.session_state.history:
        pid = entry.get('pattern_id', '-')
        title = f"[{entry['date']}] 💳 {entry['card']} | 🏪 {entry['store']} 💸 {entry['amount']}원 (Pattern #{pid})"
        
        with st.expander(title, expanded=True):
            st.caption(f"시간: {entry['time']} | 상태: :{entry['color']}[{entry['method']}]")
            st.markdown(f"> {entry['raw']}")

# --- [3단] 로직 리스트 (마법 잉크병) ---
st.divider()
st.subheader("🔮 마법 잉크병 (로직 리스트)")
if not st.session_state.logic_db:
    st.write("아직 학습된 패턴이 없습니다.")
else:
    for i, logic in enumerate(st.session_state.logic_db):
        logic_idx = len(st.session_state.logic_db) - i
        col_code, col_del = st.columns([0.85, 0.15])
        
        with col_code:
            st.code(f"#{logic_idx} | 💳 {logic['card']} (기준 가맹점: {logic['store']})\n{logic['regex']}", language="regex")
        
        with col_del:
            if st.button("🗑️", key=f"del_{logic_idx}"):
                st.session_state.logic_db.pop(i)
                st.toast(f"Pattern #{logic_idx} 삭제됨")
                st.rerun()
