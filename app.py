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

# --- GitHub 저장 함수 ---
def save_to_github(token, repo_name, history_data, logic_data):
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # 1. 히스토리 저장 (CSV)
        csv_buffer = io.StringIO()
        fieldnames = ["date", "time", "card", "store", "amount", "type", "method", "pattern_id", "raw", "color"]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history_data)
        csv_content = csv_buffer.getvalue()
        
        # 2. 로직 저장 (JSON - desc 필드 포함)
        json_content = json.dumps(logic_data, ensure_ascii=False, indent=2)
        
        for path, content, msg in [
            ("data/history.csv", csv_content, "Update parsing history v2.8"),
            ("data/logic.json", json_content, "Update magic logic db v2.8")
        ]:
            try:
                contents = repo.get_contents(path)
                repo.update_file(contents.path, msg, content, contents.sha)
            except:
                repo.create_file(path, msg, content)
        return True, "저장 성공!"
    except Exception as e:
        return False, str(e)

# --- GitHub 불러오기 함수 ---
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

st.title("🖋️ MagicQuill: Logic Stack v2.8")
st.caption("대표님의 직관적인 '설명' 기능이 추가된 업그레이드 버전")
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
        success, msg = save_to_github(gh_token, gh_repo, st.session_state.history, st.session_state.logic_db)
        if success: st.success("저장 완료!"); st.balloons()
        else: st.error(f"실패: {msg}")
    if col_load.button("📥 로드(Pull)", use_container_width=True):
        success, h_data, l_data = load_from_github(gh_token, gh_repo)
        if success:
            st.session_state.history = h_data
            st.session_state.logic_db = l_data
            st.success("데이터 로드 완료!"); st.rerun()
        else: st.error(f"로드 실패: {h_data}")

# --- 신규 로직 승인창 (설명 필드 추가) ---
if st.session_state.temp_logic:
    with st.container(border=True):
        st.warning("✨ **새로운 패턴을 발견했습니다! 저장할까요?**")
        tl = st.session_state.temp_logic
        st.info(f"💡 **AI의 로직 설명:** {tl.get('desc', '설명 없음')}")
        st.write(f"**추출 결과:** [{tl['type']}] 💳 {tl['card']} | 🏪 {tl['store']} | 💸 {tl['amount']}원")
        st.code(tl['regex'], language="regex")
        
        # 사용자가 직접 설명을 수정할 수도 있게 텍스트 입력창 제공
        user_desc = st.text_input("설명 수정 (필요시)", value=tl.get('desc', ''))
        
        col_ok, col_no = st.columns(2)
        if col_ok.button("✅ 로직 저장 및 적용", use_container_width=True):
            tl['desc'] = user_desc # 수정한 설명 적용
            st.session_state.logic_db.insert(0, tl)
            new_id = len(st.session_state.logic_db)
            if st.session_state.history:
                st.session_state.history[0]['pattern_id'] = new_id
                st.session_state.history[0]['method'] = "✅ 신규 로직 학습됨"
            st.session_state.temp_logic = None
            st.rerun()
        if col_no.button("❌ 무시", use_container_width=True):
            st.session_state.temp_logic = None
            st.rerun()

# --- 메인 엔진 가동 ---
input_text = st.text_input("📩 금융 알림 문구를 입력하세요", key="input_text")
if st.button("MagicQuill 실행 ✨", use_container_width=True):
    if not api_key: st.error("API Key를 입력하세요.")
    elif input_text:
        now_date = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M:%S")
        
        matched_idx = -1
        for i, logic in enumerate(st.session_state.logic_db):
            if re.search(logic['regex'], input_text):
                matched_idx = len(st.session_state.logic_db) - i
                matched_logic = logic
                break
        
        if matched_idx != -1:
            match = re.search(matched_logic['regex'], input_text)
            groups = match.groups()
            amount_val = next((g for g in groups if any(c.isdigit() for c in g)), "0")
            store_val = next((g for g in groups if not any(c.isdigit() for c in g)), matched_logic['store'])
            new_entry = {
                "date": now_date, "time": now_time, "raw": input_text, 
                "card": matched_logic['card'], "store": store_val, "amount": amount_val,
                "type": matched_logic.get('type', '지출'),
                "method": f"✅ 기존 로직 매칭 (#{matched_idx})", "pattern_id": matched_idx, "color": "green"
            }
            st.session_state.history.insert(0, new_entry)
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-3.1-flash-lite")
                # 프롬프트에 6.desc 항목 추가
                prompt = f"""
                금융 문자를 분석해 JSON만 출력해:
                1.card: 카드사/은행명
                2.store: 상호/사용처
                3.amount: 숫자만
                4.type: '입금', '출금', '지출', '수입' 중 하나 (수입은 계좌외 자산증가, 입금은 계좌입금)
                5.regex: 상호와 금액을 그룹화한 정규식 (^로 시작하고 도구명 포함)
                6.desc: 이 정규식이 어떤 문자를 어떤 조건으로 파싱하는지에 대한 1문장 설명
                원문: {input_text}
                """
                response = model.generate_content(prompt)
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    res = json.loads(json_match.group(0))
                    new_entry = {
                        "date": now_date, "time": now_time, "raw": input_text,
                        "card": res['card'], "store": res['store'], "amount": res['amount'],
                        "type": res['type'], "method": "❓ 신규 로직 검토 중", "pattern_id": "NEW", "color": "orange"
                    }
                    st.session_state.history.insert(0, new_entry)
                    st.session_state.temp_logic = {
                        "regex": res['regex'], "card": res['card'], "store": res['store'], 
                        "amount": res['amount'], "type": res['type'], "desc": res.get('desc', '')
                    }
                    st.rerun()
            except Exception as e: st.error(f"분석 실패: {e}")

# --- 하단 리스트 레이아웃 ---
st.subheader("📋 파싱 히스토리")
for entry in st.session_state.history:
    # 💡 여기서부터는 반드시 스페이스바 4칸(또는 Tab 1번)이 들어가야 합니다!
    t_type = entry.get('type', '지출') 
    t_icon = {"입금":"💰", "수입":"➕", "출금":"📤", "지출":"💸"}.get(t_type, "📝")
    
    # 나머지 데이터들도 안전하게 .get()으로 가져오도록 보강했습니다.
    pid = entry.get('pattern_id', '-')
    e_date = entry.get('date', '0000-00-00')
    e_card = entry.get('card', '알 수 없음')
    e_store = entry.get('store', '상호 미상')
    e_amount = entry.get('amount', '0')
    e_time = entry.get('time', '00:00:00')
    e_raw = entry.get('raw', '내용 없음')

    title = f"[{e_date}] {t_icon} {t_type} | 💳 {e_card} | 🏪 {e_store} | {e_amount}원"
    
    with st.expander(title, expanded=True):
        st.caption(f"시간: {e_time} | 패턴: #{pid}")
        st.markdown(f"> {e_raw}")

st.divider()
st.subheader("🔮 마법 잉크병 (로직 리스트)")
for i, logic in enumerate(st.session_state.logic_db):
    logic_idx = len(st.session_state.logic_db) - i
    col_code, col_del = st.columns([0.85, 0.15])
    with col_code:
        # 설명 필드 표시 (마크다운 주석 스타일)
        st.markdown(f"**📝 로직 설명:** {logic.get('desc', '설명 없음')}")
        st.code(f"#{logic_idx} | [{logic['type']}] 💳 {logic['card']}\n{logic['regex']}", language="regex")
    with col_del:
        if st.button("🗑️", key=f"del_{logic_idx}"):
            st.session_state.logic_db.pop(i); st.rerun()
