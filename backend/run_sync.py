"""手动触发全量数据同步"""
import sys
sys.path.insert(0, '.')
from app.services.sync_service import SyncService

if __name__ == '__main__':
    svc = SyncService()
    print("开始全量同步...")
    result = svc.sync_all()
    print(f"同步完成: {result}")
