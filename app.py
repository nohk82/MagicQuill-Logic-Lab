import streamlit as st
import google.generativeai as genai
import re
import json
import csv
import io
from datetime import datetime
from github import Github

# --- 페이지 설정 ---
st.set_page_config(page_title="MagicQuill: Logic Lab", layout="centered", page_icon="🖋️")

# --- 세션 상태 초기화 ---
if "history" not in st.session_state:
    st.session_state.history = []
if "logic_db" not in st.session_state:
    st.session_state.logic_db = []
if "temp_logic" not in st.session_state:
    st.session_state.temp_logic = None

# --- GitHub 저장 함수 (Push) ---
def save_to_github(token, repo_name, history_data, logic_data):
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # CSV 변환 (type 필드 추가됨)
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["date", "time", "card", "store", "amount", "type", "method", "pattern_id", "raw", "color"])
        writer.writeheader()
        writer.writerows(history_data)
        csv_content = csv_buffer.getvalue()
        
        # JSON 변환
        json_content = json.dumps(logic_data, ensure_ascii=False, indent=2)
        
        for path, content, msg in [
            ("data/history.csv", csv_content, "Update parsing history"),
            ("data/logic.json", json_content, "Update magic logic db")
        ]:
            try:
                contents = repo.get_contents(path)
                repo.update_file(contents.path, msg, content, contents.sha)
            except:
                repo.create_file(path, msg, content)
        return True, "저장 성공!"
    except Exception as e:
        return False, str(e)

# --- GitHub 불러오기 함수 (Pull) ---
def load_from_github(token, repo_name):
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        logic_file = repo.get_contents("data/logic.json")
        logic_data = json.loads(logic_file.decoded_content.decode('utf-8'))
        
        history_file = repo.get_contents("data/history.csv")
        csv_content = history_file.decoded_content.decode('utf-8-sig', errors='ignore')
        reader = csv.DictReader(io.StringIO(csv_content))
        history_data = list(reader)
        
        return True, history_data, logic_data
    except Exception as e:
        return False, str(e), None

# --- 타이틀 ---
st.title("🖋️ MagicQuill: Logic Stack v2.9")
st.caption("AI 강제 JSON 모드 및 자산 기준 분류 시스템 탑재")
st.markdown("---")

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    st.subheader("☁️ GitHub Sync")
    gh_token = st.text_input("GitHub Token (PAT)", type="password")
    gh_repo = st.text_input("Repository", placeholder="username/repo-name")
    
    col_save, col_load = st.columns(2)
    if col_save.button("🚀 저장(Push)", use_container_width=True):
        if not gh_token or not gh_repo:
            st.warning("토큰과 저장소 이름을 입력하세요.")
        else:
            with st.spinner("저장 중..."):
                success, msg = save_to_github(gh_token, gh_repo, st.session_state.history, st.session_state.logic_db)
                if success:
                    st.success("GitHub에 저장 완료!"); st.balloons()
                else:
                    st.error(f"실패: {msg}")

    if col_load.button("📥 로드(Pull)", use_container_width=True):
        if not gh_token or not gh_repo:
            st.warning("토큰과 저장소 이름을 입력하세요.")
        else:
            with st.spinner("불러오는 중..."):
                success, h_data, l_data = load_from_github(gh_token, gh_repo)
                if success:
                    st.session_state.history = h_data
                    st.session_state.logic_db = l_data
                    st.success("데이터를 성공적으로 불러왔습니다!"); st.rerun() 
                else:
                    st.error(f"데이터가 없거나 권한이 없습니다: {h_data}")

    st.divider()
    if st.button("🗑️ 화면 초기화 (Memory Clear)"):
        st.session_state.clear(); st.rerun()

# --- 신규 로직 승인창 ---
if st.session_state.temp_logic:
    with st.container(border=True):
        st.warning("✨ **새로운 패턴을 발견했습니다! 저장할까요?**")
        tl = st.session_state.temp_logic
        st.info(f"💡 **AI 설명:** {tl.get('desc', '설명 없음')}")
        st.write(f"**추출 결과:** [{tl.get('type', '지출')}] 💳 {tl['card']} | 🏪 {tl['store']} | 💸 {tl['amount']}원")
        st.code(tl['regex'], language="regex")
        
        col_ok, col_no = st.columns(2)
        if col_ok.button("✅ 로직 저장 및 적용", use_container_width=True):
            st.session_state.logic_db.insert(0, st.session_state.temp_logic)
            new_pattern_id = len(st.session_state.logic_db)
            if st.session_state.history:
                st.session_state.history[0]['pattern_id'] = new_pattern_id
                st.session_state.history[0]['method'] = "✅ 신규 로직 학습됨"
            st.session_state.temp_logic = None
            st.rerun()
        if col_no.button("❌ 무시", use_container_width=True):
            st.session_state.temp_logic = None
            st.rerun()

# --- 엔진 가동 (텍스트 입력) ---
input_text = st.text_input("📩 새로운 금융 알림 문구를 입력하세요", key="input_text")
if st.button("MagicQuill 실행 ✨", use_container_width=True):
    if not api_key:
        st.error("API Key를 입력하세요.")
    elif input_text:
        now_date = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M:%S")
        
        # 기존 로직 매칭 시도
        matched_idx = -1
        for i, logic in enumerate(st.session_state.logic_db):
            if re.search(logic['regex'], input_text):
                matched_idx = len(st.session_state.logic_db) - i
                matched_logic = logic
                break
        
        if matched_idx != -1:
            match = re.search(matched_logic['regex'], input_text)
            groups = match.groups()
            amount_val = next((g for g in groups if any(c.isdigit() for c in g)), "금액확인")
            store_val = next((g for g in groups if not any(c.isdigit() for c in g)), matched_logic['store'])
            new_entry = {
                "date": now_date, "time": now_time, "raw": input_text, 
                "card": matched_logic['card'], "store": store_val, "amount": amount_val, 
                "type": matched_logic.get('type', '지출'),
                "method": "✅ 기존 로직 매칭", "pattern_id": matched_idx, "color": "green"
            }
            st.session_state.history.insert(0, new_entry)
        else:
            # 💡 AI 분석 (안정적인 2.5 Flash + 강제 JSON 모드)
            try:
                genai.configure(api_key=api_key)
                
                # 모델 변경 및 JSON 모드 활성화
                model = genai.GenerativeModel(
                    "gemini-2.5-flash",
                    generation_config={"response_mime_type": "application/json"}
                )
                
                prompt = f"""
                다음 금융 알림 문자를 분석해서, 정확히 아래 제공된 JSON 형식에 맞춰서 데이터만 출력해.
                
                [분류 기준]
                - '입금': [은행 계좌]로 돈이 들어오는 모든 경우 (월급, 이자, 배당금, 타행이체 등)
                - '수입': [계좌 외 자산]이 늘어나는 경우 (카드 취소/환불, 페이 충전 등)
                - '출금': [은행 계좌]에서 돈이 나가는 경우 (이체, 현금 인출 등)
                - '지출': [카드/페이] 등으로 일반적인 결제 및 소비를 하는 경우
                
                [출력 형식]
                {{
                  "card": "결제수단/카드사/은행명",
                  "store": "상호명/사용처",
                  "amount": "숫자만 (예: 10000)",
                  "type": "입금, 출금, 지출, 수입 중 택 1",
                  "regex": "^로 시작하고 도구명이 포함된 정규식 (절대 .*로 시작 금지)",
                  "desc": "이 정규식에 대한 1문장 설명"
                }}
                
                원문: {input_text}
                """
                
                response = model.generate_content(prompt)
                
                # 💡 강제 JSON 모드 덕분에 복잡한 정규식 추출 불필요!
                res_json = json.loads(response.text)
                
                new_entry = {
                    "date": now_date, "time": now_time, "raw": input_text, 
                    "card": res_json.get('card', '알수없음'), "store": res_json.get('store', '알수없음'), 
                    "amount": res_json.get('amount', '0'), "type": res_json.get('type', '지출'),
                    "method": "❓ 신규 로직 검토 중", "pattern_id": "NEW", "color": "orange"
                }
                st.session_state.history.insert(0, new_entry)
                
                st.session_state.temp_logic = {
                    "regex": res_json.get('regex', ''), "card": res_json.get('card', '알수없음'), 
                    "store": res_json.get('store', '알수없음'), "amount": res_json.get('amount', '0'),
                    "type": res_json.get('type', '지출'), "desc": res_json.get('desc', '')
                }
                st.rerun()
                    
            except Exception as e:
                st.error(f"AI 통신/분석 에러: {e}")

# --- 하단 리스트 레이아웃 ---
st.subheader("📋 파싱 히스토리")
if not st.session_state.history:
    st.info("아직 처리된 내역이 없습니다.")
else:
    for entry in st.session_state.history:
        pid = entry.get('pattern_id', '-')
        t_type = entry.get('type', '지출')
        t_icon = {"입금":"💰", "수입":"➕", "출금":"📤", "지출":"💸"}.get(t_type, "📝")
        
        title = f"[{entry['date']}] {t_icon} {t_type} | 💳 {entry['card']} | 🏪 {entry['store']} 💸 {entry['amount']}원"
        with st.expander(title, expanded=True):
            st.caption(f"시간: {entry['time']} | 패턴: #{pid} | 상태: :{entry['color']}[{entry['method']}]")
            st.markdown(f"> {entry['raw']}")

st.divider()
st.subheader("🔮 마법 잉크병 (로직 리스트)")
if not st.session_state.logic_db:
    st.write("아직 학습된 패턴이 없습니다.")
else:
    for i, logic in enumerate(st.session_state.logic_db):
        logic_idx = len(st.session_state.logic_db) - i
        col_code, col_del = st.columns([0.85, 0.15])
        with col_code:
            st.markdown(f"**📝 {logic.get('type', '지출')} 로직:** {logic.get('desc', '설명 없음')}")
            st.code(f"#{logic_idx} | 💳 {logic['card']}\n{logic['regex']}", language="regex")
        with col_del:
            if st.button("🗑️", key=f"del_{logic_idx}"):
                st.session_state.logic_db.pop(i)
                st.rerun()
