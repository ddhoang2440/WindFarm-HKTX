# WindFarm Monitoring System – Backend

Hệ thống giám sát trang trại điện gió thời gian thực.  
Backend xây dựng trên **FastAPI** + **MongoDB Atlas** + **Beanie ODM**, tích hợp AI fault prediction và WebSocket real-time.

---
```bash
cd WindFarm/backend/WindFarm-Backend

# Cài đặt dependencies
pip install -r requirements.txt
```

---

## Chạy Ứng Dụng

### Development (có auto-reload)

```bash
cd WindFarm/backend/WindFarm-Backend

# Dùng pip
uvicorn src.main:app --reload --port 8000


```
## Cấu Hình Biến Môi Trường

File `.env` nằm tại thư mục gốc `WindFarm-Backend/`. Các biến cần thiết:

```env
# ── Application ──────────────────────────────────────────────
APP_NAME=WindFarm Monitoring System
APP_VERSION=0.1.0
DEBUG=true
HOST=0.0.0.0
PORT=8000

# ── MongoDB Atlas ────────────────────────────────────────────
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net
MONGO_DB_NAME=<database_name>

# ── JWT Authentication ───────────────────────────────────────
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── Datadog (tùy chọn) ──────────────────────────────────────
DD_AGENT_HOST=localhost
DD_TRACE_AGENT_PORT=8126
DD_SERVICE=windfarm-backend
DD_ENV=development
DD_API_KEY=your-datadog-api-key

# ── AI Model ─────────────────────────────────────────────────
MODEL_PATH=src/modules/AI_Agent/model_weights/fault_classifier.pkl
```

>  **Lưu ý**: Thay `<username>`, `<password>`, `<cluster>`, `<database_name>` bằng thông tin MongoDB Atlas thực tế.



## Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Framework | FastAPI |
| Database | MongoDB Atlas (Motor + Beanie ODM) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| AI/ML | scikit-learn / XGBoost (.pkl model) |
| Real-time | WebSocket (native FastAPI) |
| Monitoring | Datadog (ddtrace) |
| Data Processing | pandas, numpy |
| Package Manager | uv / pip |

---
