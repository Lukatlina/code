from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_all_job_details(url):
    """
    모든 컬럼의 데이터를 크롤링하고 DataFrame으로 반환합니다.
    """
    driver = None
    all_details = {}

    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.81 Safari/537.36'
        chrome_options.add_argument(f'user-agent={user_agent}')

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        logger.info(f"페이지 접속 완료: {url}")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-sentry-component="RecruitmentGuidelines"]'))
        )
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'application-section'))
        )
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'company-section'))
        )
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 새로운 제목 및 회사명 크롤링 함수 호출
        all_details['제목'] = scrape_job_title(soup)
        all_details['회사명'] = scrape_company_name(soup)

        all_details.update(scrape_recruitment_guidelines_section(soup))
        all_details.update(scrape_qualification_section(soup))
        all_details.update(scrape_application_section(soup))
        all_details.update(scrape_company_section(soup))

        columns = [
            '제목', '회사명', '모집분야', '모집인원', '고용형태', '직급/직책', '급여', '근무시간', 
            '근무지주소', '인근지하철', '경력', '학력', '스킬', '핵심역량', 
            '우대조건', '기본우대', '시작일', '마감일', '사원수', 
            '기업구분', '산업(업종)', '위치'
        ]
        for col in columns:
            if col not in all_details:
                all_details[col] = None

        return {'status': 'success', 'content': all_details}

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        return {'status': 'error', 'content': f"❌ 오류 발생: {e}"}
    finally:
        if driver:
            driver.quit()

# --- 제목 추출 함수 ---
def scrape_job_title(soup):
    h1_tag = soup.find('h1')
    return h1_tag.get_text(strip=True) if h1_tag else None

# --- 회사명 추출 함수 ---
def scrape_company_name(soup):
    h2_tag = soup.find('h2', class_=re.compile(r'Typography_variant_size20__.*'))
    return h2_tag.get_text(strip=True) if h2_tag else None

# --- 각 섹션별 데이터 추출 함수들 (기존 함수들) ---

def scrape_recruitment_guidelines_section(soup):
    details = {}
    recruitment_section = soup.find('div', attrs={'data-sentry-component': 'RecruitmentGuidelines'})
    if not recruitment_section: return {}

    for item in recruitment_section.find_all('div', attrs={'data-sentry-component': 'RecruitmentItem'}):
        try:
            key_tag = item.find('span', style=re.compile(r'min-width'))
            if not key_tag: continue
            key = key_tag.get_text(strip=True)
            value = None
            if key == '고용형태':
                value_tags = item.find_all('span', class_=re.compile(r'Typography_.*'))
                value = ' '.join([tag.get_text(strip=True) for tag in value_tags if tag.get_text(strip=True)])
            elif key == '인근지하철':
                subway_info_container = key_tag.find_next_sibling('div')
                if subway_info_container:
                    value = "".join(subway_info_container.stripped_strings)
            else:
                value_tag = item.find('span', class_=re.compile(r'Typography_color_gray900__.*'))
                value = value_tag.get_text(strip=True) if value_tag else None
            if value: details[key] = value
        except AttributeError:
            continue
    return details

def scrape_qualification_section(soup):
    details = {}
    qualification_section = soup.find('div', attrs={'data-sentry-component': 'Qualification'})
    if not qualification_section: return {}
    
    for item in qualification_section.find_all('div', attrs={'data-sentry-component': 'QualificationItem'}):
        try:
            key_tag = item.find('span', style=re.compile(r'min-width'))
            if not key_tag: continue
            key = key_tag.get_text(strip=True)
            value = None
            if key in ['경력', '학력']:
                value_tag = item.find('span', attrs={'data-accent-color': 'theme-primary'})
                value = value_tag.get_text(strip=True) if value_tag else None
            elif key in ['스킬', '핵심역량']:
                value_tag = item.find('span', attrs={'data-accent-color': 'gray900'})
                value = value_tag.get_text(strip=True) if value_tag else None
            elif key == '우대조건':
                preference_items = item.find_all('div', attrs={'data-sentry-component': 'PreferenceSubItem'})
                if preference_items:
                    preferences = {}
                    for pref_item in preference_items:
                        pref_key_tag = pref_item.find('span', attrs={'data-accent-color': 'gray500'})
                        ul_tag = pref_item.find('ul')
                        if pref_key_tag and ul_tag:
                            pref_key = pref_key_tag.get_text(strip=True)
                            li_tags = ul_tag.find_all('li')
                            texts = [li.get_text(strip=True) for li in li_tags]
                            preferences[pref_key] = ', '.join(texts)
                    value = json.dumps(preferences, ensure_ascii=False)
                else:
                    value_tag = item.find('span', attrs={'data-accent-color': 'gray900'})
                    value = value_tag.get_text(strip=True) if value_tag else None
            elif key == '기본우대':
                value_tag = item.find('span', attrs={'data-accent-color': 'gray900'})
                value = value_tag.get_text(strip=True) if value_tag else None
            if value: details[key] = value
        except AttributeError:
            continue
    return details

def scrape_application_section(soup):
    details = {}
    application_section = soup.find('div', id='application-section')
    if not application_section: return {}
    
    simple_table = application_section.find('div', attrs={'data-sentry-component': 'SimpleTable'})
    if simple_table:
        for item in simple_table.find_all('div', class_=re.compile(r'Flex_display_flex__.* Flex_gap_space12__.*')):
            key_tag = item.find('span', attrs={'data-accent-color': 'gray700'})
            value_tag = item.find('span', attrs={'data-accent-color': 'gray900'})
            if key_tag and value_tag:
                key = key_tag.get_text(strip=True)
                value = value_tag.get_text(strip=True)
                details[key] = value
    return details

def scrape_company_section(soup):
    details = {}
    company_section = soup.find('div', id='company-section')
    if not company_section: return {}
    
    info_boxes = company_section.find_all('div', attrs={'data-sentry-component': 'CorpInformationBox'})
    for box in info_boxes:
        try:
            key_element = box.find('span', class_=re.compile(r'Typography_variant_size13__'))
            key = key_element.get_text(strip=True)
            value_element = box.find('div', class_=re.compile(r'Typography_variant_size14__'))
            value = value_element.get_text(strip=True)
            details[key] = value
        except Exception:
            continue
    return details

def create_dataframe_and_save(data, filename="job_details.csv"):
    df = pd.DataFrame([data])
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    logger.info(f"✅ 데이터가 '{filename}' 파일로 성공적으로 저장되었습니다.")
    return df

if __name__ == "__main__":
    url = 'https://www.jobkorea.co.kr/Recruit/GI_Read/47655231?rPageCode=SL&logpath=21&sn=6&sc=611'
    result = scrape_all_job_details(url)
    
    if result['status'] == 'success':
        print("\n--- 통합 크롤링 성공 ---")
        df = create_dataframe_and_save(result['content'])
        print(df)
    else:
        print(f"❌ 크롤링 실패: {result['content']}")