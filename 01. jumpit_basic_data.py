import requests
import json
import time
import csv
import os
import xmltodict # <--- 이 줄을 추가합니다.

# --- 변수 설정 ---
BASE_URL = 'https://jumpit-api.saramin.co.kr/api/positions'
TOTAL_ITEMS = 1404 # <-- 총 아이템 수를 1404로 수정했습니다.
ITEMS_PER_PAGE = 16

# 총 페이지 수 계산
total_pages = (TOTAL_ITEMS + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

job_list = []

print(f"총 {total_pages} 페이지의 기본 데이터를 수집합니다.")
print("====================================")

# --- 데이터 수집 루프 ---
for page_num in range(1, total_pages + 1):
    params = {
        'sort': 'reg_dt',
        'highlight': 'false',
        'page': page_num
    }
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        
        # JSON 구조에 맞게 items 변수 정의
        data = response.json()
        
        # data -> result -> positions 경로로 접근
        items = data.get('result', {}).get('positions', [])

        if not items:
            print(f"페이지 {page_num}에 데이터가 없습니다. 중단합니다.")
            break
        
        # API 응답이 단일 객체일 경우 리스트로 변환
        if isinstance(items, dict):
            items = [items]

        # 각 공고에서 필요한 모든 기본 정보 추출
        for item in items:
            
            # techStacks와 locations 데이터 추출 및 정제
            tech_stacks_data = item.get('techStacks', {})
            locations_data = item.get('locations', {})
            
            # 'techStacks'와 'locations'의 실제 리스트 추출
            # 만약 단일 문자열이라면 리스트로 변환
            tech_stacks = tech_stacks_data.get('techStacks', []) if isinstance(tech_stacks_data, dict) else [tech_stacks_data]
            locations = locations_data.get('locations', []) if isinstance(locations_data, dict) else [locations_data]
            
            # 리스트가 아닐 경우 빈 리스트로 초기화 (추가 안정성)
            if not isinstance(tech_stacks, list):
                tech_stacks = []
            if not isinstance(locations, list):
                locations = []

            job_list.append({
                'id': item.get('id'),
                'companyName': item.get('companyName'),
                'title': item.get('title'),
                'jobCategory': item.get('jobCategory'),
                'techStacks': tech_stacks,
                'minCareer': item.get('minCareer'),
                'maxCareer': item.get('maxCareer'),
                'locations': locations,
                'closedAt': item.get('closedAt')
            })
            
            # 진행 상황 출력
            print(f"페이지 {page_num}/{total_pages} - ID: {item.get('id')}, techStacks: {item.get('techStacks')} 데이터 추가 완료.")
            
        time.sleep(0.5)
        
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류가 발생했습니다: {e}")
        break
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        print("API 응답 내용:")
        print(response.text)
        break
        
print("====================================")
print(f"총 {len(job_list)}개의 공고 기본 데이터를 성공적으로 수집했습니다.")

# --- 수집한 데이터를 CSV 파일로 저장 ---
file_path = 'jumpit_basic_data.csv'

if not job_list:
    print("수집된 데이터가 없어 파일을 저장할 수 없습니다.")
else:
    # CSV 헤더(필드명) 정의
    csv_header = list(job_list[0].keys())

    # 'techStacks'와 'locations'를 문자열로 변환
    for item in job_list:
        # techStacks 처리
        tech_stacks_list = item.get('techStacks', [])
        # 리스트에 문자열이 아닌 항목이 있을 수 있으므로 모두 문자열로 변환
        cleaned_tech_stacks = [str(ts) for ts in tech_stacks_list if ts is not None]
        item['techStacks'] = ', '.join(cleaned_tech_stacks)
        
        # locations 처리
        locations_list = item.get('locations', [])
        # 리스트에 문자열이 아닌 항목이 있을 수 있으므로 모두 문자열로 변환
        cleaned_locations = [str(loc) for loc in locations_list if loc is not None]
        item['locations'] = ', '.join(cleaned_locations)

    try:
        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_header)
            
            # 헤더(필드명)를 CSV 파일에 작성
            writer.writeheader()
            
            # 모든 데이터를 CSV 파일에 작성
            writer.writerows(job_list)
        
        print(f"데이터를 '{file_path}' 파일에 성공적으로 저장했습니다.")
        file_size = os.path.getsize(file_path)
        print(f"파일 크기: {file_size / 1024:.2f} KB")

    except IOError as e:
        print(f"CSV 파일 저장 중 오류가 발생했습니다: {e}")