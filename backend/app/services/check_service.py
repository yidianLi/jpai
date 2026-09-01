"""智能盘点分析服务"""
from datetime import datetime, date, timedelta
from sqlalchemy import case, func, and_
from ..database import AiSessionLocal
from ..models.asset import AiAsset, AiCheckRecord


class CheckService:
    def __init__(self):
        self.db = AiSessionLocal()

    def close(self):
        self.db.close()

    def get_check_tasks(self):
        """获取盘点任务列表"""
        rows = self.db.query(
            AiCheckRecord.check_bid, AiCheckRecord.check_title, AiCheckRecord.check_date,
            func.count(AiCheckRecord.id).label("total"),
            func.sum(case((AiCheckRecord.check_state == 1, 1), else_=0)).label("normal"),
            func.sum(case((AiCheckRecord.check_state == 2, 1), else_=0)).label("loss"),
            func.sum(case((AiCheckRecord.check_state == 3, 1), else_=0)).label("mismatch"),
            func.sum(case((AiCheckRecord.check_state == 0, 1), else_=0)).label("unchecked"),
        ).group_by(AiCheckRecord.check_bid, AiCheckRecord.check_title, AiCheckRecord.check_date
        ).order_by(AiCheckRecord.check_date.desc()).all()
        return [{
            "check_bid": r[0], "title": r[1], "date": str(r[2]) if r[2] else None,
            "total": r[3], "normal": r[4] or 0, "loss": r[5] or 0,
            "mismatch": r[6] or 0, "unchecked": r[7] or 0,
            "match_rate": round((r[4] or 0) / r[3] * 100, 1) if r[3] else 0
        } for r in rows]

    def get_check_detail(self, check_bid, check_state=None, page=1, size=20):
        """获取盘点明细"""
        q = self.db.query(AiCheckRecord).filter(AiCheckRecord.check_bid == check_bid)
        if check_state is not None:
            q = q.filter(AiCheckRecord.check_state == check_state)
        total = q.count()
        rows = q.offset((page-1)*size).limit(size).all()
        state_map = {0: "未盘", 1: "正常", 2: "盘亏", 3: "不符"}
        return {
            "total": total, "page": page, "size": size,
            "list": [{
                "id": r.id, "asset_id": r.asset_id, "barcode": r.barcode,
                "check_state": r.check_state, "state_text": state_map.get(r.check_state, "未知"),
                "old_dept": r.old_dept, "new_dept": r.new_dept,
                "old_position": r.old_position, "new_position": r.new_position,
                "old_responsible": r.old_responsible, "new_responsible": r.new_responsible,
                "handle_status": r.handle_status
            } for r in rows]
        }

    def get_check_diagnosis(self, check_bid):
        """盘点结果智能诊断"""
        records = self.db.query(AiCheckRecord).filter(AiCheckRecord.check_bid == check_bid).all()
        total = len(records)
        normal = sum(1 for r in records if r.check_state == 1)
        loss = sum(1 for r in records if r.check_state == 2)
        mismatch = sum(1 for r in records if r.check_state == 3)
        # 按部门统计盘亏
        dept_loss = {}
        for r in records:
            if r.check_state == 2 and r.old_dept:
                dept_loss[r.old_dept] = dept_loss.get(r.old_dept, 0) + 1
        # 按位置统计不符
        pos_mismatch = {}
        for r in records:
            if r.check_state == 3 and r.old_position:
                pos_mismatch[r.old_position] = pos_mismatch.get(r.old_position, 0) + 1
        # 高价值盘亏
        high_value_loss = []
        loss_assets = [r for r in records if r.check_state == 2]
        for r in loss_assets[:20]:
            asset = self.db.query(AiAsset).filter(AiAsset.asset_id == r.asset_id).first()
            if asset and (asset.buy_price or 0) > 5000:
                high_value_loss.append({
                    "asset_name": asset.asset_name, "barcode": asset.barcode,
                    "buy_price": asset.buy_price, "dept": asset.dept_name
                })
        return {
            "total": total, "normal": normal, "loss": loss, "mismatch": mismatch,
            "match_rate": round(normal / total * 100, 1) if total else 0,
            "dept_loss_ranking": sorted(dept_loss.items(), key=lambda x: -x[1])[:10],
            "position_mismatch_ranking": sorted(pos_mismatch.items(), key=lambda x: -x[1])[:10],
            "high_value_loss": high_value_loss,
            "suggestions": self._generate_suggestions(loss, mismatch, dept_loss)
        }

    def _generate_suggestions(self, loss, mismatch, dept_loss):
        """生成整改建议"""
        suggestions = []
        if loss > 0:
            suggestions.append(f"本次盘点盘亏{loss}台，建议逐台核实去向，对责任人进行追责")
            top_dept = sorted(dept_loss.items(), key=lambda x: -x[1])[:1]
            if top_dept:
                suggestions.append(f"盘亏集中在{top_dept[0][0]}（{top_dept[0][1]}台），建议重点检查该部门资产管理流程")
        if mismatch > 0:
            suggestions.append(f"账实不符{mismatch}台，建议及时更新系统中的存放位置和责任人信息")
        if loss == 0 and mismatch == 0:
            suggestions.append("本次盘点账实相符，资产管理状况良好")
        suggestions.append("建议将盘点结果纳入部门绩效考核，强化资产保管责任")
        return suggestions

    def get_optimized_check_path(self, check_bid=None):
        """盘点路径优化：按仓库→位置排序"""
        q = self.db.query(AiAsset).filter(AiAsset.state_id.notin_([15000, 15100, 15200, 19900]))
        assets = q.order_by(AiAsset.warehouse_id, AiAsset.position).all()
        return [{
            "asset_id": a.asset_id, "barcode": a.barcode, "asset_name": a.asset_name,
            "warehouse": a.warehouse_id, "position": a.position, "dept": a.dept_name
        } for a in assets[:500]]
