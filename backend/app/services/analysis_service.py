"""统计分析服务：驾驶舱数据、指标计算、趋势分析"""
from datetime import datetime, date, timedelta
from sqlalchemy import func, case, and_, or_
from ..database import AiSessionLocal
from ..models.asset import AiAsset, AiAssetTransfer, AiCheckRecord
from ..models.dict import AiDepartment, AiAssetClass, AiAssetState
from ..models.warning import AiWarning, AiIdlePool, AiScrapEvaluation


class AnalysisService:
    def __init__(self):
        self.db = AiSessionLocal()

    def close(self):
        self.db.close()

    def get_overview(self):
        """资产总览指标"""
        # 原系统在用状态：10400在用、10610内调、10640外调、10670个调、10680变更、11400(默认在用)
        IN_USE_STATES = [10400, 10610, 10640, 10670, 10680, 11400, 11410]
        IDLE_STATES = [10500]
        SCRAP_STATES = [15000, 14900, 19900]
        total = self.db.query(func.count(AiAsset.asset_id)).scalar() or 0
        total_value = self.db.query(func.sum(AiAsset.buy_price)).scalar() or 0
        current_value = self.db.query(func.sum(AiAsset.current_value)).scalar() or 0
        in_use = self.db.query(func.count(AiAsset.asset_id)).filter(AiAsset.state_id.in_(IN_USE_STATES)).scalar() or 0
        idle = self.db.query(func.count(AiAsset.asset_id)).filter(or_(AiAsset.state_id.in_(IDLE_STATES), AiAsset.is_idle == 1)).scalar() or 0
        scrap = self.db.query(func.count(AiAsset.asset_id)).filter(AiAsset.state_id.in_(SCRAP_STATES)).scalar() or 0
        warning_count = self.db.query(func.count(AiWarning.id)).filter(AiWarning.status == 0).scalar() or 0
        # 账实相符率（最近一次盘点）
        latest_check = self.db.query(func.max(AiCheckRecord.check_date)).scalar()
        match_rate = 0
        if latest_check:
            total_checked = self.db.query(func.count(AiCheckRecord.id)).filter(
                AiCheckRecord.check_date == latest_check, AiCheckRecord.check_state.in_([1, 2, 3])
            ).scalar() or 0
            normal = self.db.query(func.count(AiCheckRecord.id)).filter(
                AiCheckRecord.check_date == latest_check, AiCheckRecord.check_state == 1
            ).scalar() or 0
            match_rate = round(normal / total_checked * 100, 1) if total_checked else 0
        return {
            "total_count": total,
            "total_value": round(total_value, 2),
            "current_value": round(current_value, 2),
            "in_use_count": in_use,
            "idle_count": idle,
            "scrap_count": scrap,
            "warning_count": warning_count,
            "idle_rate": round(idle / total * 100, 1) if total else 0,
            "match_rate": match_rate,
            "latest_check_date": str(latest_check) if latest_check else None,
            "data_cutoff": str(self.db.query(func.max(AiAsset.sync_time)).scalar()) if self.db.query(func.max(AiAsset.sync_time)).scalar() else None,
            "rules_version": "dashboard-v1",
            "generated_at": datetime.now().isoformat(),
            "metric_definitions": {
                "idle_rate": "闲置资产数 / 资产总数；闲置状态或 is_idle=1",
                "match_rate": "最近一次盘点中状态为正常的记录 / 有盘点结果记录",
                "warning_count": "当前 status=0 的预警数量"
            }
        }

    def get_class_distribution(self):
        """按一级分类统计"""
        rows = self.db.query(
            AiAsset.class_path,
            func.count(AiAsset.asset_id).label("cnt"),
            func.sum(AiAsset.buy_price).label("val")
        ).filter(AiAsset.class_path.isnot(None)).group_by(AiAsset.class_path).all()
        # 取一级分类
        result = {}
        for r in rows:
            top_class = r[0].split(" > ")[0] if r[0] else "未分类"
            result[top_class] = result.get(top_class, {"count": 0, "value": 0})
            result[top_class]["count"] += r[1] or 0
            result[top_class]["value"] += round(r[2] or 0, 2)
        return [{"name": k, "count": v["count"], "value": v["value"]} for k, v in sorted(result.items(), key=lambda x: -x[1]["count"])[:15]]

    def get_state_distribution(self):
        """按状态统计"""
        rows = self.db.query(
            AiAsset.state_name,
            func.count(AiAsset.asset_id).label("cnt")
        ).filter(AiAsset.state_name.isnot(None)).group_by(AiAsset.state_name).all()
        return [{"name": r[0] or "未知", "value": r[1]} for r in rows if r[1] > 0][:20]

    def get_monthly_trend(self, months=12):
        """近12个月增减趋势"""
        end = date.today().replace(day=1)
        result = []
        for i in range(months - 1, -1, -1):
            m = end - timedelta(days=30 * i)
            m = m.replace(day=1)
            next_m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
            added = self.db.query(func.count(AiAssetTransfer.id)).filter(
                AiAssetTransfer.bill_type.in_([10100, 10300]),
                AiAssetTransfer.bill_date >= m, AiAssetTransfer.bill_date < next_m
            ).scalar() or 0
            reduced = self.db.query(func.count(AiAssetTransfer.id)).filter(
                AiAssetTransfer.bill_type.in_([15000, 15100, 15200, 15300, 15400, 15500, 19000]),
                AiAssetTransfer.bill_date >= m, AiAssetTransfer.bill_date < next_m
            ).scalar() or 0
            result.append({"month": m.strftime("%Y-%m"), "added": added, "reduced": reduced,
                           "metric_basis": "入库 bill_type=10100/10300；减少 bill_type=15000-15500/19000"})
        return result

    def get_dept_ranking(self):
        """部门资产排名"""
        rows = self.db.query(
            AiAsset.dept_id, AiAsset.dept_name,
            func.count(AiAsset.asset_id).label("cnt"),
            func.sum(AiAsset.buy_price).label("val"),
            func.sum(case((AiAsset.is_idle == 1, 1), else_=0)).label("idle_cnt")
        ).filter(AiAsset.dept_name.isnot(None), AiAsset.dept_name != "").group_by(
            AiAsset.dept_name
        ).order_by(func.count(AiAsset.asset_id).desc()).all()
        return [{
            "dept_id": r[0], "dept": r[1], "count": r[2], "value": round(r[3] or 0, 2),
            "idle_count": r[4], "idle_rate": round(r[4] / r[2] * 100, 1) if r[2] else 0,
            "metric_basis": "按部门聚合资产台账，闲置率=闲置资产数/部门资产数"
        } for r in rows[:15]]

    def get_department_headcount(self):
        """获取部门人数（用于人均资产）"""
        rows = self.db.query(AiDepartment.dept_name, AiDepartment.headcount).all()
        return {r[0]: r[1] or 0 for r in rows}

    def get_operational_effectiveness(self, months=12, dept_id=None):
        """Monthly operational outcomes with explicit metric definitions."""
        months = min(max(int(months or 12), 1), 24)
        end = date.today().replace(day=1)
        result = []
        for i in range(months - 1, -1, -1):
            current = (end - timedelta(days=31 * i)).replace(day=1)
            next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            transfer_query = self.db.query(func.count(AiAssetTransfer.id)).filter(
                AiAssetTransfer.bill_date >= current, AiAssetTransfer.bill_date < next_month
            )
            savings_query = self.db.query(func.coalesce(func.sum(AiAssetTransfer.fee), 0)).filter(
                AiAssetTransfer.bill_date >= current, AiAssetTransfer.bill_date < next_month,
                AiAssetTransfer.bill_type.in_([10100, 10300])
            )
            if dept_id:
                transfer_query = transfer_query.filter(AiAssetTransfer.new_dept_id == dept_id)
                savings_query = savings_query.filter(AiAssetTransfer.new_dept_id == dept_id)
            transfers = transfer_query.scalar() or 0
            savings = savings_query.scalar() or 0
            checks = self.db.query(func.count(AiCheckRecord.id)).filter(
                AiCheckRecord.check_date >= current, AiCheckRecord.check_date < next_month,
                AiCheckRecord.check_state.in_([1, 2, 3])
            ).scalar() or 0
            anomalies = self.db.query(func.count(AiCheckRecord.id)).filter(
                AiCheckRecord.check_date >= current, AiCheckRecord.check_date < next_month,
                AiCheckRecord.check_state.in_([2, 3])
            ).scalar() or 0
            warning_total = self.db.query(func.count(AiWarning.id)).filter(
                AiWarning.create_time >= current, AiWarning.create_time < next_month
            ).scalar() or 0
            warning_done = self.db.query(func.count(AiWarning.id)).filter(
                AiWarning.create_time >= current, AiWarning.create_time < next_month, AiWarning.status == 1
            ).scalar() or 0
            evaluations = self.db.query(func.count(AiScrapEvaluation.id)).filter(
                AiScrapEvaluation.eval_date >= current, AiScrapEvaluation.eval_date < next_month
            ).scalar() or 0
            compliant = self.db.query(func.count(AiScrapEvaluation.id)).filter(
                AiScrapEvaluation.eval_date >= current, AiScrapEvaluation.eval_date < next_month,
                AiScrapEvaluation.eval_result.in_([1, 2, 3])
            ).scalar() or 0
            result.append({"month": current.strftime("%Y-%m"), "transfer_count": transfers,
                           "idle_saving_amount": round(float(savings), 2),
                           "check_anomaly_rate": round(anomalies / checks * 100, 1) if checks else 0,
                           "warning_response_rate": round(warning_done / warning_total * 100, 1) if warning_total else 0,
                           "scrap_compliance_rate": round(compliant / evaluations * 100, 1) if evaluations else 0,
                           "metric_basis": {"idle_saving_amount": "transfer fee sum for inbound bill types; replace with validated saving ledger when available",
                                            "check_anomaly_rate": "check_state 2/3 divided by check_state 1/2/3",
                                            "warning_response_rate": "handled status=1 divided by warnings created in month",
                                            "scrap_compliance_rate": "evaluations with explicit result 1/2/3 divided by evaluations in month"}})
        return {"months": result, "rules_version": "operations-v1", "generated_at": datetime.now().isoformat(),
                "scope": {"dept_id": dept_id, "description": "global scope" if not dept_id else "transfers grouped by new_dept_id; non-department facts remain global"}}
