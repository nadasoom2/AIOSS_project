# 🚀 Deployment Frequency (배포 빈도) 추적 시스템

GitHub를 기반으로 **배포 빈도(Deployment Frequency)** 메트릭을 자동으로 추적하고 분석하는 시스템입니다. DORA 메트릭 중 하나로, 조직의 DevOps 성숙도를 측정합니다.

## 📊 주요 기능

### 1. **자동 배포 빈도 분석**
- 🔄 매일 자동으로 배포 메트릭 수집
- 📈 일일/주간/월간 배포 현황 추적
- 🎯 DORA 등급 자동 계산

### 2. **배포 성공률 모니터링**
- ✅ 배포 성공/실패 추적
- ⚠️ 낮은 성공률 자동 경고
- 📊 추세 분석

### 3. **다양한 환경 지원**
- 🏗️ Development, Staging, Production 환경별 추적
- 🔀 환경별 독립적인 메트릭 분석
- 📌 환경별 임계값 설정

### 4. **실시간 알림**
- 🔔 Slack 알림
- 📧 Email 알림
- 🐛 GitHub Issues 자동 생성

## 🎯 DORA 성과 등급

| 등급 | 배포 빈도 | 설명 |
|------|---------|------|
| 🟢 **Elite** | 일 1회 이상 | 매우 높은 배포 능력 |
| 🟢 **High** | 주 1회~월 1회 | 높은 배포 능력 |
| 🟡 **Medium** | 월 1회~6개월 1회 | 중간 배포 능력 |
| 🔴 **Low** | 6개월에 1회 미만 | 배포 개선 필요 |

## 🚀 빠른 시작

### 1️⃣ GitHub Token 생성

1. GitHub 프로필 → **Settings** → **Developer settings**
2. **Personal access tokens** → **Tokens (classic)**
3. **New token** 생성:
   - 이름: `Deployment Frequency Token`
   - 권한: `repo`, `read:deployment` 선택
   - 토큰 복사

### 2️⃣ GitHub 리포지토리에 저장소 시크릿 추가

1. 리포지토리 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. 이름: `DEPLOYMENT_TOKEN`
4. 값: 생성한 토큰 붙여넣기

### 3️⃣ 워크플로우 자동 실행 확인

```bash
# GitHub Actions 확인
https://github.com/{owner}/{repo}/actions
```

- ✅ "Deployment Frequency Tracking" 워크플로우 자동 실행
- ✅ "Deployment Frequency Monitoring" 워크플로우 자동 실행

## 📂 파일 구조

```
.github/workflows/
├── deployment-frequency.yml              # 메인 분석 워크플로우
└── deployment-frequency-monitoring.yml  # 모니터링 경고 워크플로우

scripts/
├── deployment_frequency_analyzer.py     # 배포 분석 도구
└── deployment_monitor.py                # 모니터링 경고 시스템

docs/
└── DEPLOYMENT_FREQUENCY_GUIDE.md        # 상세 사용 가이드

deployment-frequency-metrics.yml         # 메트릭 설정 파일
```

## 💻 수동 분석 (로컬)

### 설치
```bash
pip install PyGithub python-dateutil
```

### 기본 분석
```bash
export GITHUB_TOKEN=your_token_here
python scripts/deployment_frequency_analyzer.py --repo owner/repo
```

### 출력 예시
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
```

## 🔧 주요 명령어

### 1. 프로덕션 환경 분석
```bash
python scripts/deployment_frequency_analyzer.py \
  --repo owner/repo \
  --env production \
  --days 30
```

### 2. Staging 환경 분석
```bash
python scripts/deployment_frequency_analyzer.py \
  --repo owner/repo \
  --env staging \
  --days 60
```

### 3. JSON으로 내보내기
```bash
python scripts/deployment_frequency_analyzer.py \
  --repo owner/repo \
  --export report.json \
  --csv deployments.csv
```

### 4. 모니터링 및 경고 확인
```bash
python scripts/deployment_monitor.py \
  --repo owner/repo \
  --config deployment-frequency-metrics.yml \
  --export alerts.json
```

## ⚙️ 설정 방법

### 배포 목표 설정
파일: `deployment-frequency-metrics.yml`

```yaml
deployment_frequency:
  targets:
    daily: 1.0         # 일일 목표
    minimum: 0.5       # 최소 목표
    warning: 0.33      # 경고 임계값
```

### 환경별 설정
```yaml
  environments:
    - name: "production"
      track: true
      alert: true
```

### 알림 설정
```yaml
notifications:
  channels:
    - slack
    - email
    - github_issues
```

## 📊 대시보드 활용

### GitHub Actions Artifacts
각 실행 후 다음 파일 다운로드:
- `deployment-frequency-report.md` - 마크다운 리포트
- `deployment-metrics.json` - JSON 데이터
- 모니터링 리포트 - HTML 대시보드

### 자동 생성되는 GitHub Issues
- 배포 빈도 심각 경고 시 자동 생성
- PR 댓글에 홈 메트릭 자동 추가

## 🐛 문제 해결

### 배포 데이터가 없는 경우
1. GitHub Actions 워크플로우에서 배포 이벤트 생성 확인
2. 환경명 정확성 확인 (`production`, `staging` 등)

### 토큰 오류
```bash
# 토큰 유효성 확인
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

### 권한 부족
- Personal token에 `read:deployment` 권한 확인
- `repo` 스코프 확인

## 📈 성과 개선 팁

### 배포 빈도 증가
1. **자동화 강화**
   - 자동 테스트 추가
   - CI/CD 파이프라인 최적화

2. **프로세스 개선**
   - 작은 PR 크기 유지
   - 빠른 코드 리뷰
   - 배포 일정 규칙화

3. **기술 개선**
   - Blue-Green 배포
   - Canary 배포
   - 자동 롤백

### 배포 성공률 향상
1. 자동 테스트 커버리지 증대
2. 배포 전 검증 강화
3. 배포 모니터링 개선

## 🔗 참고 자료

- [DORA Metrics](https://cloud.google.com/software-delivery-intelligence/docs/dora-metrics)
- [GitHub Deployments API](https://docs.github.com/rest/deploy/deployments)
- [GitHub Actions](https://docs.github.com/actions)

## 📌 상세 가이드

더 자세한 사용 방법은 [DEPLOYMENT_FREQUENCY_GUIDE.md](docs/DEPLOYMENT_FREQUENCY_GUIDE.md)를 참고하세요.

## 💡 팁

### 처음 사용할 때
1. 먼저 로컬에서 Python 스크립트로 테스트
2. 메트릭이 정상 수집되는지 확인
3. GitHub Actions에서 자동 실행 설정

### 정기 점검
- ✅ 주 1회: 배포 빈도 확인
- ✅ 월 1회: 추이 분석
- ✅ 분기 1회: 목표 조정

### 다른 DORA 메트릭
이 시스템은 Deployment Frequency만 추적합니다.
다른 DORA 메트릭:
- **Lead Time for Changes**: [Lead Time 추적](../LEAD_TIME_GUIDE.md)
- **Change Failure Rate**: TBD
- **Mean Time to Recovery**: TBD

---

**작성일**: 2026년 3월 30일  
**버전**: 1.0.0  
**유지보수**: GitHub AIOSS 팀
