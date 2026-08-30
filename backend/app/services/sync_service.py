"""
数据同步服务
支持两种通道：1) 直连原库（默认） 2) 简普API（文档到位后切换）
"""
import logging
from datetime import datetime, date
from sqlalchemy import text
from ..database import SourceSessionLocal, AiSessionLocal
from ..models.asset import AiAsset, AiAssetTransfer, AiCheckRecord
from ..models.dict import AiCompany, AiDepartment, AiUser, AiAssetClass, AiAssetState
from ..config import settings

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self):
        self.src = SourceSessionLocal()
        self.ai = AiSessionLocal()

    def close(self):
        self.src.close()
        self.ai.close()

    def _get_class_path(self, class_id, class_map):
        """递归获取分类全路径"""
        path = []
        cid = class_id
        visited = set()
        while cid and cid not in visited and cid in class_map:
            visited.add(cid)
            c = class_map[cid]
            path.insert(0, c["name"])
            cid = c["parent_id"]
        return " > ".join(path)

    def sync_dictionaries(self):
        """同步字典表：单位、部门、分类、状态"""
        try:
            # 单位
            rows = self.src.execute(text("SELECT CID, P_CID, CO_CODE, CO_NAME, STATE FROM jp_company")).fetchall()
            self.ai.query(AiCompany).delete()
            for r in rows:
                self.ai.add(AiCompany(company_id=r[0], parent_id=r[1], company_code=r[2], company_name=r[3], state=r[4] or 1))
            # 部门
            rows = self.src.execute(text("SELECT DID, CID, P_DID, DEPT_CODE, DEPT_NAME, STATE FROM jp_dept")).fetchall()
            self.ai.query(AiDepartment).delete()
            for r in rows:
                self.ai.add(AiDepartment(dept_id=r[0], company_id=r[1], parent_id=r[2], dept_code=r[3], dept_name=r[4], state=r[5] or 1))
            # 分类
            rows = self.src.execute(text("SELECT CSID, P_CSID, CLASS_CODE, CLASS_NAME, USE_YEAR, LOWEST, STATE FROM fs_class")).fetchall()
            class_map = {r[0]: {"parent_id": r[1], "name": r[3]} for r in rows}
            self.ai.query(AiAssetClass).delete()
            for r in rows:
                self.ai.add(AiAssetClass(class_id=r[0], parent_id=r[1], class_code=r[2], class_name=r[3], use_year=r[4], is_lowest=r[5] or 0, state=r[6] or 1))
            # 状态
            rows = self.src.execute(text("SELECT SID, STATE_NAME, REMARK, STATE_IDX, STATE FROM fs_state")).fetchall()
            self.ai.query(AiAssetState).delete()
            for r in rows:
                self.ai.add(AiAssetState(state_id=r[0], state_name=r[1], state_label=r[2], state_idx=r[3] or r[0], is_valid=r[4] or 1))
            self.ai.commit()
            logger.info(f"字典同步完成: 单位{len(rows)}条")
        except Exception as e:
            self.ai.rollback()
            logger.error(f"字典同步失败: {e}")
            raise

    def sync_users(self):
        """同步用户"""
        try:
            rows = self.src.execute(text("""
                SELECT u.UID, u.USER_CODE, u.USER_NAME, u.PASSWORD, u.CID, u.DID, u.RID,
                       u.MOBILE, u.EMAIL, u.STATE, r.ROLE_NAME
                FROM jp_user u LEFT JOIN jp_role r ON u.RID = r.RID
            """)).fetchall()
            self.ai.query(AiUser).delete()
            for r in rows:
                is_admin = 1 if (r[10] and "管理员" in r[10]) or r[1] == "admin" else 0
                self.ai.add(AiUser(
                    user_id=r[0], user_code=r[1], user_name=r[2], password=r[3],
                    company_id=r[4], dept_id=r[5], role_id=r[6], mobile=r[7], email=r[8],
                    state=r[9] or 1, role_name=r[10], is_admin=is_admin
                ))
            self.ai.commit()
            logger.info(f"用户同步完成: {len(rows)}条")
        except Exception as e:
            self.ai.rollback()
            logger.error(f"用户同步失败: {e}")
            raise

    def sync_assets(self):
        """同步资产主表（全量）"""
        try:
            # 先加载分类和单位部门映射
            class_rows = self.src.execute(text("SELECT CSID, P_CSID, CLASS_NAME FROM fs_class")).fetchall()
            class_map = {r[0]: {"parent_id": r[1], "name": r[2]} for r in class_rows}
            company_rows = self.src.execute(text("SELECT CID, CO_NAME FROM jp_company")).fetchall()
            company_map = {r[0]: r[1] for r in company_rows}
            dept_rows = self.src.execute(text("SELECT DID, DEPT_NAME FROM jp_dept")).fetchall()
            dept_map = {r[0]: r[1] for r in dept_rows}
            state_rows = self.src.execute(text("SELECT SID, REMARK FROM fs_state")).fetchall()
            state_map = {r[0]: r[1] for r in state_rows}

            rows = self.src.execute(text("""
                SELECT BOMID, BARCODE, BOM_NAME, MODEL, BRAND_NAME, SN, CSID, STATE,
                       CID, DID, WHID, POSITION, RESPONSIBLE, USER, BUY_PRICE, BUY_DATE,
                       START_DATE, USE_YEAR, CHANGE_DATE, OVER_DATE, STATUS2, INVOICE_NO,
                       CONTRACT_NO, SUPPLIER_NAME
                FROM fs_bom
            """)).fetchall()

            self.ai.query(AiAsset).delete()
            now = datetime.now()
            batch = []
            for r in rows:
                buy_date = r[15]
                use_year = r[17] or 0
                expire_date = None
                if buy_date and use_year:
                    try:
                        expire_date = date(buy_date.year + use_year, buy_date.month, buy_date.day)
                    except ValueError:
                        expire_date = date(buy_date.year + use_year, 12, 31)
                # 净值计算（直线法）
                current_value = r[14] or 0
                if buy_date and use_year and r[14]:
                    used_days = (now.date() - buy_date).days
                    total_days = use_year * 365
                    if total_days > 0 and used_days > 0:
                        depreciable = r[14] * (1 - settings.RESIDUAL_RATE)
                        depreciation = min(depreciable, depreciable * used_days / total_days)
                        current_value = round(r[14] - depreciation, 2)
                # 数据质量评分
                dq_score = 100
                if not r[2] or r[2] in ("*", "1", "2", "3", "11"):
                    dq_score -= 30
                if not r[8]: dq_score -= 10  # 单位
                if not r[9]: dq_score -= 10  # 部门
                if not r[14]: dq_score -= 10  # 价值
                if not r[15]: dq_score -= 10  # 购置日期
                dq_score = max(0, dq_score)

                batch.append(AiAsset(
                    asset_id=r[0], barcode=r[1], asset_name=r[2], model=r[3], brand=r[4],
                    sn=r[5], class_id=r[6], class_path=self._get_class_path(r[6], class_map),
                    state_id=r[7], state_name=state_map.get(r[7], ""),
                    company_id=r[8], company_name=company_map.get(r[8], ""),
                    dept_id=r[9], dept_name=dept_map.get(r[9], ""),
                    warehouse_id=r[10], position=r[11], responsible=r[12], user_name=r[13],
                    buy_price=r[14], buy_date=buy_date, start_date=r[16], use_year=use_year,
                    expire_date=expire_date, current_value=current_value,
                    change_date=r[18], over_date=r[19], status2=r[20],
                    invoice_no=r[21], contract_no=r[22], supplier_name=r[23],
                    data_quality_score=dq_score, clean_status=2 if dq_score < 70 else 0,
                    sync_time=now
                ))
                if len(batch) >= 1000:
                    self.ai.add_all(batch)
                    self.ai.commit()
                    batch = []
            if batch:
                self.ai.add_all(batch)
                self.ai.commit()
            logger.info(f"资产同步完成: {len(rows)}条")
        except Exception as e:
            self.ai.rollback()
            logger.error(f"资产同步失败: {e}")
            raise

    def sync_transfers(self):
        """同步资产流转记录"""
        try:
            state_rows = self.src.execute(text("SELECT SID, REMARK FROM fs_state")).fetchall()
            state_map = {r[0]: r[1] for r in state_rows}
            rows = self.src.execute(text("""
                SELECT bl.BOMID, b.BILL_NO, b.SID, b.BILL_DATE, b.HANDLER,
                       bl.O_STATE, bl.N_STATE, bl.O_DID, bl.N_DID,
                       bl.O_RESPONSIBLE, bl.N_RESPONSIBLE, bl.O_POSITION, bl.N_POSITION, bl.RATE
                FROM fs_bill_list bl JOIN fs_bill b ON bl.BID = b.BID
                WHERE bl.BOMID IS NOT NULL
            """)).fetchall()
            self.ai.query(AiAssetTransfer).delete()
            batch = []
            for r in rows:
                batch.append(AiAssetTransfer(
                    asset_id=r[0], bill_no=r[1], bill_type=r[2],
                    bill_type_name=state_map.get(r[2], ""), bill_date=r[3], handler=r[4],
                    old_state=r[5], new_state=r[6], old_dept_id=r[7], new_dept_id=r[8],
                    old_responsible=r[9], new_responsible=r[10], old_position=r[11],
                    new_position=r[12], fee=r[13]
                ))
                if len(batch) >= 1000:
                    self.ai.add_all(batch)
                    self.ai.commit()
                    batch = []
            if batch:
                self.ai.add_all(batch)
                self.ai.commit()
            logger.info(f"流转记录同步完成: {len(rows)}条")
        except Exception as e:
            self.ai.rollback()
            logger.error(f"流转记录同步失败: {e}")
            raise

    def sync_check_records(self):
        """同步盘点记录"""
        try:
            rows = self.src.execute(text("""
                SELECT cl.BOMID, cb.BID, cb.TITLE, cb.BILL_DATE, cl.BARCODE,
                       cl.CHECK_STATE, cl.O_DID, cl.N_DID, cl.O_POSITION, cl.N_POSITION,
                       cl.O_RESPONSIBLE, cl.N_RESPONSIBLE
                FROM fs_chk_bill_list cl JOIN fs_chk_bill cb ON cl.BID = cb.BID
            """)).fetchall()
            self.ai.query(AiCheckRecord).delete()
            batch = []
            for r in rows:
                batch.append(AiCheckRecord(
                    asset_id=r[0], check_bid=r[1], check_title=r[2], check_date=r[3],
                    barcode=r[4], check_state=r[5], old_dept=str(r[6] or ""),
                    new_dept=str(r[7] or ""), old_position=r[8], new_position=r[9],
                    old_responsible=r[10], new_responsible=r[11]
                ))
                if len(batch) >= 1000:
                    self.ai.add_all(batch)
                    self.ai.commit()
                    batch = []
            if batch:
                self.ai.add_all(batch)
                self.ai.commit()
            logger.info(f"盘点记录同步完成: {len(rows)}条")
        except Exception as e:
            self.ai.rollback()
            logger.error(f"盘点记录同步失败: {e}")
            raise

    def sync_all(self):
        """执行全量同步"""
        self.sync_dictionaries()
        self.sync_users()
        self.sync_assets()
        self.sync_transfers()
        self.sync_check_records()
        self.close()
        return {"status": "success", "message": "全量同步完成"}
