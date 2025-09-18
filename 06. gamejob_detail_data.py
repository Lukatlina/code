import pandas as pd
import os
import time
import logging
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 각 섹션별 데이터 추출 함수들 (이전에 수정한 최종 함수들을 여기에 붙여넣기) ---
def scrape_all_job_details(url, driver):
    """
    모든 컬럼의 데이터를 크롤링하고 DataFrame으로 반환합니다.
    """
    all_details = {}
    
    # 💡 User-Agent 목록
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0'
    ]

    try:
        # 💡 매번 다른 User-Agent 설정
        random_user_agent = random.choice(user_agents)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": random_user_agent})
        
        # 💡 불규칙한 시간으로 페이지 로딩 대기
        random_wait_time = random.uniform(1, 3) # 2초 ~ 5초 사이의 무작위 값
        time.sleep(random_wait_time)

        driver.get(url)
        post_load_wait_time = random.uniform(1, 3) # 1초 ~ 3초 사이의 무작위 값
        time.sleep(post_load_wait_time)

        logger.info(f"페이지 접속 완료: {url}")


        # 💡 수정된 부분: 대기 시간을 3~6초 사이의 무작위 값으로 설정
        try:
            WebDriverWait(driver, 5).until(
				        EC.presence_of_element_located((By.ID, 'gibOutline'))
				    )
            logger.info("✅ '모집요강' 섹션 로딩 확인.")
        except TimeoutException:
            logger.warning("⚠️ 5초 내에 '모집요강' 섹션을 찾지 못했습니다. 페이지가 로딩되지 않았을 수 있습니다.")

				# 모집요강, 담당업무 및 자격요건, 수정일 및 등록일 함수 가져와서 저장
        all_details['URL'] = url
        all_details.update(scrape_dates(driver))
        all_details.update(scrape_gib_outline(driver))
        all_details.update(scrape_job_duties_and_qualifications(driver))


        columns = [
            'URL', '모집분야', '해당키워드','게임분야', '고용형태', '모집인원', '채용직급·직책', 
            '급여조건', '해당분야', '최종학력', '자격사항', '외국어 능력', '자격증', '수정일', '등록일'
        ]

        for col in columns:
            if col not in all_details:
                all_details[col] = None

        return {'status': 'success', 'content': all_details}

    except WebDriverException as e:
        logger.error(f"❌ WebDriver 오류 발생 (자동 재시작): {e}")
        return {'status': 'webdriver_error', 'content': str(e)}
    except Exception as e:
        logger.error(f"❌ 기타 오류 발생: {e}")
        return {'status': 'error', 'content': str(e)}

# --- 등록일, 수정일 추출 함수 ---
def scrape_dates(driver):
    dates = {'수정일': None, '등록일': None}

    # 정규 표현식 패턴: 콜론(:) 뒤에 있는 날짜와 시간을 추출 (예: '2025-09-10 19:06')
    date_pattern = r':\s*(.*)'

    try:
        # 모든 <p class="date"> 요소를 찾습니다.
        date_elements = driver.find_elements(By.CSS_SELECTOR, 'div#gibReadTop p.date')
        
        # 첫 번째 요소(수정일)와 두 번째 요소(등록일)의 텍스트를 추출합니다.
        # find_elements는 리스트를 반환하므로 인덱스로 접근합니다.
        if len(date_elements) > 0:
            modified_date_text = date_elements[0].text
            # 정규 표현식으로 날짜와 시간 추출
            match = re.search(date_pattern, modified_date_text)
            if match:
                dates['수정일'] = match.group(1).strip()
            # logger.info(f"✅ 수정일: {dates['수정일']} 추출 완료.")
        
        if len(date_elements) > 1:
            registered_date_text = date_elements[1].text
            # 정규 표현식으로 날짜와 시간 추출
            match = re.search(date_pattern, registered_date_text)
            if match:
                dates['등록일'] = match.group(1).strip()
            # logger.info(f"✅ 등록일: {dates['등록일']} 추출 완료.")

    except (NoSuchElementException, IndexError) as e:
        logger.warning(f"⚠️ 날짜 정보를 찾는 중 오류가 발생했습니다: {e}")

    return dates




# --- 모집요강 추출 함수 ---
def scrape_gib_outline(driver):
    """
    Selenium을 사용하여 '모집요강' 섹션의 정보를 추출합니다.
    
    Args:
        driver (WebDriver): Selenium WebDriver 객체.
    
    Returns:
        dict: 추출된 모집요강 정보.
    """
    gib_details = {
        '모집분야': None,
        '해당키워드': None,
        '게임분야': None,
        '고용형태': None,
        '모집인원': None,
        '채용직급·직책': None,
        '급여조건': None,
        '해당분야': None,  # 지원자격 테이블 내
        '연령': None,     # 지원자격 테이블 내
        '최종학력': None,  # 지원자격 테이블 내
        '성별': None,     # 지원자격 테이블 내
        '자격사항': None,  # 우대사항 내
        '외국어 능력': None, # 우대사항 내
        '자격증': None,    # 우대사항 내
        '사전인터뷰': None
    }
    try:
        # '모집요강' 섹션 찾기
        gib_outline_section = driver.find_element(By.ID, 'gibOutline')
        dl_tags = gib_outline_section.find_elements(By.TAG_NAME, 'dl')

        for dl_tag in dl_tags:
            dt_elements = dl_tag.find_elements(By.TAG_NAME, 'dt')
            for dt_element in dt_elements:
                key = dt_element.text.strip()
                
                # 다음 형제인 dd 태그 찾기
                dd_element = None
                try:
                    dd_element = dt_element.find_element(By.XPATH, 'following-sibling::dd[1]')
                except NoSuchElementException:
                    continue

                # '지원자격' 테이블 처리
                if key == '지원자격':
                    try:
                        table = dd_element.find_element(By.TAG_NAME, 'table')
                        headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, 'th')]
                        values = [td.text.strip() for td in table.find_elements(By.TAG_NAME, 'td')]
                        for header, value in zip(headers, values):
                            gib_details[header] = value
                    except NoSuchElementException:
                        continue
                
                # '우대사항' 내의 세부 항목 처리
                elif key == '우대사항':
                    try:
                        sub_dl = dd_element.find_element(By.TAG_NAME, 'dl')
                        sub_dt_elements = sub_dl.find_elements(By.TAG_NAME, 'dt')
                        for sub_dt in sub_dt_elements:
                            sub_key = sub_dt.text.strip()
                            sub_dd = sub_dt.find_element(By.XPATH, 'following-sibling::dd[1]')
                            gib_details[sub_key] = sub_dd.text.strip()
                    except NoSuchElementException:
                        # 우대사항 하위 항목이 없을 경우 패스
                        continue
                
                # '게임분야' 처리
                elif key == '게임분야':
                    device_text = ""
                    genre_text = ""
                    try:
                        device_element = dd_element.find_element(By.CSS_SELECTOR, "font[color='#5e42a6']")
                        device_text = device_element.text.strip()
                    except NoSuchElementException:
                        pass
                    try:
                        genre_element = dd_element.find_element(By.CSS_SELECTOR, "font[color='#ae489e']")
                        genre_text = genre_element.text.strip()
                    except NoSuchElementException:
                        pass
                    gib_details['게임분야'] = f"{device_text} {genre_text}".strip()

                # 기타 일반 항목 처리
                elif key in gib_details:
                    # dd 태그의 모든 텍스트를 가져옴
                    full_text = dd_element.text.strip()
                    
                    # '모집인원'의 경우 불필요한 텍스트 제거
                    if key == '모집인원':
                        # '0명 / 현재 지원자수 : **명' 형태에서 '0명'만 가져옴
                        if '/' in full_text:
                            full_text = full_text.split('/')[0].strip()

                    # 링크가 있는 경우, 링크 텍스트만 추출
                    # 이 코드는 링크 텍스트가 불필요하게 포함되는 경우를 제거하기 위한 로직입니다.
                    # '채용직급·직책' 처럼 여러 링크가 있는 경우를 다시 고려해야 합니다.
                    link_elements = dd_element.find_elements(By.TAG_NAME, 'a')
                    
                    if key == '모집분야' or key == '채용직급·직책':
                        if link_elements:
                            links_text = [link.text.strip() for link in link_elements]
                            gib_details[key] = ', '.join(links_text)
                        else:
                            gib_details[key] = full_text
                            
                    elif key == '급여조건':
                        # '급여조건'은 a태그가 있든 없든 dd의 전체 텍스트를 가져옴
                        gib_details[key] = full_text
                    
                    else:
                        gib_details[key] = full_text

    
    except NoSuchElementException as e:
        print(f"⚠️ '모집요강' 섹션을 찾을 수 없습니다: {e}")
    
    return gib_details

# --- 모집요강 추출 함수 ---
def scrape_iframe_content(driver, iframe_id):
    """
    지정된 ID의 iframe 내부 텍스트를 크롤링합니다.
    Args:
        driver (WebDriver): Selenium WebDriver 객체.
        iframe_id (str): 크롤링할 iframe의 ID ('GI_Work_Content' 또는 'GI_Comment').
    Returns:
        str: iframe 내부의 텍스트, 또는 오류 발생 시 None.
    """
    try:
        # iframe이 로드될 때까지 최대 10초 대기
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, iframe_id))
        )
        iframe = driver.find_element(By.ID, iframe_id)
        
        # 드라이버의 포커스를 iframe으로 전환
        driver.switch_to.frame(iframe)
        
        # iframe 내부의 모든 텍스트 가져오기
        content = driver.find_element(By.TAG_NAME, 'body').text
        
        # 포커스를 다시 메인 페이지로 복귀
        driver.switch_to.default_content()
        
        return content.strip()
        
    except (NoSuchElementException, TimeoutException) as e:
        print(f"⚠️ iframe '{iframe_id}'를 찾거나 로드하는 데 실패했습니다: {e}")
        return None

def scrape_job_duties_and_qualifications(driver):
    """
    담당업무와 자격조건을 iframe에서 추출합니다.
    """
    duties_and_qualifications = {
        '담당업무': None,
        '자격조건': None
    }
    
    # '담당업무' iframe 크롤링
    duties_and_qualifications['담당업무'] = scrape_iframe_content(driver, 'GI_Work_Content')
    
    # '자격조건' iframe 크롤링
    duties_and_qualifications['자격조건'] = scrape_iframe_content(driver, 'GI_Comment')
    
    return duties_and_qualifications



def create_dataframe_and_save(data, filename="job_details_test.csv"):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    logger.info(f"✅ 데이터가 '{filename}' 파일로 성공적으로 저장되었습니다.")
    return df


# --- 최종 실행 코드 ---
if __name__ == "__main__":
    
    # 파일 경로 설정
    file_path = 'C:/Users/nezumi/Documents/code/'
    input_file = 'gamejob.csv'
    full_path = os.path.join(file_path, input_file)
    
   
    df_existing = pd.read_csv(full_path)
    valid_urls_df = df_existing[df_existing['URL'].str.startswith('http', na=False)].copy()
   
    df_existing.dropna(subset=['URL'], inplace=True)

    # 💡 재개 지점 설정 (여기를 수정하세요!)
    # 이미 130개를 크롤링했다면, 131번째 URL부터 시작해야 합니다.
    # 인덱스는 0부터 시작하므로 130번째 인덱스부터 시작합니다.
    start_index_to_resume = 0

    urls_to_crawl_df = valid_urls_df.iloc[start_index_to_resume:].copy()
    logger.info("❌ 처음부터 크롤링을 시작합니다.")

    total_urls = len(urls_to_crawl_df)

    if total_urls == 0:
        logger.info("✅ 모든 URL을 이미 크롤링했습니다.")
        exit()

    chunk_size = 100 # 💡 청크 사이즈를 100으로 늘려 안정성 향상
    total_chunks = (total_urls + chunk_size - 1) // chunk_size

    all_crawled_data = []


    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # 불필요한 모든 기능 비활성화
        chrome_options.add_argument("--disable-images")  # 이미지 차단
        chrome_options.add_argument("--disable-background-networking")  # 백그라운드 네트워킹 차단
        chrome_options.add_argument("--aggressive-cache-discard")  # 적극적 캐시 정리
        chrome_options.add_argument("--window-size=1920,1080")

        # 💡 추가된 코드: 브라우저 지문 위장
        # 브라우저가 자동화되고 있음을 알리는 내부 플래그를 비활성화합니다.
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        # 웹 드라이버가 활성화될 때 자동으로 추가되는 '자동화(automation)' 스위치를 제거
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # '자동화 확장 프로그램'을 사용하지 않도록 설정하여 봇 감지를 회피
        chrome_options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=chrome_options)
        
        for i in range(total_chunks):
            start_index = i * chunk_size
            end_index = start_index + chunk_size
            df_chunk = urls_to_crawl_df.iloc[start_index:end_index]
            
            logger.info(f"\n--- 현재 {i+1}/{total_chunks}번째 묶음 처리 중 (총 {len(df_chunk)}개) ---")

            # for idx, row in df_chunk.iterrows():
            for idx, row in df_chunk.iterrows():

                url = row['URL']
                
                if 'gamejob.co.kr' in url:
                    result = scrape_all_job_details(url, driver) 
                    
                    if result['status'] == 'success':
                        all_crawled_data.append(result['content'])
                        logger.info(f"[{idx+1}/{total_urls}] ✅ 성공적으로 크롤링 완료.")
                    else:
                        all_crawled_data.append({'URL': url, '오류': result['content']})
                        logger.warning(f"[{idx+1}/{total_urls}] ⚠️ 크롤링 실패: {result['content']}")
                        time.sleep(3) # 오류 발생 시 잠시 대기
                else:
                    all_crawled_data.append({'URL': url, '오류': '도메인 불일치로 건너뜀'})
                    logger.warning(f"[{url}] ⚠️ 도메인 불일치로 건너뜀.")
            
            # 중간 저장
            intermediate_df = pd.DataFrame(all_crawled_data)
            intermediate_df.to_csv(os.path.join(file_path, f'intermediate_crawled_data_retry_{i+1}.csv'), index=False, encoding='utf-8-sig')

            logger.info(f"✅ {len(all_crawled_data)}개 데이터 중간 저장 완료.")
            random_wait_time = random.uniform(1, 2)
            time.sleep(random_wait_time) # 묶음 처리 후 추가 대기

        # driver.quit()
        
        # df_scraped_final = pd.DataFrame(all_crawled_data)
        # final_df = pd.merge(df_existing, df_scraped_final, left_on='URL', right_on='URL', how='left', suffixes=('', '_crawled'))
        
        # output_file = 'merged_job_postings_9218_final_final_(09_17).csv'
        # output_path = os.path.join(file_path, output_file)
        # final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        logger.info("✅ 최종 데이터 저장 완료!")

    except Exception as e:
        logger.error(f"예상치 못한 최종 오류가 발생했습니다: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()