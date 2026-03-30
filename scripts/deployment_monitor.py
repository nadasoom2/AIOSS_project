#!/usr/bin/env python3
"""
배포 빈도 모니터링 및 경고 시스템

배포 빈도가 목표에서 벗어나면 경고를 발생시킵니다.
Slack, Email 등으로 알림을 전송할 수 있습니다.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

try:
    from github import Github
except ImportError:
    print("❌ PyGithub 설치 필요: pip install PyGithub")
    exit(1)


class AlertLevel(Enum):
    """경고 수준"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert:
    """경고 클래스"""
    
    def __init__(self, level: AlertLevel, message: str, metric: str, value: float, threshold: float):
        self.level = level
        self.message = message
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'message': self.message,
            'metric': self.metric,
            'value': self.value,
            'threshold': self.threshold
        }


class DeploymentMonitor:
    """배포 현황 모니터"""
    
    def __init__(self, repo_name: str, config: Dict):
        """
        초기화
        
        Args:
            repo_name: 리포지토리 이름 (owner/repo)
            config: 설정 딕셔너리
        """
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            raise ValueError("GITHUB_TOKEN 환경변수 필수")
        
        self.g = Github(token)
        self.repo = self.g.get_repo(repo_name)
        self.config = config
        self.alerts: List[Alert] = []
        self.metrics: Dict = {}
    
    def check_deployment_frequency(self) -> None:
        """배포 빈도 확인"""
        days = 30
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        deployments = list(self.repo.get_deployments(environment='production'))
        successful = [
            d for d in deployments
            if d.created_at >= start_date and 
            any(s.state == 'success' for s in d.get_statuses())
        ]
        
        daily_freq = len(successful) / days if days > 0 else 0
        self.metrics['daily_frequency'] = daily_freq
        
        # 목표와 비교
        target = self.config.get('frequency_targets', {}).get('daily', 1.0)
        min_threshold = target * 0.7  # 목표의 70%
        
        if daily_freq < min_threshold:
            self.alerts.append(Alert(
                AlertLevel.CRITICAL,
                f"배포 빈도가 목표(일 {target}회) 이하입니다",
                'deployment_frequency',
                daily_freq,
                target
            ))
        elif daily_freq < target:
            self.alerts.append(Alert(
                AlertLevel.WARNING,
                f"배포 빈도가 목표(일 {target}회)에 미달했습니다",
                'deployment_frequency',
                daily_freq,
                target
            ))
        else:
            self.alerts.append(Alert(
                AlertLevel.INFO,
                f"배포 빈도가 목표를 달성했습니다",
                'deployment_frequency',
                daily_freq,
                target
            ))
    
    def check_deployment_success_rate(self) -> None:
        """배포 성공률 확인"""
        days = 30
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        deployments = list(self.repo.get_deployments(environment='production'))
        recent = [d for d in deployments if d.created_at >= start_date]
        
        if not recent:
            return
        
        successful = sum(
            1 for d in recent
            if any(s.state == 'success' for s in d.get_statuses())
        )
        
        success_rate = (successful / len(recent) * 100) if recent else 0
        self.metrics['success_rate'] = success_rate
        
        # 목표와 비교
        target = self.config.get('success_rate_target', 95)
        
        if success_rate < target:
            self.alerts.append(Alert(
                AlertLevel.WARNING,
                f"배포 성공률({success_rate:.1f}%)이 목표({target}%)에 미달했습니다",
                'success_rate',
                success_rate,
                target
            ))
        else:
            self.alerts.append(Alert(
                AlertLevel.INFO,
                f"배포 성공률이 목표({target}%)를 달성했습니다",
                'success_rate',
                success_rate,
                target
            ))
    
    def check_frequency_trend(self) -> None:
        """배포 빈도 추세 확인"""
        # 최근 7일 vs 이전 7일 비교
        now = datetime.utcnow()
        recent_period_end = now
        recent_period_start = now - timedelta(days=7)
        previous_period_end = recent_period_start
        previous_period_start = previous_period_end - timedelta(days=7)
        
        def count_deployments(start, end):
            deployments = list(self.repo.get_deployments(environment='production'))
            return sum(
                1 for d in deployments
                if start <= d.created_at <= end and
                any(s.state == 'success' for s in d.get_statuses())
            )
        
        recent_count = count_deployments(recent_period_start, recent_period_end)
        previous_count = count_deployments(previous_period_start, previous_period_end)
        
        if previous_count > 0:
            change_rate = ((recent_count - previous_count) / previous_count) * 100
            self.metrics['frequency_change_rate'] = change_rate
            
            threshold = self.config.get('frequency_drop_threshold', 20)
            
            if change_rate < -threshold:
                self.alerts.append(Alert(
                    AlertLevel.WARNING,
                    f"배포 빈도가 {abs(change_rate):.1f}% 감소했습니다",
                    'frequency_trend',
                    recent_count,
                    previous_count
                ))
    
    def get_alerts(self) -> List[Alert]:
        """경고 목록 반환"""
        return self.alerts
    
    def get_critical_alerts(self) -> List[Alert]:
        """심각한 경고만 반환"""
        return [a for a in self.alerts if a.level == AlertLevel.CRITICAL]
    
    def export_alerts_json(self, filepath: str) -> None:
        """경고를 JSON으로 내보내기"""
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': self.metrics,
            'alerts': [a.to_dict() for a in self.alerts]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 경고 내보내기 완료: {filepath}")
    
    def print_summary(self) -> None:
        """요약 출력"""
        print("\n" + "="*60)
        print("📊 배포 빈도 모니터링 요약")
        print("="*60)
        
        print(f"\n📈 메트릭:")
        for metric, value in self.metrics.items():
            print(f"  {metric}: {value}")
        
        print(f"\n⚠️  경고 ({len(self.alerts)}개):")
        if not self.alerts:
            print("  경고 없음 ✅")
        else:
            for alert in self.alerts:
                emoji = {'info': '💬', 'warning': '⚠️', 'critical': '🔴'}
                print(f"  {emoji.get(alert.level.value, '•')} [{alert.level.value.upper()}] {alert.message}")
        
        print("\n" + "="*60)


def load_config(config_file: str = 'deployment-frequency-metrics.yml') -> Dict:
    """설정 파일 로드"""
    import yaml
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('deployment_frequency', {})
    except FileNotFoundError:
        print(f"⚠️  설정 파일을 찾을 수 없습니다: {config_file}")
        return {}
    except ImportError:
        print("❌ PyYAML이 필요합니다. 설치: pip install PyYAML")
        return {}


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='배포 빈도 모니터링')
    parser.add_argument('--repo', required=True, help='리포지토리 (owner/repo)')
    parser.add_argument('--config', default='deployment-frequency-metrics.yml', help='설정 파일')
    parser.add_argument('--export', help='JSON 경고 내보내기')
    
    args = parser.parse_args()
    
    # 설정 로드
    config = load_config(args.config)
    default_config = {
        'frequency_targets': {'daily': 1.0},
        'success_rate_target': 95,
        'frequency_drop_threshold': 20
    }
    config = {**default_config, **config}
    
    # 모니터링 실행
    try:
        monitor = DeploymentMonitor(args.repo, config)
        monitor.check_deployment_frequency()
        monitor.check_deployment_success_rate()
        monitor.check_frequency_trend()
        monitor.print_summary()
        
        if args.export:
            monitor.export_alerts_json(args.export)
        
        # 심각한 경고 있으면 종료 코드 1
        if monitor.get_critical_alerts():
            exit(1)
    
    except Exception as e:
        print(f"❌ 오류: {e}")
        exit(1)
