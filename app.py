import streamlit as st
import google.generativeai as genai
import re
import json

# 페이지 설정
st.set_page_config(page_title="MagicQuill Logic Lab", layout="wide", page_icon="🖋️")

# 타이틀 및 테마
st.title("🖋️ MagicQuill: AI 로직 실험실")
st.markdown("---")
st.caption("AI가 스스로 파싱 로직(Regex)을 써 내려가는 MagicQuill의 핵심 엔진 테스트 공간입니다.")

# 사이드바: API 및 설정
with st.sidebar:
    st.header("⚙️ MagicQuill Settings")
    api_key = st.text_input("Gemini API Key", type="password", help="Google AI Studio에서 발급받은 키를 입력하세요.")
    model_name = st.selectbox("Intelligence Level", [
    "gemini-3-flash-preview",   # 가장 빠르고 효율적인 모델 (추천)
    "gemini-3.1-pro-preview"    # 더 복잡한 로직 생성 시 유리함
])
    st.divider()
    st.info("여기서 완성된 정규표현식은 MagicQuill 앱의 내부 DB에 저장되어 마법 같은 자동 가계부를 완성합니다.")

# 메인 UI Layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📩 알림 원문 입력 (Input)")
    raw_text = st.text_area(
        "금융 앱 푸시 알림 문구를 그대로 입력하세요.",
        placeholder="예: [매출취소안내] 01일 / -60,000 원 / 네이버페이",
        height=180
    )
    analyze_btn = st.button("✨ 마법의 로직 생성", type="primary", use_container_width=True)

# AI 분석 프로세스
if analyze_btn:
    if not api_key:
        st.error("사이드바에 API Key를 입력해야 마법이 시작됩니다.")
    elif not raw_text:
        st.warning("분석할 텍스트가 필요합니다.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            
            # MagicQuill 전용 프롬프트
            prompt = f"""
            너는 가계부 앱 'MagicQuill'의 데이터 파싱 전문가야. 
            아래 텍스트에서 결제 정보를 추출하고, 향후 동일 패턴을 처리할 정규표현식을 생성해줘.
            
            [분석할 원문]: {raw_text}
            
            다음 JSON 형식으로만 응답해:
            1. 'store': 가맹점명 혹은 입출금처
            2. 'amount': 숫자만 추출 (취소/출금은 마이너스 기호 필수)
            3. 'type': 거래 유형 (BUY, CANCEL, DEPOSIT 등)
            4. 'suggested_regex': 이 문자와 동일한 패턴을 완벽히 잡는 Python 정규표현식. 
               (상호명이나 금액 같은 변수는 (.*)나 (\d+) 등으로 그룹핑할 것)
            
            순수 JSON 데이터만 출력해.
            """
            
            with st.spinner("MagicQuill이 로직을 써 내려가는 중..."):
                response = model.generate_content(prompt)
                clean_res = response.text.replace("```json", "").replace("```", "").strip()
                result = json.loads(clean_res)
                
            with col2:
                st.subheader("📜 생성된 로직 (Output)")
                st.json(result)
                
                st.success(f"**추천 정규표현식:** `{result['suggested_regex']}`")
                
                # 실시간 검증 (Sandbox)
                st.divider()
                st.subheader("🧪 로직 검증 테스트")
                test_text = st.text_input("금액이나 날짜를 바꿔서 테스트해보세요:", value=raw_text)
                
                try:
                    match = re.search(result['suggested_regex'], test_text)
                    if match:
                        st.balloons() # 매칭 성공 시 축하 효과
                        st.write("✅ **매칭 성공!** 추출된 그룹 데이터:")
                        st.code(match.groups())
                    else:
                        st.error("❌ 매칭 실패. 로직 보정이 필요합니다.")
                except Exception as e:
                    st.error(f"정규식 테스트 중 오류: {e}")
                    
        except Exception as e:
            st.error(f"마법이 실패했습니다: {e}")

st.divider()
st.caption("© 2026 MagicQuill Project - 가볍고 영리한 가계부의 시작")
