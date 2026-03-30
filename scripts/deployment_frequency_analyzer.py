#!/usr/bin/env python3
"""
Deployment Frequency 분석 도구

GitHub 리포지토리의 배포 빈도 메트릭을 분석합니다.
- 일일/주간/월간 배포 횟수
- 배포 성공률
- 환경별 배포 현황
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

try:
    from github import Github
    from github.GithubException import GithubException
except ImportError:
    print("❌ PyGithub이 설치되지 않았습니다.")
    print("설치 명령: pip install PyGithub")
    sys.exit(1)


class DeploymentFrequencyAnalyzer:
    """배포 빈도를 분석하는 클래스"""
    
    def __init__(self, token: str, repo_name: str):
        """
        초기화
        
        Args:
            token: GitHub API 토큰
            repo_name: 리포지토리 이름 (owner/repo 형식)
        """
        self.g = Github(token)
        self.repo = self.g.get_repo(repo_name)
        self.deployments: List[Dict] = []
        self.releases: List[Dict] = []
    
    def fetch_deployments(self, days: int = 30, environment: str = 'production') -> None:
        """
        배포 데이터 수집
        
        Args:
            days: 분석 기간 (일)
            environment: 환경명
        """
        print(f"🔍 최근 {days}일간 '{environment}' 환경의 배포를 수집 중...")
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            deployments = list(self.repo.get_deployments(environment=environment))
            
            for deployment in deployments:
                if deployment.created_at < start_date:
                    break
                
                # 배포 상태 확인
                statuses = list(deployment.get_statuses())
                status = None
                if statuses:
                    latest_status = statuses[0]
                    status = latest_status.state
                
                self.deployments.append({
                    'date': deployment.created_at,
                    'sha': deployment.sha[:7],
                    'ref': deployment.ref,
                    'creator': deployment.creator.login if deployment.creator else 'unknown',
                    'environment': deployment.environment,
                    'status': status,
                    'url': deployment.url
                })
            
            print(f"✅ {len(self.deployments)}개의 배포 기록 수집 완료")
        
        except GithubException as e:
            print(f"❌ GitHub API 오류: {e}")
            sys.exit(1)
    
    def fetch_releases(self, days: int = 30) -> None:
        """
        릴리스 데이터 수집
        
        Args:
            days: 분석 기간 (일)
        """
        print(f"🔍 최근 {days}일간의 릴리스를 수집 중...")
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            for release in self.repo.get_releases():
                if release.published_at and release.published_at < start_date:
                    break
                
                if release.published_at and release.published_at >= start_date:
                    release_type = self._classify_release(release.tag_name)
                    
                    self.releases.append({
                        'tag': release.tag_name,
                        'date': release.published_at,
                        'name': release.title or release.tag_name,
                        'type': release_type,
                        'prerelease': release.prerelease,
                        'draft': release.draft
                    })
            
            print(f"✅ {len(self.releases)}개의 릴리스 기록 수집 완료")
        
        except GithubException as e:
            print(f"❌ GitHub API 오류: {e}")
            sys.exit(1)
    
    def _classify_release(self, tag: str) -> str:
        """
        릴리스 태그 분류 (Major/Minor/Patch)
        
        Args:
            tag: 릴리스 태그
        
        Returns:
            릴리스 유형
        """
        # v1.0.0 형식 분석
        parts = tag.lstrip('v').split('.')
        try:
            if len(parts) >= 3:
                major, minor, patch = map(int, [p.split('-')[0] for p in parts[:3]])
                if patch == 0 and minor == 0:
                    return 'major'
                elif patch == 0:
                    return 'minor'
                else:
                    return 'patch'
        except (ValueError, IndexError):
            pass
        
        return 'other'
    
    def calculate_statistics(self, days: int = 30) -> Dict:
        """
        배포 통계 계산
        
        Args:
            days: 분석 기간
        
        Returns:
            통계 딕셔너리
        """
        if not self.deployments:
            return {
                'total_deployments': 0,
                'success_rate': 0,
                'daily_average': 0.0,
                'days_with_deployments': 0
            }
        
        # 성공한 배포만 필터링
        successful = [d for d in self.deployments if d['status'] == 'success']
        failed = [d for d in self.deployments if d['status'] == 'failure']
        
        # 날짜별 분류
        deployment_by_date = defaultdict(list)
        for deployment in successful:
            date = deployment['date'].date()
            deployment_by_date[date].append(deployment)
        
        days_with_deployments = len(deployment_by_date)
        daily_average = len(successful) / days if days > 0 else 0
        
        # 성공률 계산
        total_deployments = len(self.deployments)
        success_rate = (len(successful) / total_deployments * 100) if total_deployments > 0 else 0
        
        # 배포 간 시간 계산
        time_between = []
        sorted_deployments = sorted(successful, key=lambda x: x['date'])
        for i in range(1, len(sorted_deployments)):
            delta = (sorted_deployments[i]['date'] - sorted_deployments[i-1]['date']).total_seconds() / 3600
            time_between.append(delta)
        
        avg_time_between = sum(time_between) / len(time_between) if time_between else 0
        
        return {
            'total_deployments': total_deployments,
            'successful_deployments': len(successful),
            'failed_deployments': len(failed),
            'success_rate': round(success_rate, 2),
            'daily_average': round(daily_average, 2),
            'days_with_deployments': days_with_deployments,
            'avg_time_between_deployments_hours': round(avg_time_between, 2),
            'analysis_period_days': days
        }
    
    def calculate_release_statistics(self) -> Dict:
        """릴리스 통계 계산"""
        if not self.releases:
            return {
                'total_releases': 0,
                'major_releases': 0,
                'minor_releases': 0,
                'patch_releases': 0
            }
        
        release_types = defaultdict(int)
        for release in self.releases:
            if not release['prerelease'] and not release['draft']:
                release_types[release['type']] += 1
        
        return {
            'total_releases': len([r for r in self.releases if not r['prerelease']]),
            'major_releases': release_types.get('major', 0),
            'minor_releases': release_types.get('minor', 0),
            'patch_releases': release_types.get('patch', 0)
        }
    
    def get_deployment_dora_level(self, daily_freq: float) -> Tuple[str, str]:
        """
        DORA 등급 결정
        
        Args:
            daily_freq: 일일 배포 빈도
        
        Returns:
            (등급, 설명)
        """
        if daily_freq >= 1.0:
            return 'elite', '엘리트 성과 (일 1회 이상)'
        elif daily_freq >= 0.143:  # 주 1회
            return 'high', '높은 성과 (주 1회)'
        elif daily_freq >= 0.033:  # 월 1회
            return 'medium', '중간 성과 (월 1회)'
        else:
            return 'low', '낮은 성과 (6개월 1회 이하)'
    
    def print_report(self) -> None:
        """분석 리포트 출력"""
        stats = self.calculate_statistics(30)
        release_stats = self.calculate_release_statistics()
        
        print("\n" + "="*70)
        print("📊 Deployment Frequency 분석 보고서")
        print("="*70)
        
        print(f"\n🚀 배포 현황 (지난 30일)")
        print(f"  총 배포 시도: {stats['total_deployments']:>6} 회")
        print(f"  성공한 배포: {stats['successful_deployments']:>6} 회")
        print(f"  실패한 배포: {stats['failed_deployments']:>6} 회")
        print(f"  성공률:      {stats['success_rate']:>6}%")
        print(f"  배포한 날:   {stats['days_with_deployments']:>6} 일")
        
        print(f"\n📈 배포 빈도")
        print(f"  일일 평균:   {stats['daily_average']:>6} 회/일")
        print(f"  배포 간격:   {stats['avg_time_between_deployments_hours']:>6} 시간")
        
        # DORA 등급
        level, description = self.get_deployment_dora_level(stats['daily_average'])
        level_emoji = {'elite': '🟢', 'high': '🟢', 'medium': '🟡', 'low': '🔴'}
        print(f"\n{level_emoji.get(level, '⚪')} DORA 등급: {description}")
        
        # 릴리스 현황
        print(f"\n📦 릴리스 현황 (지난 30일)")
        print(f"  총 릴리스:   {release_stats['total_releases']:>6} 회")
        print(f"  Major:      {release_stats['major_releases']:>6} 회")
        print(f"  Minor:      {release_stats['minor_releases']:>6} 회")
        print(f"  Patch:      {release_stats['patch_releases']:>6} 회")
        
        # 추천사항
        print(f"\n💡 추천사항")
        if stats['daily_average'] < 0.143:
            print(f"  ⚠️  배포 빈도가 낮습니다. 자동화 강화를 권장합니다.")
        elif stats['daily_average'] >= 1.0:
            print(f"  ✅ 배포 빈도가 우수합니다. 현재 수준 유지를 권장합니다.")
        
        if stats['success_rate'] < 95:
            print(f"  ⚠️  배포 성공률이 낮습니다. 테스트 강화를 권장합니다.")
        
        print("\n" + "="*70)
    
    def export_json(self, filepath: str) -> None:
        """JSON으로 내보내기"""
        stats = self.calculate_statistics(30)
        release_stats = self.calculate_release_statistics()
        
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'deployment_statistics': stats,
            'release_statistics': release_stats,
            'dora_level': self.get_deployment_dora_level(stats['daily_average'])[0],
            'deployments': self.deployments,
            'releases': self.releases
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ JSON 내보내기 완료: {filepath}")
    
    def export_csv(self, filepath: str) -> None:
        """CSV로 내보내기"""
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'sha', 'environment', 'status', 'creator'])
            writer.writeheader()
            
            for deployment in sorted(self.deployments, key=lambda x: x['date']):
                writer.writerow({
                    'date': deployment['date'].isoformat(),
                    'sha': deployment['sha'],
                    'environment': deployment['environment'],
                    'status': deployment['status'],
                    'creator': deployment['creator']
                })
        
        print(f"✅ CSV 내보내기 완료: {filepath}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='GitHub Deployment Frequency 분석 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''사용 예시:
  python deployment_frequency_analyzer.py --repo owner/repo
  python deployment_frequency_analyzer.py --repo owner/repo --env staging --export report.json
  python deployment_frequency_analyzer.py --repo owner/repo --days 60 --csv deployments.csv
        '''
    )
    
    parser.add_argument('--token', help='GitHub API 토큰 (GITHUB_TOKEN 환경변수 사용 가능)')
    parser.add_argument('--repo', required=True, help='리포지토리 이름 (owner/repo 형식)')
    parser.add_argument('--env', default='production', help='배포 환경명 (기본: production)')
    parser.add_argument('--days', type=int, default=30, help='분석 기간 일수 (기본: 30)')
    parser.add_argument('--export', help='JSON 파일로 내보내기')
    parser.add_argument('--csv', help='CSV 파일로 내보내기')
    
    args = parser.parse_args()
    
    # 토큰 확인
    token = args.token or os.getenv('GITHUB_TOKEN')
    if not token:
        print("❌ GitHub 토큰이 필요합니다.")
        print("다음 중 하나로 제공하세요:")
        print("  1. --token 인자")
        print("  2. GITHUB_TOKEN 환경변수")
        sys.exit(1)
    
    # 분석 실행
    analyzer = DeploymentFrequencyAnalyzer(token, args.repo)
    analyzer.fetch_deployments(days=args.days, environment=args.env)
    analyzer.fetch_releases(days=args.days)
    analyzer.print_report()
    
    if args.export:
        analyzer.export_json(args.export)
    
    if args.csv:
        analyzer.export_csv(args.csv)


if __name__ == '__main__':
    main()
