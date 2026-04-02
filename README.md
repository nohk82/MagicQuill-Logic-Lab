# 🖋️ MagicQuill: AI Logic Lab

**MagicQuill**은 금융 앱 푸시 알림에서 데이터를 정교하게 추출하기 위한 AI 로직 실험실입니다. 
생성형 AI(Gemini)를 활용하여 비정형 문자열에서 상호명, 금액을 파싱하고, 이를 자동화할 수 있는 **정규표현식(Regex)**을 마법처럼 생성합니다.

## ✨ 주요 기능
- **AI 파싱:** 금융 알림 원문을 분석하여 JSON 데이터로 변환
- **로직 생성:** 동일 패턴 처리를 위한 Python 정규표현식(Regex) 자동 생성
- **샌드박스 테스트:** 생성된 로직이 실제 데이터와 일치하는지 즉석 검증

## 🛠️ 시작하기

### 1. 필수 조건
- Python 3.9+
- [Google AI Studio](https://aistudio.google.com/)에서 발급받은 Gemini API Key

### 2. 로컬 실행 방법
```bash
# 저장소 복제
git clone [https://github.com/사용자이름/MagicQuill-Lab.git](https://github.com/사용자이름/MagicQuill-Lab.git)
cd MagicQuill-Lab

# 라이브러리 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py
