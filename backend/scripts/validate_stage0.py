"""Stage 0 read-only data validation for asset and repair metrics."""
import json
import os
import random
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import case, func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import AiSessionLocal
from app.models.asset import AiAsset, AiAssetTransfer


def scalar(db, query):
    return db.execute(select(query)).scalar() or 0


def main():
    db = AiSessionLocal()
    try:
        total_assets = scalar(db, func.count(AiAsset.asset_id))
        missing_brand = db.query(AiAsset).filter((AiAsset.brand.is_(None)) | (AiAsset.brand == "")).count()
        missing_model = db.query(AiAsset).filter((AiAsset.model.is_(None)) | (AiAsset.model == "")).count()
        missing_buy_date = db.query(AiAsset).filter(AiAsset.buy_date.is_(None)).count()

        repair_filter = AiAssetTransfer.bill_type == 10700
        repair_total = db.query(AiAssetTransfer).filter(repair_filter).count()
        repair_assets = db.query(func.count(func.distinct(AiAssetTransfer.asset_id))).filter(repair_filter).scalar() or 0
        repair_unlinked = db.query(AiAssetTransfer).filter(repair_filter, ~AiAssetTransfer.asset_id.in_(db.query(AiAsset.asset_id))).count()
        repair_fee_total = db.query(func.coalesce(func.sum(AiAssetTransfer.fee), 0)).filter(repair_filter).scalar() or 0
        repair_fee_missing = db.query(AiAssetTransfer).filter(repair_filter, AiAssetTransfer.fee.is_(None)).count()
        repair_min_date = db.query(func.min(AiAssetTransfer.bill_date)).filter(repair_filter).scalar()
        repair_max_date = db.query(func.max(AiAssetTransfer.bill_date)).filter(repair_filter).scalar()

        groups = db.query(
            AiAsset.brand,
            AiAsset.model,
            AiAsset.class_id,
            func.count(AiAsset.asset_id).label("asset_count"),
            func.sum(case((AiAsset.is_idle == 1, 1), else_=0)).label("idle_count"),
            func.count(AiAssetTransfer.id).label("repair_count"),
            func.coalesce(func.sum(AiAssetTransfer.fee), 0).label("repair_fee"),
        ).outerjoin(
            AiAssetTransfer,
            (AiAssetTransfer.asset_id == AiAsset.asset_id) & repair_filter,
        ).group_by(AiAsset.brand, AiAsset.model, AiAsset.class_id).order_by(func.count(AiAsset.asset_id).desc()).limit(100).all()

        asset_ids = [row[0] for row in db.query(AiAsset.asset_id).order_by(AiAsset.asset_id).limit(1000).all()]
        random.seed(0)
        sample_ids = random.sample(asset_ids, min(10, len(asset_ids)))
        sample = []
        for asset_id in sample_ids:
            asset = db.query(AiAsset).filter(AiAsset.asset_id == asset_id).first()
            repairs = db.query(AiAssetTransfer).filter(repair_filter, AiAssetTransfer.asset_id == asset_id).order_by(AiAssetTransfer.bill_date).all()
            sample.append({
                "asset_id": asset.asset_id,
                "barcode": asset.barcode,
                "brand": asset.brand,
                "model": asset.model,
                "class_id": asset.class_id,
                "repair_count": len(repairs),
                "repair_fee": float(sum((item.fee or 0) for item in repairs)),
                "repair_dates": [str(item.bill_date) for item in repairs],
            })

        result = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "read_only": True,
            "repair_bill_type": 10700,
            "assets": {"total": total_assets, "missing_brand": missing_brand, "missing_model": missing_model, "missing_buy_date": missing_buy_date},
            "repairs": {
                "total": repair_total,
                "distinct_assets": repair_assets,
                "unlinked": repair_unlinked,
                "fee_total": float(repair_fee_total),
                "fee_missing": repair_fee_missing,
                "min_date": str(repair_min_date) if repair_min_date else None,
                "max_date": str(repair_max_date) if repair_max_date else None,
            },
            "brand_model_top100": [
                {"brand": row[0], "model": row[1], "class_id": row[2], "asset_count": row[3], "idle_count": row[4], "repair_count": row[5], "repair_fee": float(row[6] or 0)}
                for row in groups
            ],
            "sample_assets": sample,
            "compatibility_notes": [
                "聚合使用 SQLAlchemy 表达式，避免依赖 MySQL 专有函数。",
                "迁移 DDL 中的 JSON 类型需在目标国产数据库验证，必要时使用 TEXT。",
            ],
        }
        output = Path(os.environ.get("STAGE0_REPORT", str(ROOT.parent / "docs" / "stage0-validation-report.json")))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"report": str(output), "assets": result["assets"], "repairs": result["repairs"]}, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
