# Deployment Frequency 추적 가이드

GitHub Actions를 사용하여 프로젝트의 **Deployment Frequency(배포 빈도)** 메트릭을 자동으로 추적하고 분석합니다. 이는 DORA 메트릭 중 하나입니다.

## 📌 Deployment Frequency란?

**배포 빈도**: 프로덕션 환경으로 배포되는 빈도

### DORA 성과 등급

| 등급 | 배포 빈도 | 특징 |
|------|---------|------|
| 🟢 **Elite** | 일 1회 이상 | 매우 높은 배포 능력 |
| 🟢 **High** | 주 1회~월 1회 | 높은 배포 능력 |
| 🟡 **Medium** | 월 1회~6개월 1회 | 중간 배포 능력 |
| 🔴 **Low** | 6개월에 1회 미만 | 배포 개선 필요 |

## 🚀 자동 실행 설정 (GitHub Actions)

### 1. 워크플로우 파일
**위치**: `.github/workflows/deployment-frequency.yml`

자동으로 실행되는 시점:
- ✅ 매일 자정(UTC+9) 정기 실행
- ✅ `main` 브랜치에 push
- ✅ Pull Request 완료 시
- ✅ 수동 실행 가능

### 2. 실행 확인
```bash
# GitHub Actions 웹 인터페이스 확인
https://github.com/{owner}/{repo}/actions
```

### 3. 리포트 다운로드
1. GitHub 리포지토리 **Actions** 탭 방문
2. **"Deployment Frequency Tracking"** 워크플로우 클릭
3. 최근 실행 선택
4. **Artifacts** 섹션에서 다음 다운로드:
   - `deployment-frequency-report` - 마크다운 리포트
   - `deployment-metrics` - JSON 메트릭

## 🔧 수동 분석 (Python 스크립트)

### 설치 (최초 1회)
```bash
pip install PyGithub python-dateutil
```

### GitHub Token 생성

1. GitHub 프로필 → **Settings** → **Developer settings**
2. **Personal access tokens** → **Tokens (classic)**
3. **New token** → 다음 권한 선택:
   - `repo` (리포지토리 접근)
   - `read:deployment` (배포 조회)

### 기본 사용법

#### 1. 환경변수 설정

**Linux/macOS:**
```bash
export GITHUB_TOKEN=your_github_token_here
```

**Windows PowerShell:**
```powershell
$env:GITHUB_TOKEN = "your_github_token_here"
```

**Windows CMD:**
```cmd
set GITHUB_TOKEN=your_github_token_here
```

#### 2. 기본 분석 실행

```bash
# 기본 분석 (지난 30일, production 환경)
python scripts/deployment_frequency_analyzer.py --repo owner/repo

# 출력 예시:
# 🚀 배포 현황 (지난 30일)
#   총 배포 시도: 45 회
#   성공한 배포: 43 회
#   실패한 배포: 2 회
#   성공률: 95.56%
#   배포한 날: 15 일
#
# 📈 배포 빈도
#   일일 평균: 1.43 회/일
#   배포 간격: 16.93 시간
#
# 🟢 DORA 등급: 엘리트 성과 (일 1회 이상)
```

### 다양한 옵션

| 옵션 | 설명 | 기본값 |
|------|------|-------|
| `--repo` | 리포지토리 (owner/repo) | 필수 |
| `--token` | GitHub API 토큰 | 환경변수 사용 |
| `--env` | 배포 환경명 | production |
| `--days` | 분석 기간 (일) | 30 |
| `--export` | JSON 파일로 내보내기 | - |
| `--csv` | CSV 파일로 내보내기 | - |

### 실용적인 예시

#### 예1: 지난 60일 분석 + JSON 내보내기
```bash
python scripts/deployment_frequency_analyzer.py \
  --repo nadasoom2/AIOSS_project \
  --days 60 \
  --export deployment-report.json
```

#### 예2: Staging 환경 분석
```bash
python scripts/deployment_frequency_analyzer.py \
  --repo nadasoom2/AIOSS_project \
  --env staging
```

#### 예3: 배포 이력을 CSV로 내보내기
```bash
python scripts/deployment_frequency_analyzer.py \
  --repo nadasoom2/AIOSS_project \
  --csv deployments.csv \
  --export report.json
```

#### 예4: 개발 환경 60일 메트릭 추출
```bash
python scripts/deployment_frequency_analyzer.py \
  --repo nadasoom2/AIOSS_project \
  --env development \
  --days 60 \
  --export dev-metrics.json
```

## 📊 메트릭 설정

**파일**: `deployment-frequency-metrics.yml`

### 배포 목표 설정
```yaml
deployment_frequency:
  targets:
    daily: 1.0         # 목표: 1회/일 (Elite)
    weekly: 7.0        # 1주일에 7회
    minimum: 0.5       # 최소 목표: 0.5회/일
    warning: 0.33      # 경고: 0.33회/일
```

### 배포 환경 설정
```yaml
  environments:
    - name: "development"
      track: true
      alert: false
    - name: "staging"
      track: true
      alert: true
    - name: "production"
      track: true
      alert: true
```

### 알림 설정
```yaml
notifications:
  # 배포 빈도 감소 시 알림
  frequency_drop:
    threshold_reduction: 30  # 30% 감소 시 알림
    consecutive_days: 3      # 3일 연속
  
  # 배포 실패 시 알림
  deployment_failure:
    threshold: 2  # 2회 이상 연속 실패
  
  channels:
    - slack
    - email
    - github_issues
```

## 📈 결과 해석

### 배포 빈도 분석

```
일일 평균 배포:    해석:
≥ 1.0              ✅ Elite 등급 (매일 1회 이상)
0.14 ~ 0.99        ✅ High 등급 (주 1회 이상)
0.033 ~ 0.13       🟡 Medium 등급 (월 1회 이상)
< 0.033            🔴 Low 등급 (개선 필요)
```

### 배포 성공률 해석

| 성공률 | 평가 | 조치 |
|-------|------|------|
| > 99% | 🟢 우수 | 현재 수준 유지 |
| 95~99% | 🟡 양호 | 모니터링 |
| < 95% | 🔴 미흡 | 원인 분석 필요 |

## 🔄 CI/CD 연동

### 배포 실패 시 자동 알림

```yaml
- name: Check Deployment Frequency Target
  run: |
    if (( $(echo "$FREQ < $TARGET" | bc -l) )); then
      echo "⚠️ 배포 빈도 감소"
      # Slack 알림 전송
    fi
```

### GitHub Issues로 리포트

```yaml
- name: Create Deployment Report Issue
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: 'Deployment Frequency Report',
        body: '배포 빈도 분석 결과...'
      })
```

## 📝 예상 출력 예시

```
🔍 최근 30일간 'production' 환경의 배포를 수집 중...
✅ 43개의 배포 기록 수집 완료
✅ 8개의 릴리스 기록 수집 완료

======================================================================
📊 Deployment Frequency 분석 보고서
======================================================================

🚀 배포 현황 (지난 30일)
  총 배포 시도:     45 회
  성공한 배포:      43 회
  실패한 배포:       2 회
  성공률:         95.56%
  배포한 날:       15 일

📈 배포 빈도
  일일 평균:      1.43 회/일
  배포 간격:      16.93 시간

🟢 DORA 등급: 엘리트 성과 (일 1회 이상)

📦 릴리스 현황 (지난 30일)
  총 릴리스:        8 회
  Major:           1 회
  Minor:           4 회
  Patch:           3 회

💡 추천사항
  ✅ 배포 빈도가 우수합니다. 현재 수준 유지를 권장합니다.

======================================================================
✅ JSON 내보내기 완료: deployment-report.json
```

## 🐛 문제 해결

### 1. "배포를 수집할 수 없음" 오류
```bash
# GitHub 배포 이력 확인
git log --oneline --all | head -20

# 배포 기록이 GitHub에 없으면 다음 확인:
# - GitHub Actions 워크플로우에서 배포 기록 생성
# - GitHub Deployments API 사용 여부 확인
```

### 2. "토큰 인증 실패" 오류
```bash
# 토큰 유효성 확인
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# 토큰 권한 확인 (read:deployment 필수)
```

### 3. "분석할 데이터가 없음"
- 배포 기록이 없거나 매우 적은 경우
- GitHub Actions에서 배포 이벤트 생성 확인
- 환경명 올바른지 확인:

```bash
# 사용 가능한 환경 확인
python scripts/deployment_frequency_analyzer.py --repo owner/repo --env staging
```

## 📌 권장 사항

### 정기 검토
- ✅ 주 1회 배포 빈도 확인
- ✅ 월 1회 추이 분석
- ✅ 분기 1회 목표 조정

### 배포 빈도 개선

1. **자동화 강화**
   - 자동 테스트 추가
   - CI/CD 파이프라인 최적화
   - 수동 스텝 자동화

2. **배포 프로세스 개선**
   - Blue-Green 배포
   - Canary 배포
   - 자동 롤백

3. **팀 협업 개선**
   - 작은 PR 크기 유지
   - 빠른 코드 리뷰
   - 배포 일정 규칙화

## 📚 추가 리소스

- [DORA Metrics](https://cloud.google.com/software-delivery-intelligence/docs/dora-metrics)
- [GitHub Deployments API](https://docs.github.com/rest/deploy/deployments)
- [GitHub Actions Documentation](https://docs.github.com/actions)

---

**작성**: 2026년 3월
**마지막 업데이트**: 2026년 3월 30일
