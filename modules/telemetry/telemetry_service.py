from datetime import timedelta
import httpx
from config.settings import settings
from models.telemetry import TelemetryInput, TelemetryRecord

async def calculate_derived_features(asset_id: int, current_time):
    """
    Tính 3 features phái sinh bằng MongoDB Aggregation.
    """
    six_hours_ago = current_time - timedelta(hours=6)
    
    # 1. Dùng Aggregation để tính mean và std (MongoDB làm, cực nhanh)
    pipeline = [
        {"$match": {
            "asset_id": asset_id,
            "time_stamp": {"$gte": six_hours_ago}
        }},
        {"$group": {
            "_id": None,
            "wind_speed_roll_mean_6h": {"$avg": "$wind_speed"},
            "power_roll_std_6h": {"$stdDevPop": "$power_output"}
        }}
    ]
    
    result = await TelemetryRecord.aggregate(pipeline).to_list()
    
    # Nếu chưa đủ dữ liệu 6h (ví dụ mới chạy lần đầu)
    if not result:
        return {
            "wind_speed_roll_mean_6h": 0.0,
            "power_roll_std_6h": 0.0,
            "theoretical_power_index": 0.0
        }
    
    stats = result[0]
    
    # 2. Tính theoretical_power_index
    # TODO: CÔNG THỨC CHÍNH XÁC. TẠM DÙNG CÔNG THỨC GIẢ LẬP
    theoretical_power_index = stats["wind_speed_roll_mean_6h"] * 10.0 
    
    return {
        "wind_speed_roll_mean_6h": round(stats["wind_speed_roll_mean_6h"], 4),
        "power_roll_std_6h": round(stats["power_roll_std_6h"], 4),
        "theoretical_power_index": round(theoretical_power_index, 4)
    }

async def process_telemetry(data: TelemetryInput):
    # 1. Lưu dữ liệu thô vào DB
    record = TelemetryRecord(**data.model_dump())
    await record.insert()
    print(f"[BACKEND] Đã lưu Telemetry tuabin {data.asset_id}")
    
    # 2. Tính 3 features phái sinh
    derived = await calculate_derived_features(data.asset_id, data.time_stamp)
    
    # 3. Ghép thành 7 features để gửi sang Long
    ml_payload = {
        "asset_id": data.asset_id,
        "time_stamp": data.time_stamp.isoformat(),
        "wind_speed": data.wind_speed,
        "power_output": data.power_output,
        "ambient_temp": data.ambient_temp,
        "status_type_id": data.status_type_id,
        "wind_speed_roll_mean_6h": derived["wind_speed_roll_mean_6h"],
        "power_roll_std_6h": derived["power_roll_std_6h"],
        "theoretical_power_index": derived["theoretical_power_index"],
    }
    
    # 4. Gọi sang ML Service của Long
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.ML_SERVICE_URL}/predict",
                json=ml_payload,
                timeout=10.0
            )
            print(f"[BACKEND] ML trả về: {response.json()}")
        except Exception as e:
            print(f"[BACKEND] Lỗi gọi ML: {e}")
    
    return record
