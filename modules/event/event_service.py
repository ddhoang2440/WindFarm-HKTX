from models.event import EventInput, EventRecord

async def process_event(data: EventInput):
    # 1. Lưu vào DB
    record = EventRecord(**data.model_dump())
    await record.insert()
    print(f"[BACKEND] Đã lưu Event {data.event_id} vào DB")
    
    # 2. Báo lên Datadog
    
    return record