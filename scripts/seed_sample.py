"""
Seed data MẪU để test API.
Chỉ lấy N dòng đầu từ CSV, insert thẳng vào MongoDB.

Usage (chạy từ thư mục WindFarm-Backend/):
    python -m scripts.seed_sample
    python -m scripts.seed_sample --csv "Wind Farm A/Wind Farm A/datasets/0.csv" --limit 200
    python -m scripts.seed_sample --reset
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ============================================================
# Thêm project root vào sys.path
# ============================================================
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ============================================================
# Import models & config
# ============================================================
from src.models.Telemetry import Telemetry
from src.models.Prediction import Prediction, PredictionClass
from src.models.Turbine import Turbine, TurbineStatus
from src.models.Incident import Incident, IncidentSeverity
from src.models.User import User, UserRole, UserStatus
from src.config.database import connect_to_mongo
from src.core.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Default paths
# ============================================================
DEFAULT_CSV = ROOT / "Wind Farm A" / "Wind Farm A" / "datasets" / "0.csv"


# ============================================================
# Helpers
# ============================================================
def _safe_float(v):
    """Chuyển về float, trả None nếu NaN/không hợp lệ."""
    if v is None:
        return None
    try:
        f = float(v)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _parse_timestamp(v) -> datetime:
    """Parse timestamp, fallback utcnow()."""
    try:
        return pd.to_datetime(v).to_pydatetime()
    except Exception:
        return datetime.utcnow()


# ============================================================
# Reset data
# ============================================================
async def reset_data(asset_id: int | None = None) -> None:
    """Xóa data cũ. Nếu asset_id=None thì xóa hết."""
    if asset_id is None:
        logger.warning("⚠️  Xóa TOÀN BỘ data trong các collection")
        for model in [Telemetry, Prediction, Incident, Turbine]:
            coll = model.get_motor_collection()
            result = await coll.delete_many({})
            logger.info(f"  → {coll.name}: xóa {result.deleted_count} documents")
    else:
        logger.warning(f"⚠️  Xóa data của asset_id={asset_id}")
        for model in [Telemetry, Prediction, Incident, Turbine]:
            coll = model.get_motor_collection()
            result = await coll.delete_many({"asset_id": asset_id})
            logger.info(f"  → {coll.name}: xóa {result.deleted_count} documents")


# ============================================================
# Seed logic
# ============================================================
async def seed_turbine(asset_id: int) -> Turbine:
    """Tạo hoặc lấy Turbine hiện có."""
    turbine = await Turbine.find_one(Turbine.asset_id == asset_id)
    if turbine:
        logger.info(f"Turbine asset_id={asset_id} đã tồn tại, dùng lại")
        return turbine

    turbine = Turbine(
        asset_id=asset_id,
        name=f"WT-{asset_id:03d}",
        status=TurbineStatus.NORMAL,
        capacity_kw=2000.0,
        manufacturer="Sample Manufacturer",
        location_lat=10.7626,
        location_lng=106.6602,
    )
    await turbine.insert()
    logger.info(f"✓ Tạo Turbine asset_id={asset_id} name={turbine.name}")
    return turbine


async def seed_telemetry(df: pd.DataFrame, asset_id: int) -> list[Telemetry]:
    """Insert telemetry theo batch, trả về list đã insert."""
    logger.info(f"Bắt đầu insert {len(df)} telemetry...")

    batch: list[Telemetry] = []
    for _, row in df.iterrows():
        ts = _parse_timestamp(row.get("time_stamp"))

        reading = Telemetry(
            asset_id=asset_id,
            timestamp=ts,
            # Mapping suy đoán - không quan trọng khi test API
            wind_speed=_safe_float(row.get("wind_speed_3_avg")),
            power=_safe_float(row.get("power_29_avg")),
            rotor_speed=_safe_float(row.get("sensor_1_avg")),
            generator_speed=_safe_float(row.get("sensor_2_avg")),
            ambient_temperature=_safe_float(row.get("sensor_0_avg")),
            nacelle_temperature=_safe_float(row.get("sensor_0_avg")),
            gearbox_temperature=_safe_float(row.get("sensor_0_avg")),
            blade_pitch_angle=_safe_float(row.get("sensor_52_avg")),
            # Lưu toàn bộ cột CSV vào raw_payload
            raw_payload={
                k: (None if pd.isna(v) else v)
                for k, v in row.to_dict().items()
            },
        )
        batch.append(reading)

    await Telemetry.insert_many(batch)
    logger.info(f"✓ Insert xong {len(batch)} telemetry")
    return batch


async def seed_predictions(
    df: pd.DataFrame,
    asset_id: int,
    telemetry_docs: list[Telemetry],
) -> None:
    """Insert Prediction tương ứng với mỗi Telemetry."""
    logger.info(f"Bắt đầu insert {len(df)} prediction...")

    batch: list[Prediction] = []
    for i, (_, row) in enumerate(df.iterrows()):
        telemetry = telemetry_docs[i]
        status_id = int(row.get("status_type_id", 0))
        pred_class = "fault" if status_id != 0 else "normal"

        pred = Prediction(
            asset_id=asset_id,
            timestamp=telemetry.timestamp,
            telemetry_id=telemetry.id,
            prediction=PredictionClass(pred_class),
            confidence=0.95,
            model_version="seed-sample",
        )
        batch.append(pred)

    await Prediction.insert_many(batch)
    logger.info(f"✓ Insert xong {len(batch)} prediction")


async def seed_sample_incident(asset_id: int) -> Incident:
    """Tạo 1 incident mẫu để test API /incidents."""
    incident = Incident(
        asset_id=asset_id,
        label="Sample fault for API testing",
        severity=IncidentSeverity.CRITICAL,
        notes="Tạo tự động bởi seed_sample.py",
    )
    await incident.insert()
    logger.info(f"✓ Tạo incident mẫu: event_id={incident.event_id}")
    return incident


async def seed_admin_user() -> User:
    from src.modules.Auth.auth_service import _hash_password

    email = "admin@windfarm.com"   # ← đổi .local → .com
    existing = await User.find_one(User.email == email)
    if existing:
        logger.info(f"User admin đã tồn tại: {email}")
        return existing

    user = User(
        email=email,
        password_hash=_hash_password("Admin123456"),
        full_name="Sample Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    await user.insert()
    logger.info(f"✓ Tạo admin user: {email} / password: Admin123456")
    return user
# ============================================================
# Orchestrator
# ============================================================
async def seed(csv_path: str, limit: int, reset: bool = False) -> None:
    # 0. Reset nếu yêu cầu
    if reset:
        await reset_data()

    # 1. Đọc CSV
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.error(f"❌ Không tìm thấy file: {csv_file}")
        logger.error(f"   Thư mục hiện tại: {Path.cwd()}")
        logger.error(f"   Đường dẫn đầy đủ: {csv_file.resolve()}")
        return

    logger.info(f"Đọc CSV: {csv_file}")
    df = pd.read_csv(csv_file, sep=";")
    logger.info(f"  → Tổng {len(df)} dòng, {len(df.columns)} cột")

    df = df.head(limit)
    logger.info(f"  → Lấy {len(df)} dòng đầu để seed")

    asset_id = int(df["asset_id"].iloc[0])

    # 2. Turbine
    turbine = await seed_turbine(asset_id)

    # 3. Telemetry
    telemetry_docs = await seed_telemetry(df, asset_id)

    # 4. Prediction
    await seed_predictions(df, asset_id, telemetry_docs)

    # 5. Incident mẫu
    await seed_sample_incident(asset_id)

    # 6. Admin user
    await seed_admin_user()

    # 7. Cập nhật turbine.last_seen_at
    turbine.last_seen_at = telemetry_docs[-1].timestamp
    turbine.updated_at = datetime.utcnow()
    await turbine.save()
    logger.info(f"✓ Cập nhật turbine.last_seen_at")

    # Report
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ SEED HOÀN TẤT")
    logger.info("=" * 60)
    logger.info(f"  Turbine:      asset_id={asset_id}")
    logger.info(f"  Telemetry:    {len(telemetry_docs)} dòng")
    logger.info(f"  Predictions:  {len(df)} dòng")
    logger.info(f"  Incidents:    1 (mẫu)")
    logger.info(f"  Admin user:   admin@windfarm.local / admin123")
    logger.info("\n  Test API:")
    logger.info(f"    GET    /api/turbines")
    logger.info(f"    GET    /api/turbines/{asset_id}")
    logger.info(f"    GET    /api/telemetry/overview")
    logger.info(f"    GET    /api/telemetry/{asset_id}?limit=10")
    logger.info(f"    GET    /api/incidents/active")
    logger.info(f"    POST   /api/telemetry/ingest")
    logger.info("=" * 60)


# ============================================================
# Main
# ============================================================
async def main():
    parser = argparse.ArgumentParser(
        description="Seed data mẫu vào MongoDB để test API"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_CSV),
        help=f"Đường dẫn CSV (default: {DEFAULT_CSV.name})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Số dòng lấy từ CSV (default: 200)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Xóa data cũ trước khi seed",
    )
    args = parser.parse_args()

    # Kết nối MongoDB
    logger.info("Kết nối MongoDB...")
    await connect_to_mongo()
    logger.info("✓ Đã kết nối MongoDB")

    await seed(args.csv, args.limit, reset=args.reset)


if __name__ == "__main__":
    asyncio.run(main())