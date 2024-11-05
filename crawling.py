import os
import time
import logging
import requests
from urllib.parse import urlparse, unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.chrome.service import Service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_images_from_url(base_url, start_page=1, end_page=928, folder_path='images', include_pattern=None, image_pattern=None):
    # 폴더가 없는 경우 생성
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # ChromeDriver 설정
    # 에러뜨면 아래에 있는 driver = webdriver.Chrome() 주석처리하고 실행해보세요
    driver = webdriver.Chrome() 
    
    # 페이지 순회
    for page_number in range(start_page, end_page + 1):
        page_url = f"{base_url}page={page_number}"
        logging.info(f"Processing: {page_url}")

        try:
            # 웹페이지 열기
            driver.get(page_url)
            
            # 페이지가 로드될 시간을 주기 위해 잠시 대기
            time.sleep(2)

            # JavaScript 실행
            # (예: CSS 가상 요소를 사용하여 링크를 숨긴 경우)
            # 필요업는 경우 이 부분을 주석 처리할 수 있습니다.
            links_script = """
            var links = [];
            var elements = document.querySelectorAll('a');
            elements.forEach(function(element) {
                var after = window.getComputedStyle(element, '::after');
                var content = after.getPropertyValue('content');
                if (content && content !== 'none') {
                    var link = content.replace(/(^"|"$)/g, '');
                    if (link.startsWith('http')) {
                        links.push(link);
                    }
                }
            });
            return links;
            """
            hidden_links = driver.execute_script(links_script)

            # 각 페이지로 이동할 링크 추출 (예: a 태그)
            links = driver.find_elements(By.TAG_NAME, 'a')
            page_urls = []
            for link in links:
                href = link.get_attribute('href')
                if href and (include_pattern is None or include_pattern in href):
                    page_urls.append(href)
            page_urls.extend(hidden_links)

            # 각 링크를 순회하며 이미지 다운로드
            for page_url in page_urls:
                try:
                    driver.get(page_url)
                    time.sleep(2)  # 페이지 로드 대기
                    img_tags = driver.find_elements(By.TAG_NAME, 'img')
                    for img in img_tags:
                        img_url = img.get_attribute('src')
                        if img_url and (image_pattern is None or image_pattern in img_url):
                            download_image(img_url, folder_path)
                except (StaleElementReferenceException, NoSuchElementException) as e:
                    logging.error(f"Error accessing element on page {page_url}: {e}")
                except Exception as e:
                    logging.error(f"Unexpected error processing page {page_url}: {e}")

        except Exception as e:
            logging.error(f"Failed to load page {page_url}: {e}")

    # 드라이버 종료
    driver.quit()

def download_image(img_url, folder_path):
    retry_count = 3  # 재시도 횟수를 제한합니다.
    for attempt in range(retry_count):
        try:
            # 이미지 요청
            response = requests.get(img_url, stream=True, timeout=10)
            response.raise_for_status()  # HTTP 에러 발생 시 예외 발생
            # URL 파싱하여 파일 이름 추출
            parsed_url = urlparse(img_url)
            img_name = os.path.basename(parsed_url.path)
            # 파일 이름이 없는 경우 쿼리 매개변수에서 추출
            if not img_name:
                img_name = unquote(parsed_url.query.split('=')[1])
            img_name = os.path.join(folder_path, img_name)

            # 이미지 저장
            with open(img_name, 'wb') as out_file:
                out_file.write(response.content)

            logging.info(f"Downloaded: {img_name}")
            return  # 성공적으로 다운로드되면 함수 종료
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt + 1} failed for {img_url}: {e}")
            time.sleep(2)
    logging.error(f"Failed to download image after {retry_count} attempts: {img_url}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    base_url = 'https://archives.seoul.go.kr/photo/list?_csrf=7408f388-7659-4562-8f04-fc00ef5bdb43&formats=jpg&query=%EB%B0%95%EC%A0%95%ED%9D%AC&acp_geol=&ranges=&'  # 크롤링할 웹페이지 기본 URL
    start_page = 1  # 시작 페이지 번호
    end_page = 63  # 끝 페이지 번호 (원하는 페이지 수에 따라 조정)
    include_pattern = '/item'  # 특정 패턴이 포함된 링크만 크롤링
    image_pattern = None  # 원하는 이미지들의 URL 패턴을 지정합니다.
    fetch_images_from_url(base_url, start_page, end_page, folder_path='images', include_pattern=include_pattern, image_pattern=image_pattern)
