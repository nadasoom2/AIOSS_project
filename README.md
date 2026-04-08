# AI OSS 개발

## 1. 오리엔테이션
### 과제1: git push 실습

## 2. 웹 크롤러

여러 종류의 웹 사이트를 유연하게 수집하기 위한 스크립트가 추가되었습니다.

- HTML 페이지: 제목, 본문 텍스트, 링크 추출
- JSON API: JSON 자동 파싱
- JS 렌더링 페이지: 옵션으로 Playwright 렌더링 지원

파일 위치:

- scripts/adaptive_web_crawler.py

### 설치

```bash
pip install aiohttp
```

JS 렌더링이 필요한 경우:

```bash
pip install playwright
playwright install chromium
```

### 사용 예시

```bash
python scripts/adaptive_web_crawler.py --url https://example.com --print
python scripts/adaptive_web_crawler.py --url https://example.com/api/data --url https://news.ycombinator.com --output crawl_results.json --print
python scripts/adaptive_web_crawler.py --from-file urls.txt --render-js --output crawl_results.json --print
```