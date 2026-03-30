# Change Failure Rate Usage Guide

이 문서는 [track-failure.yml](track-failure.yml) 워크플로우를 기준으로 Change Failure Rate(CFR) 추적 방법을 설명합니다.

## 1. 개요

- 워크플로우 파일: [track-failure.yml](track-failure.yml)
- 워크플로우 이름: Track Deployment Result
- 트리거 이벤트: deployment_status
- 목적: 배포 성공/실패 이벤트를 기록하고 이벤트 단위 CFR 정보를 Workflow Summary에 남김

## 2. 현재 워크플로우 동작

[track-failure.yml](track-failure.yml)에는 2개의 Step이 있습니다.

1. Log Result
- deployment_status.state를 읽어 success 여부를 판별
- deployment id, environment, target_url, status를 로그에 출력

2. Write CFR Summary
- success면 failed=0, total=1
- success가 아니면 failed=1, total=1
- 실행마다 GITHUB_STEP_SUMMARY에 CFR 이벤트 결과를 기록

## 3. CFR 계산 방식

Change Failure Rate는 일반적으로 아래 식으로 계산합니다.

$$
CFR = \frac{Failed\ Deployments}{Total\ Deployments} \times 100
$$

현재 워크플로우는 이벤트 단위(1회 실행 기준)로 아래처럼 기록합니다.

- 성공 이벤트: 0/1 (0%)
- 실패 이벤트: 1/1 (100%)

즉, "개별 배포 이벤트 결과"를 남기는 구조입니다.

## 4. 실행 확인 방법

1. 배포가 발생해 deployment_status 이벤트가 생성되면 워크플로우가 실행됩니다.
2. GitHub Actions에서 Track Deployment Result 실행 내역을 엽니다.
3. Summary 탭에서 다음 항목을 확인합니다.
- Environment
- Result
- Failed Deployments
- Total Deployments
- Event CFR

## 5. 운영 시 해석 팁

- 이 워크플로우는 "집계 CFR"이 아니라 "이벤트별 CFR"을 기록합니다.
- 주간/월간 CFR이 필요하면 여러 실행 결과를 모아 합산해야 합니다.
- 일반적인 팀 목표는 CFR을 낮게 유지하는 것입니다.

예시:
- 30회 배포 중 3회 실패면
$$
CFR = \frac{3}{30} \times 100 = 10\%
$$

## 6. 권장 후속 작업

- 배포 실패 기준(rollback, hotfix, incident 라벨 등)을 팀 규칙으로 명확히 정의
- 배포 이벤트 로그를 저장소 아티팩트 또는 외부 대시보드로 누적
- 배포 빈도/MTTR과 함께 DORA 관점으로 통합 모니터링
