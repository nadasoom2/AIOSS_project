#!/usr/bin/env python3
"""
MTTR(Mean Time To Recovery) 분석 도구

GitHub 리포지토리의 MTTR 메트릭을 분석합니다.
- 평균 복구 시간
- 인시던트별 복구 시간
- 복구 시간 추이
- 환경별 MTTR 통계
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import statistics

try:
    from github import Github
    from github.GithubException import GithubException
except ImportError:
    print("❌ PyGithub이 설치되지 않았습니다.")
    print("설치 명령: pip install PyGithub")
    sys.exit(1)


class MTTRAnalyzer:
    """MTTR을 분석하는 클래스"""
    
    def __init__(self, token: str, repo_name: str):
        """
        초기화
        
        Args:
            token: GitHub API 토큰
            repo_name: 리포지토리 이름 (owner/repo 형식)
        """
        self.g = Github(token)
        self.repo = self.g.get_repo(repo_name)
        self.incidents: List[Dict] = []
        self.metrics: Dict = {}
    
    def fetch_incidents(self, days: int = 30, incident_label: str = 'incident') -> None:
        """
        인시던트 데이터 수집 (이슈 기반)
        
        Args:
            days: 분석 기간 (일)
            incident_label: 인시던트 라벨명
        """
        print(f"🔍 최근 {days}일간 '{incident_label}' 라벨의 이슈를 수집 중...")
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 인시던트 라벨이 있는 모든 닫힌 이슈 검색
            query = f'repo:{self.repo.full_name} label:{incident_label} is:issue is:closed'
            issues = self.g.search_issues(query, sort='updated', order='desc')
            
            incident_count = 0
            for issue in issues:
                if issue.created_at < start_date:
                    break
                
                if issue.closed_at:
                    # 복구 시간 계산 (분)
                    recovery_time_seconds = (issue.closed_at - issue.created_at).total_seconds()
                    recovery_time_minutes = recovery_time_seconds / 60
                    recovery_time_hours = recovery_time_minutes / 60
                    
                    # 심각도 라벨 확인
                    severity = 'Medium'
                    for label in issue.labels:
                        if 'critical' in label.name.lower():
                            severity = 'Critical'
                        elif 'high' in label.name.lower():
                            severity = 'High'
                        elif 'low' in label.name.lower():
                            severity = 'Low'
                    
                    self.incidents.append({
                        'number': issue.number,
                        'title': issue.title,
                        'created_at': issue.created_at.isoformat(),
                        'closed_at': issue.closed_at.isoformat(),
                        'recovery_time_minutes': round(recovery_time_minutes, 2),
                        'recovery_time_hours': round(recovery_time_hours, 2),
                        'severity': severity,
                        'labels': [label.name for label in issue.labels],
                        'creator': issue.user.login if issue.user else 'unknown',
                        'url': issue.html_url
                    })
                    incident_count += 1
            
            print(f"✅ {incident_count}개의 인시던트 기록 수집 완료")
        
        except GithubException as e:
            print(f"❌ GitHub API 오류: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"⚠️  일반 오류: {e}")
            # 데이터가 없어도 계속 진행
    
    def calculate_metrics(self) -> None:
        """MTTR 메트릭 계산"""
        print("📊 MTTR 메트릭 계산 중...")
        
        if not self.incidents:
            print("⚠️  분석할 인시던트가 없습니다.")
            self.metrics = {
                'total_incidents': 0,
                'average_mttr': 0,
                'median_mttr': 0,
                'min_mttr': 0,
                'max_mttr': 0,
                'p95_mttr': 0,
                'p99_mttr': 0,
                'by_severity': {},
                'by_date': {},
                'analysis_period_days': 0
            }
            return
        
        recovery_times = [incident['recovery_time_minutes'] for incident in self.incidents]
        recovery_times.sort()
        
        # 백분위 계산
        def percentile(data, p):
            """데이터의 p 백분위 계산"""
            if len(data) == 0:
                return 0
            if len(data) == 1:
                return data[0]
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]
        
        # 기본 통계
        self.metrics = {
            'total_incidents': len(self.incidents),
            'average_mttr': round(sum(recovery_times) / len(recovery_times), 2),
            'median_mttr': round(statistics.median(recovery_times), 2),
            'min_mttr': round(min(recovery_times), 2),
            'max_mttr': round(max(recovery_times), 2),
            'p95_mttr': round(percentile(recovery_times, 95), 2),
            'p99_mttr': round(percentile(recovery_times, 99), 2),
            'stddev_mttr': round(statistics.stdev(recovery_times), 2) if len(recovery_times) > 1 else 0,
            'incidents': self.incidents
        }
        
        # 심각도별 MTTR
        by_severity = defaultdict(list)
        for incident in self.incidents:
            by_severity[incident['severity']].append(incident['recovery_time_minutes'])
        
        severity_metrics = {}
        for severity in ['Critical', 'High', 'Medium', 'Low']:
            if severity in by_severity:
                times = by_severity[severity]
                severity_metrics[severity] = {
                    'count': len(times),
                    'average': round(sum(times) / len(times), 2),
                    'median': round(statistics.median(times), 2),
                    'min': round(min(times), 2),
                    'max': round(max(times), 2),
                    'p95': round(percentile(times, 95), 2)
                }
        
        self.metrics['by_severity'] = severity_metrics
        
        # 날짜별 MTTR (주간)
        by_date = defaultdict(list)
        for incident in self.incidents:
            date = incident['created_at'][:10]
            by_date[date].append(incident['recovery_time_minutes'])
        
        date_metrics = {}
        for date in sorted(by_date.keys()):
            times = by_date[date]
            date_metrics[date] = {
                'count': len(times),
                'average': round(sum(times) / len(times), 2),
                'min': round(min(times), 2),
                'max': round(max(times), 2)
            }
        
        self.metrics['by_date'] = date_metrics
        
        print(f"✅ 메트릭 계산 완료")
        print(f"   - 총 인시던트: {self.metrics['total_incidents']}개")
        print(f"   - 평균 복구 시간: {self.metrics['average_mttr']}분")
        print(f"   - 중앙값: {self.metrics['median_mttr']}분")
        print(f"   - 범위: {self.metrics['min_mttr']} ~ {self.metrics['max_mttr']}분")
    
    def save_metrics(self, output_file: str = 'mttr-metrics.json') -> None:
        """메트릭을 JSON 파일로 저장"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        print(f"💾 메트릭 저장: {output_file}")
    
    def print_report(self) -> None:
        """MTTR 리포트 출력"""
        print("\n" + "="*70)
        print("📊 MTTR(Mean Time To Recovery) 리포트")
        print("="*70)
        
        if self.metrics['total_incidents'] == 0:
            print("분석할 인시던트가 없습니다.")
            return
        
        print(f"\n📈 종합 통계")
        print(f"  총 인시던트: {self.metrics['total_incidents']}개")
        print(f"  평균 복구 시간: {self.metrics['average_mttr']}분 ({self.metrics['average_mttr']/60:.1f}시간)")
        print(f"  중앙값: {self.metrics['median_mttr']}분")
        print(f"  최소: {self.metrics['min_mttr']}분")
        print(f"  최대: {self.metrics['max_mttr']}분")
        print(f"  표준편차: {self.metrics.get('stddev_mttr', 0)}분")
        print(f"  95 백분위: {self.metrics['p95_mttr']}분")
        print(f"  99 백분위: {self.metrics['p99_mttr']}분")
        
        if self.metrics['by_severity']:
            print(f"\n🎯 심각도별 MTTR")
            for severity in ['Critical', 'High', 'Medium', 'Low']:
                if severity in self.metrics['by_severity']:
                    stats = self.metrics['by_severity'][severity]
                    print(f"  [{severity}]")
                    print(f"    건수: {stats['count']}개")
                    print(f"    평균: {stats['average']}분")
                    print(f"    중앙값: {stats['median']}분")
                    print(f"    범위: {stats['min']} ~ {stats['max']}분")
                    print(f"    P95: {stats['p95']}분")
        
        if self.metrics.get('by_date'):
            print(f"\n📅 날짜별 MTTR (최근 5일)")
            dates = sorted(self.metrics['by_date'].keys(), reverse=True)[:5]
            for date in reversed(dates):
                data = self.metrics['by_date'][date]
                print(f"  {date}: 평균 {data['average']}분 ({data['count']}건, {data['min']}~{data['max']}분)")
        
        print(f"\n📋 최근 인시던트 (상위 10개)")
        for i, incident in enumerate(self.incidents[:10], 1):
            print(f"  {i}. #{incident['number']} - {incident['title'][:50]}")
            print(f"     복구: {incident['recovery_time_hours']}시간 | 심각도: {incident['severity']}")
        
        print("\n" + "="*70)
    
    def export_csv(self, output_file: str = 'mttr-incidents.csv') -> None:
        """인시던트 데이터를 CSV로 내보내기"""
        import csv
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Issue #', 'Title', 'Created At', 'Closed At', 
                'Recovery Time (min)', 'Recovery Time (hour)', 'Severity', 'Labels', 'URL'
            ])
            
            for incident in self.incidents:
                writer.writerow([
                    incident['number'],
                    incident['title'],
                    incident['created_at'],
                    incident['closed_at'],
                    incident['recovery_time_minutes'],
                    incident['recovery_time_hours'],
                    incident['severity'],
                    ' | '.join(incident['labels']),
                    incident['url']
                ])
        
        print(f"💾 CSV 저장: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='MTTR 분석 도구')
    parser.add_argument('--repo', required=True, help='리포지토리 (owner/repo)')
    parser.add_argument('--days', type=int, default=30, help='분석 기간 (일)')
    parser.add_argument('--incident-label', default='incident', help='인시던트 라벨명')
    parser.add_argument('--output', default='mttr-metrics.json', help='JSON 출력 파일')
    parser.add_argument('--csv', help='CSV 출력 파일')
    parser.add_argument('--print-report', action='store_true', help='리포트 출력')
    
    args = parser.parse_args()
    
    # GitHub 토큰 확인
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("❌ GITHUB_TOKEN 환경 변수가 설정되지 않았습니다.")
        print("GitHub Token을 설정하세요:")
        print("  export GITHUB_TOKEN=your_github_token")
        sys.exit(1)
    
    # MTTR 분석
    analyzer = MTTRAnalyzer(token, args.repo)
    analyzer.fetch_incidents(days=args.days, incident_label=args.incident_label)
    analyzer.calculate_metrics()
    analyzer.save_metrics(args.output)
    
    if args.csv:
        analyzer.export_csv(args.csv)
    
    if args.print_report:
        analyzer.print_report()
    else:
        # 기본적으로 요약 출력
        analyzer.print_report()


if __name__ == '__main__':
    main()
