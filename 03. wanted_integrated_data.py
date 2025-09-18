import requests
import json
import time
import csv
import os
import random

# --- 변수 설정 ---
BASE_URL_LIST = 'https://www.wanted.co.kr/api/chaos/navigation/v1/results'
BASE_URL_DETAIL = 'https://www.wanted.co.kr/api/chaos/jobs/v4'
ITEMS_PER_PAGE = 20

# 일반적인 웹 브라우저의 User-Agent 헤더
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
}


all_jobs_data = []
offset = 0

print("🚀 Wanted API에서 전체 채용 공고 데이터 수집을 시작합니다.")
print("====================================")

# --- 1단계: 기본 목록 데이터 수집 ---
while True:
    params = {
        int(time.time() * 1000): "",
        "job_group_id": 518,
        "country": "kr",
        "job_sort": "job.popularity_order",
        "years": -1,
        "locations": "all",
        "limit": ITEMS_PER_PAGE,
        "offset": offset,
    }
    
    try:
        response = requests.get(BASE_URL_LIST, params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        items = data.get('data', [])

        if not items:
            print(f"✅ offset {offset}에서 더 이상 데이터가 없습니다. 기본 데이터 수집을 종료합니다.")
            break
        
        for item in items:
            job_info = {
                'id': item.get('id', ''),
                'company_id': item.get('company', {}).get('id', ''),
                'company_name': item.get('company', {}).get('name', ''),
                'position': item.get('position', ''),
                'location': item.get('address', {}).get('location', ''),
                'district': item.get('address', {}).get('district', ''),
                'reward_total': item.get('reward_total', ''),
                'employment_type': item.get('employment_type', ''),
                'is_newbie': item.get('is_newbie', False),
                'annual_from': item.get('annual_from', None),
                'annual_to': item.get('annual_to', None),
                'skill_tags': item.get('skill_tags', []),
                'category_tag_id': item.get('category_tag', {}).get('id', ''),
                'user_oriented_tags': item.get('user_oriented_tags', [])
            }
            all_jobs_data.append(job_info)
            
        print(f"✔️ 현재까지 {len(all_jobs_data)}개의 기본 공고 데이터 수집 완료.")
        offset += ITEMS_PER_PAGE
        time.sleep(random.uniform(0.5, 1.5))

    except requests.exceptions.RequestException as e:
        print(f"❌ 기본 데이터 수집 중 오류가 발생했습니다: {e}")
        break
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        break

print("\n--- 2단계: 상세 데이터 수집 시작 ---")
# --- 상세 데이터 수집 루프 ---
for job in all_jobs_data:
    job_id = job['id']
    detail_url = f"{BASE_URL_DETAIL}/{job_id}/details"
    
    try:
        response = requests.get(detail_url, headers=HEADERS)
        response.raise_for_status()
        detail_data = response.json().get('data', {}).get('job', {})
        
        if detail_data:
            detail_info = detail_data.get('detail', {})
            job['intro'] = detail_info.get('intro', '')
            job['main_tasks'] = detail_info.get('main_tasks', '')
            job['requirements'] = detail_info.get('requirements', '')
            job['preferred_points'] = detail_info.get('preferred_points', '')
            job['benefits'] = detail_info.get('benefits', '')
            job['hire_rounds'] = detail_info.get('hire_rounds', '')
            
            # 기타 추가 정보
            job['full_location'] = detail_data.get('address', {}).get('full_location', '')
            job['category_tag_parent_id'] = detail_data.get('category_tag', {}).get('parent_tag', {}).get('id', '')
            job['category_tag_child_text'] = detail_data.get('category_tag', {}).get('child_tags', [{}])[0].get('text', '')

            # attraction_tags의 title을 추출하여 리스트로 저장
            attraction_tags = [tag.get('title', '') for tag in detail_data.get('attraction_tags', [])]
            job['attraction_tags'] = attraction_tags
            
            print(f"✔️ ID {job_id} 상세 데이터 추가 완료.")
        else:
            print(f"⚠️ ID {job_id}의 상세 데이터를 찾을 수 없습니다.")

        time.sleep(random.uniform(0.5, 1.5))
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ID {job_id} 상세 데이터 요청 중 오류: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ ID {job_id} JSON 파싱 오류: {e}")

print("====================================")
print(f"총 {len(all_jobs_data)}개의 공고 데이터를 성공적으로 수집했습니다.")

# --- 수집한 데이터를 CSV 파일로 저장 ---
file_path = 'wanted_full_job_data.csv'

if not all_jobs_data:
    print("수집된 데이터가 없어 파일을 저장할 수 없습니다.")
else:
    # CSV 헤더(필드명) 정의
    csv_header = list(all_jobs_data[0].keys())

    # 리스트 형태의 데이터를 문자열로 변환하여 CSV에 저장
    for item in all_jobs_data:
        for key in ['skill_tags', 'user_oriented_tags', 'attraction_tags']:
            if isinstance(item.get(key), list):
                item[key] = ', '.join([str(tag) for tag in item[key] if tag is not None])
            else:
                item[key] = ''

    try:
        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_header)
            writer.writeheader()
            writer.writerows(all_jobs_data)
        
        print(f"데이터를 '{file_path}' 파일에 성공적으로 저장했습니다.")
        file_size = os.path.getsize(file_path)
        print(f"파일 크기: {file_size / 1024:.2f} KB")

    except IOError as e:
        print(f"CSV 파일 저장 중 오류가 발생했습니다: {e}")