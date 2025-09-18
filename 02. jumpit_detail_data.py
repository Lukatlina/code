import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import os
import csv

# --- 1단계: API로 수집한 기본 데이터 불러오기 ---
input_file = 'jumpit_basic_data.csv'
output_file = 'jumpit_full_data.csv'

if not os.path.exists(input_file):
    print(f"오류: {input_file} 파일이 존재하지 않습니다. API 수집을 먼저 진행해 주세요.")
else:
    try:
        df = pd.read_csv(input_file)
        job_list = df.to_dict('records')
        print(f"'{input_file}' 파일에서 총 {len(job_list)}개의 기본 데이터를 불러왔습니다.")
    except Exception as e:
        print(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        job_list = []

# --- 2단계: 상세 페이지 크롤링 루프 ---
print("\n상세 페이지 크롤링을 시작합니다.")
print("====================================")

# 필요한 데이터가 담길 새로운 리스트
final_job_data = []

# 웹 스크래핑할 기본 URL
BASE_URL = "https://jumpit.saramin.co.kr/position/"

for job in job_list:
    position_id = job.get('id')
    if not position_id:
        continue # ID가 없으면 건너뛰기
    
    detail_url = f"{BASE_URL}{position_id}"
    
    # 상세 페이지에서 추출한 데이터를 임시로 담을 딕셔너리
    # URL 하나를 처리할 때마다 detailed_info 딕셔너리를 새로 생성 (초기화)
    detailed_info = {
        "주요업무": None,
        "자격요건": None,
        "우대사항": None,
        "복지 및 혜택": None,
        "채용절차 및 기타 지원 유의사항": None,
        "경력_상세": None,
        "학력": None,
        "마감일_상세": None,
        "근무지역_상세": None,
        "기업/서비스 소개": None,
    }

    try:
        print(f"ID {position_id}의 상세 페이지 스크래핑 중...")

        # 웹 페이지에 요청 보내기
        response = requests.get(detail_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        


        # --- HTML에서 원하는 데이터 추출 ---
        # 1. 포지션 상세 정보 섹션 (class='position_info')
        position_info_section = soup.find('div', class_='position_info')
        
        if position_info_section:
            for dl_tag in position_info_section.find_all('dl'):
                dt_tag = dl_tag.find('dt')
                dd_tag = dl_tag.find('dd')
                
                if dt_tag and dd_tag:
                    pre_tag = dd_tag.find('pre')
                    section_title = dt_tag.get_text(strip=True)
                    section_content = pre_tag.get_text(strip=True) if pre_tag else dd_tag.get_text(strip=True)

                    # 제목을 딕셔너리의 키로 사용하여 데이터 저장
                    if "주요업무" in section_title:
                        detailed_info["주요업무"] = section_content
                    elif "자격요건" in section_title:
                        detailed_info["자격요건"] = section_content
                    elif "우대사항" in section_title:
                        detailed_info["우대사항"] = section_content
                    elif "복지 및 혜택" in section_title:
                        detailed_info["복지 및 혜택"] = section_content
                    elif "채용절차 및 기타 지원 유의사항" in section_title:
                        detailed_info["채용절차 및 기타 지원 유의사항"] = section_content

        # 2. 포지션 경력/학력/마감일/근무지역 정보 섹션 (class='sc-b12ae455-0 ehVsnD')
        job_details_section = soup.find('div', class_='sc-b12ae455-0 ehVsnD')

        if job_details_section:
            for dl in job_details_section.find_all('dl'):
                dt_tag = dl.find('dt')
                dd_tag = dl.find('dd')
                
                if dt_tag and dd_tag:
                    title = dt_tag.get_text(strip=True)
                    value = dd_tag.get_text(strip=True)
                    
                    # 제목을 딕셔너리의 키로 사용하여 데이터 저장
                    if "경력" in title:
                        detailed_info["경력"] = value
                    elif "학력" in title:
                        detailed_info["학력"] = value
                    elif "마감일" in title:
                        detailed_info["마감일"] = value
                    elif "근무지역" in title:
                        detailed_info["근무지역"] = value

        # 3. 기업/서비스 소개 섹션 (class='sc-3ef60426-3 dlAoCI')

        # CSS 선택자 사용: .sc-3ef60426-3.dlAoCI 클래스를 가진 div 안에 있는 pre 태그를 찾음
        company_intro_pre = soup.select_one('div.sc-3ef60426-3.dlAoCI pre')

        if company_intro_pre:
            company_intro = company_intro_pre.get_text(strip=True)
        
        detailed_info["기업/서비스 소개"] = company_intro

        # API 데이터와 웹 스크래핑 데이터를 결합
        # job 딕셔너리에 상세 정보를 추가
        job.update(detailed_info)
        final_job_data.append(job)
        
        print(f"ID {position_id} 상세 내용 추출 완료.")
        time.sleep(0.5)

    except requests.exceptions.RequestException as e:
        print(f"ID {position_id} 상세 페이지 요청 중 오류가 발생했습니다: {e}")
        continue
    except Exception as e:
        print(f"ID {position_id} 데이터 파싱 중 오류가 발생했습니다: {e}")
        continue

print("====================================")
print(f"총 {len(final_job_data)}개의 공고에 대한 상세 정보 수집을 완료했습니다.")

# --- 3단계: 최종 데이터를 CSV 파일로 저장 ---
if final_job_data:
    try:
        # 데이터프레임으로 변환하여 CSV 저장
        final_df = pd.DataFrame(final_job_data)
        
        # techStacks와 locations 리스트를 문자열로 변환 (다시 한 번)
        # final_df['techStacks'] = final_df['techStacks'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
        # final_df['locations'] = final_df['locations'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
        
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"최종 데이터를 '{output_file}' 파일에 성공적으로 저장했습니다.")
    except Exception as e:
        print(f"최종 데이터 저장 중 오류가 발생했습니다: {e}")