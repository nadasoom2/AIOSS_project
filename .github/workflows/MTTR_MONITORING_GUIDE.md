# MTTR(평균 복구 시간) 모니터링 가이드

MTTR(Mean Time To Recovery)은 시스템 장애나 인시던트 발생부터 완전히 복구될 때까지 걸리는 평균 시간을 측정하는 중요한 DevOps 메트릭입니다.

## 📋 개요

### MTTR이란?
- **정의**: 인시던트 보고 → 인시던트 해결까지의 소요 시간
- **중요도**: 시스템 안정성과 운영팀의 대응 효율성을 나타냄
- **목표**: MTTR이 낮을수록 좋음 (복구가 빠름)

### MTTR 계산 방식
```
MTTR = (총 장애 복구 시간의 합) / (총 장애 건수)
```

## 🚀 설정 및 사용 방법

### 1. 워크플로우 활성화
GitHub Action 워크플로우는 다음 이벤트에 자동으로 실행됩니다:

```yaml
on:
  issues:
    types: [opened, closed, labeled]
  schedule:
    - cron: '0 9 * * *'  # 매일 09:00 UTC (한국 시간 18:00)
```

### 2. 인시던트 이슈 레이블 설정

MTTR 추적을 위해 다음 라벨을 GitHub에서 생성하세요:

- **incident**: 기본 인시던트 라벨
- **critical**: 심각한 인시던트 (MTTR 중요)
- **high**: 높음 심각도
- **medium**: 중간 심각도 (기본값)
- **low**: 낮음 심각도

### 3. 인시던트 이슈 작성 방법

```markdown
# 제목: [인시던트] 데이터베이스 연결 오류

## 설명
데이터베이스 연결이 끊어져 서비스가 다운됨

## 영향 범위
- 프로덕션 환경
- 모든 사용자

## 라벨
- incident
- critical
- database
```

**라벨 선택**: `incident` + 심각도 라벨 (`critical`, `high`, `medium`, `low`)

이슈를 닫으면 자동으로 MTTR이 계산됩니다.

## 📊 메트릭 해석

### 출력 파일: `mttr-metrics.json`

```json
{
  "total_incidents": 5,
  "average_mttr": 120.5,
  "median_mttr": 95,
  "min_mttr": 15,
  "max_mttr": 280,
  "p95_mttr": 250,
  "p99_mttr": 275,
  "by_severity": {
    "Critical": {
      "count": 2,
      "average": 180,
      "min": 120,
      "max": 240
    },
    "High": {
      "count": 3,
      "average": 80,
      "min": 15,
      "max": 150
    }
  }
}
```

| 메트릭 | 의미 | 좋은 값 |
|--------|------|--------|
| **average_mttr** | 평균 복구 시간 (분) | < 60분 |
| **median_mttr** | 중앙값 (이상치 영향 적음) | < 45분 |
| **p95_mttr** | 상위 95% 복구 시간 | < 120분 |
| **p99_mttr** | 상위 99% 복구 시간 | < 240분 |

### 심각도별 분석

```
Critical (심각): MTTR < 30분 권장
High (높음): MTTR < 60분 권장
Medium (중간): MTTR < 120분 권장
Low (낮음): MTTR < 240분 권장
```

## 🛠️ 수동 실행

스크립트를 수동으로 실행하여 즉시 메트릭을 확인할 수 있습니다:

```bash
# 기본 실행 (최근 30일 분석)
python scripts/mttr_analyzer.py --repo owner/repo

# 60일 분석
python scripts/mttr_analyzer.py --repo owner/repo --days 60

# 리포트 출력
python scripts/mttr_analyzer.py --repo owner/repo --print-report

# 커스텀 인시던트 라벨 사용
python scripts/mttr_analyzer.py --repo owner/repo --incident-label "outage"
```

### 환경 변수 설정
```bash
export GITHUB_TOKEN=your_github_token
python scripts/mttr_analyzer.py --repo nadasoom2/AIOSS_project --print-report
```

## 📈 Best Practices

### 1. 일관된 라벨링
- 모든 인시던트에 라벨 일관성 있게 적용
- 심각도 라벨과 인시던트 라벨을 함께 사용

### 2. 상세한 이슈 설명
```markdown
# 제목: [인시던트] API 서버 응답 지연

- **보고 시간**: 자동 (이슈 생성 시간)
- **발견 경로**: 모니터링 알림
- **영향을 받은 서비스**: 결제 API
- **공동 작업자**: @team-member

설명...

## 해결 방법
1. 로그 확인
2. 서버 재시작
3. 캐시 초기화

## 라벨
- incident
- critical
- api
```

### 3. 정기적인 리뷰
- 주간 MTTR 리포트 검토
- 심각도별 MTTR 비교
- 개선 목표 수립

## 📊 GitHub Actions 워크플로우 상세

### `mttr-monitoring.yml` 구성

1. **track-mttr**: MTTR 메트릭 계산
   - 최근 30일 인시던트 수집
   - JSON 파일로 메트릭 저장
   - 닫힌 이슈에 자동 댓글 추가

2. **generate-report**: 리포트 생성
   - 메트릭을 읽기 좋은 형식으로 정리
   - Workflow summary에 표시

### 자동 이슈 댓글
이슈가 닫힐 때 자동으로 다음 정보가 댓글로 추가됩니다:

```
## MTTR 정보
- 보고 시간: 2024-03-30T10:00:00
- 해결 시간: 2024-03-30T11:45:00
- 복구 시간: 105분 (1.8시간)
- 라벨: incident, critical, database
```

## 🔗 연계 메트릭

### DORA 메트릭과의 연관
- **MTTR**: 안정성 (Stability) 측정
- **배포 빈도**: `deployment-frequency-monitoring.yml`
- **리드 타임**: `deployment-frequency-analyzer.py`
- **변경 실패율**: 모니터링 알림 연계

## ⚠️ 주의사항

1. **GitHub Token 권한**
   - `repo` 권한 필요
   - 읽기 권한만 필요

2. **API 레이트 제한**
   - GitHub API는 시간당 5000 요청 제한
   - 큰 저장소는 분석 기간을 줄일 수 있음

3. **정확성**
   - 이슈 생성 시간 = 인시던트 보고 시간
   - 이슈 종료 시간 = 인시던트 해결 시간
   - 임시 닫음은 제외하도록 라벨링 약속 필요

## 📚 참고 자료

- [GitHub Issues Search API](https://docs.github.com/en/rest/reference/search)
- [DORA Metricsv](https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-devops-performance)
- [SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
