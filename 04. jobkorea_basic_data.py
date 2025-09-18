import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from bs4 import BeautifulSoup
import re
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_all_job_listings_with_validation(url):
    """
    페이지네이션을 통해 모든 채용 공고를 크롤링하고 페이지 이동을 검증합니다.
    """
    job_listings = []
    driver = None
    
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
        logger.info(f"✅ 초기 페이지 접속 완료: {url}")
        
        # 필터링 로직 (기존과 동일)
        # ... (AI·개발·데이터 버튼 클릭, 직무 선택, 검색 버튼 클릭 로직)
        ai_dev_label = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//label[@for='duty_step1_10031']"))
        )
        ai_dev_label.click()
        logger.info("✅ 'AI·개발·데이터' 버튼 클릭 완료.")
        time.sleep(2)

        sub_job_list_items = driver.find_elements(By.CSS_SELECTOR, '#duty_step2_10031_ly .item')

        if len(sub_job_list_items) == 0:
            logger.warning("❌ 하위 직무 목록을 찾을 수 없습니다.")
            return

        for i in range(min(12, len(sub_job_list_items))):
            label = sub_job_list_items[i].find_element(By.CSS_SELECTOR, '.lb_tag')
            label.click()
            job_name = sub_job_list_items[i].find_element(By.CSS_SELECTOR, 'input').get_attribute('data-name')
            logger.info(f"✅ '{job_name}' 직무 선택 완료.")
        time.sleep(2)
        
        search_button = driver.find_element(By.ID, 'dev-btn-search')
        search_button.click()
        logger.info("✅ 검색 버튼 클릭 완료. 결과 페이지로 이동합니다.")

        # 셀레늄 드라이버 10초정도 id가 dvGIPaging인 요소가 페이지에 나타날때까지 기다려야함.
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'dvGIPaging')))
        time.sleep(2)
    
        
        page_num = 1
        while True:
            logger.info(f"\n--- {page_num}페이지 스크랩 중 ---")
            
            # 페이지네이션이 로드될 때까지 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'dvGIPaging'))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table_body = soup.find('div', class_='tplList tplJobList')
            
            if not table_body:
                logger.warning("⚠️ 채용 공고 목록 테이블을 찾을 수 없습니다. 크롤링을 종료합니다.")
                break
            
            # 데이터 추출
            for tr in table_body.find_all('tr', class_='devloopArea'):
                try:
                    company_name = tr.find('td', class_='tplCo').a.text.strip()
                    job_title_element = tr.find('td', class_='tplTit').find('strong').find('a')
                    job_title = job_title_element.text.strip()
                    job_detail_url = f'https://www.jobkorea.co.kr{job_title_element["href"]}'

                    etc_info = tr.find('td', class_='tplTit').find('p', class_='etc').find_all('span', class_='cell')
                    experience = etc_info[0].text.strip() if len(etc_info) > 0 else None
                    education = etc_info[1].text.strip() if len(etc_info) > 1 else None
                    location = etc_info[2].text.strip() if len(etc_info) > 2 else None
                    job_type = etc_info[3].text.strip() if len(etc_info) > 3 else None
                    # 급여와 직급/직책 데이터 추출 (추가된 부분)
                    salary = etc_info[4].text.strip() if len(etc_info) > 4 else None
                    rank = etc_info[5].text.strip() if len(etc_info) > 5 else None

                    odd_td = tr.find('td', class_='odd')
                    registration_date = odd_td.find('span', class_='time').text.strip() if odd_td and odd_td.find('span', class_='time') else None
                    closing_date = odd_td.find('span', class_='date').text.strip() if odd_td and odd_td.find('span', class_='date') else None

                    job_listings.append({
                        '회사명': company_name,
                        '제목': job_title,
                        '상세페이지_URL': job_detail_url,
                        '경력': experience,
                        '학력': education,
                        '지역': location,
                        '고용형태': job_type,
                        '등록일': registration_date,
                        '마감일': closing_date
                    })

                except Exception as e:
                    logger.warning(f"⚠️ 데이터 중 오류 발생: {e}")
                    continue
            
            # 다음 페이지로 이동하는 로직
            next_page_num = page_num + 1
            try:
                # 다음 페이지 버튼(a 태그)을 찾습니다.
                next_page_link_selector = f'div.tplPagination a[data-page="{next_page_num}"]'
                next_page_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, next_page_link_selector))
                )
                
                next_page_button.click()
                logger.info(f"✅ {next_page_num}페이지 버튼을 클릭했습니다.")
                
                # 다음 페이지로 이동했는지 검증
                now_page_selector = f'div.tplPagination span.now[data-page="{next_page_num}"]'
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, now_page_selector))
                )
                logger.info(f"✅ {next_page_num}페이지로 성공적으로 이동했습니다.")

                page_num += 1
                time.sleep(2)
                
            except TimeoutException:
                logger.info("🏁 다음 페이지 버튼을 찾을 수 없습니다. 크롤링을 종료합니다.")
                break
            except Exception as e:
                logger.error(f"❌ 페이지 이동 중 오류 발생: {e}")
                break

    except Exception as e:
        logger.error(f"❌ 전체 스크랩 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()

    return job_listings

if __name__ == '__main__':
    url_to_scrape = 'https://www.jobkorea.co.kr/recruit/joblist?menucode=duty'
    scraped_data = scrape_all_job_listings_with_validation(url_to_scrape)
    
    if scraped_data:
        df = pd.DataFrame(scraped_data)
        file_name = "jobkorea_all_listings.csv"
        df.to_csv(file_name, index=False, encoding='utf-8-sig')
        
        logger.info("\n--- 크롤링 완료 ---")
        logger.info(f"✅ 총 {len(scraped_data)}건의 채용 공고를 '{file_name}' 파일에 저장했습니다.")
        print(df.head())
    else:
        logger.warning("\n❌ 크롤링된 데이터가 없습니다.")