from datetime import datetime
import re
import requests
import streamlit as st
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="학교 급식 찾아보기", page_icon="🍱", layout="centered")

st.title("🍱 학교 급식 찾아보기")

# 1. 학교 이름 줄임말 변환 함수
def expand_school_name(name: str) -> str:
    """줄여 쓴 학교 이름을 정식 명칭 형태 단어로 변환합니다."""
    replaced = name
    replacements = [
        ("여고", "여자고등학교"),
        ("남고", "남자고등학교"),
        ("공고", "공업고등학교"),
        ("상고", "상업고등학교"),
        ("농고", "농업고등학교"),
        ("체고", "체육고등학교"),
        ("예고", "예술고등학교"),
        ("외고", "외국어고등학교"),
        ("과고", "과학고등학교"),
        ("고", "고등학교"),
        ("여중", "여자중학교"),
        ("중", "중학교"),
        ("초", "초등학교"),
    ]
    for old, new in replacements:
        if old in replaced:
            replaced = replaced.replace(old, new)
            break
    return replaced

# 2. 학교 검색 API 호출 함수
def search_school(school_name: str):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {
        "Type": "json",
        "SCHUL_NM": school_name,
        "pSize": 5
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        # API 오류 응답 처리
        if "RESULT" in data:
            return []
            
        if "schoolInfo" in data:
            rows = data["schoolInfo"][1]["row"]
            schools = []
            for row in rows:
                schools.append({
                    "name": row.get("SCHUL_NM", ""),
                    "office_code": row.get("ATPT_OFCDC_SC_CODE", ""),
                    "school_code": row.get("SD_SCHUL_CODE", ""),
                    "location": row.get("LCTN_SC_NM", "지역 정보 없음")
                })
            return schools
    except Exception:
        return []
    
    return []

# 3. 급식 정보 API 호출 함수
def get_meal_info(office_code: str, school_code: str, date_str: str):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": date_str,
        "MLSV_TO_YMD": date_str,
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if "RESULT" in data:
            code = data["RESULT"].get("CODE")
            if code == "INFO-200":
                return None, "해당 날짜에 등록된 중식 급식 정보가 없습니다."
            else:
                return None, f"급식 정보를 불러오는 중 오류가 발생했습니다. (코드: {code})"
                
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            if rows:
                meal_data = rows[0]
                ddish_nm = meal_data.get("DDISH_NM", "")
                cal_info = meal_data.get("CAL_INFO", "정보 없음")
                return {"menu": ddish_nm, "calories": cal_info}, None
                
    except Exception as e:
        return None, "급식 정보를 불러오는 중 네트워크 오류가 발생했습니다."
        
    return None, "급식 정보를 찾을 수 없습니다."

# --- 화면 UI 구성 ---

# 검색어 입력
search_query = st.text_input("학교 이름을 입력하세요", placeholder="예: 수도여고, 서울고, 한국초")

selected_school = None

if search_query.strip():
    # 1차 검색
    schools = search_school(search_query.strip())
    
    # 1차 검색 결과가 없으면 줄임말을 풀어 2차 검색 진행
    if not schools:
        expanded_query = expand_school_name(search_query.strip())
        if expanded_query != search_query.strip():
            schools = search_school(expanded_query)
            
    if not schools:
        st.warning("입력하신 이름으로 검색된 학교가 없습니다. 학교명을 다시 확인해 주세요.")
    else:
        # 셀렉트박스로 학교 선택 (지역명 병기)
        options = [f"{s['name']} ({s['location']})" for s in schools]
        selected_index = st.selectbox(
            "학교를 선택해 주세요:",
            range(len(options)),
            format_func=lambda x: options[x]
        )
        selected_school = schools[selected_index]

st.divider()

# 날짜 선택 (기본값: 한국 시간 기준 오늘)
korea_tz = pytz.timezone("Asia/Seoul")
today_korea = datetime.now(korea_tz).date()

selected_date = st.date_input("날짜를 선택하세요", value=today_korea)

# 급식 정보 조회
if selected_school and selected_date:
    formatted_date = selected_date.strftime("%Y%m%d")
    
    with st.spinner("급식 정보를 불러오는 중입니다..."):
        meal_result, error_msg = get_meal_info(
            selected_school["office_code"],
            selected_school["school_code"],
            formatted_date
        )
        
    st.subheader(f"🍱 {selected_school['name']} 중식 메뉴")
    st.caption(f"날짜: {selected_date.strftime('%Y년 %m월 %d일')}")
    
    if error_msg:
        st.info(error_msg)
    elif meal_result:
        # 메뉴 가공 (<br/>를 줄바꿈으로 변경)
        raw_menu = meal_result["menu"]
        clean_menu_items = [item.strip() for item in re.split(r"<br\s*/?>", raw_menu) if item.strip()]
        
        st.markdown("### 📋 오늘의 식단")
        for item in clean_menu_items:
            st.write(f"- {item}")
            
        st.write("")
        st.info(f"🔥 **칼로리 정보:** {meal_result['calories']}")
