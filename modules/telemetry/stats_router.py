from fastapi import APIRouter, Depends
from core.security import verify_token
from models.telemetry import TelemetryRecord

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry Stats"])

@router.get("/stats", dependencies=[Depends(verify_token)])
async def get_telemetry_stats(asset_id: int):
    pipeline = [
        {"$match": {"asset_id": asset_id}},
        {"$group": {
            "_id": "$asset_id",
            "avg_wind_speed": {"$avg": "$wind_speed"},
            "min_wind_speed": {"$min": "$wind_speed"},
            "max_wind_speed": {"$max": "$wind_speed"},
            "avg_power_output": {"$avg": "$power_output"},
            "min_power_output": {"$min": "$power_output"},
            "max_power_output": {"$max": "$power_output"},
            "total_records": {"$sum": 1}
        }}
    ]
    
    result = await TelemetryRecord.aggregate(pipeline).to_list()
    
    if not result:
        return {"asset_id": asset_id, "message": "Chưa có dữ liệu"}
    
    stats = result[0]
    stats["asset_id"] = stats.pop("_id")
    
    
    return stats