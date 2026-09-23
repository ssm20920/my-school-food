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
from collections import Counter
from datetime import datetime
import calendar
import re
import requests
import streamlit as st
import pytz

# 페이지 기본 설정
st.set_page_config(
    page_title="송탄고 급식 분석 - 반찬 반복 횟수",
    page_icon="📅",
    layout="wide"
)

st.title("📅 송탄고등학교 월간 급식 분석")
st.subheader("같은 반찬이 한 달에 몇 번이나 나왔을까?")

# 송탄고등학교 고정 정보 (경기도교육청 J10 / 송탄고등학교 7530480)
ATPT_OFCDC_SC_CODE = "J10"
SD_SCHUL_CODE = "7530480"

# 1. 메뉴명 정제 및 알레르기 번호 제거 함수
def clean_dish_name(dish_text: str, remove_allergy_only: bool = False) -> str:
    """
    메뉴명에서 괄호 안 알레르기 번호를 제거하거나,
    통계용으로 특수문자까지 깔끔하게 지운 순수 반찬명을 반환합니다.
    """
    # 괄호와 안쪽 알레르기 숫자/점 제거 (예: "제육볶음(10.13.)" -> "제육볶음")
    cleaned = re.sub(r"\([0-9\.\s]+\)", "", dish_text).strip()
    
    if remove_allergy_only:
        return cleaned
    
    # 반복 횟수 집계를 위해 기타 특수문자 제거
    cleaned = re.sub(r"[^\w\s가-힣]", "", cleaned).strip()
    return cleaned

# 2. 한 달 전체 급식 데이터 API 호출 함수
def get_monthly_meal_data(year: int, month: int):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    
    # 해당 월의 시작일과 마지막 날 계산
    _, last_day = calendar.monthrange(year, month)
    from_date = f"{year}{month:02d}01"
    to_date = f"{year}{month:02d}{last_day:02d}"
    
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": from_date,
        "MLSV_TO_YMD": to_date,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "RESULT" in data and data["RESULT"].get("CODE") == "INFO-200":
            return None, "급식이 없는 날입니다 (해당 월 급식 데이터가 없습니다)."
            
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            return rows, None
            
    except Exception:
        return None, "급식 데이터를 불러오는 중 네트워크 오류가 발생했습니다."
        
    return None, "급식이 없는 날입니다."

# --- UI 컨트롤 영역 (나란히 배치) ---
korea_tz = pytz.timezone("Asia/Seoul")
today_korea = datetime.now(korea_tz).date()

col_date, col_toggle = st.columns([2, 1], vertical_alignment="center")

with col_date:
    # 달력에서 날짜를 고르면 해당 연/월 전체를 분석합니다.
    selected_date = st.date_input("조회할 달의 날짜 선택", value=today_korea)

with col_toggle:
    show_allergy = st.toggle("알레르기 정보 보기", value=True)

st.divider()

# --- 데이터 조회 및 처리 ---
selected_year = selected_date.year
selected_month = selected_date.month
selected_ymd_str = selected_date.strftime("%Y%m%d")

with st.spinner(f"송탄고등학교 {selected_year}년 {selected_month}월 급식 데이터를 수집 중..."):
    monthly_rows, error_msg = get_monthly_meal_data(selected_year, selected_month)

if error_msg or not monthly_rows:
    st.info(f"💡 {error_msg}")
else:
    # 선택한 날짜의 데이터 찾아두기
    target_day_row = None
    dish_counter = Counter()
    total_days = len(monthly_rows)

    for row in monthly_rows:
        ymd = row.get("MLSV_YMD", "")
        ddish_nm = row.get("DDISH_NM", "")
        
        if ymd == selected_ymd_str:
            target_day_row = row
            
        # 한 달 동안의 모든 반찬 세기
        raw_dishes = re.split(r"<br\s*/?>", ddish_nm)
        for raw in raw_dishes:
            cleaned = clean_dish_name(raw, remove_allergy_only=False)
            if cleaned:
                dish_counter[cleaned] += 1

    # --- 1. 선택한 날짜의 급식 정보 표시 ---
    st.markdown(f"### 🍽️ {selected_date.strftime('%Y년 %m월 %d일')} 식단 카드")
    
    if target_day_row:
        raw_menu = target_day_row.get("DDISH_NM", "")
        cal_info = target_day_row.get("CAL_INFO", "정보 없음")
        
        # 원본 메뉴 리스트
        raw_menu_items = [item.strip() for item in re.split(r"<br\s*/?>", raw_menu) if item.strip()]
        
        # 알레르기 정보 스위치에 맞춰 표시 단어 가공
        if show_allergy:
            display_menu_items = raw_menu_items
        else:
            display_menu_items = [clean_dish_name(item, remove_allergy_only=True) for item in raw_menu_items]
            
        # 큰 숫자 카드 (Metric) 표시
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="🥗 선택한 날의 메뉴 가짓수", value=f"{len(display_menu_items)}개")
        with col_m2:
            st.metric(label="🔥 선택한 날의 칼로리", value=cal_info)
            
        st.write("")
        
        # 메뉴 카드를 여러 열로 나란히 배치 (한 줄에 4개씩)
        cols_per_row = 4
        for i in range(0, len(display_menu_items), cols_per_row):
            row_items = display_menu_items[i : i + cols_per_row]
            cols = st.columns(len(row_items))
            for idx, item in enumerate(row_items):
                with cols[idx]:
                    with st.container(border=True):
                        st.markdown(f"**{item}**")
    else:
        st.warning("선택하신 날짜는 급식이 없는 날입니다.")

    st.write("")
    st.divider()

    # --- 2. 한 달 동안의 반찬 반복 횟수 통계 ---
    st.markdown(f"### 📊 {selected_year}년 {selected_month}월 반찬 반복 등장 통계 (총 {total_days}일 제공)")

    # 2회 이상 반복된 반찬 필터링 및 정렬
    repeated_dishes = {dish: count for dish, count in dish_counter.items() if count > 1}
    sorted_repeated = sorted(repeated_dishes.items(), key=lambda x: x[1], reverse=True)

    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric(label="🔄 2회 이상 반복 나온 반찬 종류", value=f"{len(repeated_dishes)}종")
    with col_stat2:
        max_dish = sorted_repeated[0] if sorted_repeated else ("없음", 0)
        st.metric(label="👑 최다 등장 반찬", value=f"{max_dish[0]} ({max_dish[1]}회)")

    st.write("")

    if sorted_repeated:
        st.markdown("#### 🔁 한 달 동안 반복해서 나온 반찬 목록")
        # 반찬 카드로 나란히 보여주기 (4열씩 배치)
        cols_per_row = 4
        for i in range(0, len(sorted_repeated), cols_per_row):
            row_items = sorted_repeated[i : i + cols_per_row]
            cols = st.columns(len(row_items))
            for idx, (dish_name, count) in enumerate(row_items):
                with cols[idx]:
                    with st.container(border=True):
                        st.markdown(f"**{dish_name}**")
                        st.caption(f"한 달 동안 **{count}회** 등장")
    else:
        st.info("이번 달에는 2회 이상 중복해서 나온 반찬이 없습니다.")
