import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
class ImagePayload(BaseModel):
    mode: Literal["dish", "ingredients", "product"]
    image_url: Optional[str] = Field(None, description="URL for the uploaded image")
    filename: Optional[str] = None

class BarcodePayload(BaseModel):
    barcode: str

class HistoryQuery(BaseModel):
    limit: Optional[int] = 25

# ---------- Helpers ----------

def _save_history(entry: Dict[str, Any]):
    try:
        from database import create_document
        create_document("analysis", entry)
    except Exception:
        # Database might be unavailable; ignore to keep API responsive
        pass


def _list_history(limit: int = 25):
    try:
        from database import get_documents
        docs = get_documents("analysis", {}, limit)
        # Convert ObjectId to string if present
        for d in docs:
            if "_id" in d:
                d["id"] = str(d.pop("_id"))
        return docs
    except Exception:
        return []

# ---------- Basic routes ----------
@app.get("/")
def read_root():
    return {"message": "Nutrition Insights API running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# ---------- Analysis endpoints (mocked logic) ----------
@app.post("/api/analyze/dish")
def analyze_dish(payload: ImagePayload):
    if payload.mode != "dish":
        raise HTTPException(status_code=400, detail="Invalid mode for this endpoint")

    result = {
        "cuisine": "Mediterranean",
        "portion_size": "420 g",
        "nutrition": {
            "kcal": 585,
            "protein_g": 28,
            "carbs_g": 62,
            "fat_g": 24
        },
        "image_url": payload.image_url,
        "filename": payload.filename
    }

    _save_history({"type": "dish", "result": result, "image_url": payload.image_url})
    return {"status": "ok", "data": result}

@app.post("/api/analyze/ingredients")
def analyze_ingredients(payload: ImagePayload):
    if payload.mode != "ingredients":
        raise HTTPException(status_code=400, detail="Invalid mode for this endpoint")

    recognized = [
        {"name": "Avocado", "confidence": 0.96},
        {"name": "Cherry Tomatoes", "confidence": 0.92},
        {"name": "Lime", "confidence": 0.88},
        {"name": "Cilantro", "confidence": 0.86},
    ]
    recipes = [
        {"title": "Avocado Lime Salad", "image": "https://images.unsplash.com/photo-1551218808-94e220e084d2", "time": "10 min"},
        {"title": "Tomato Avocado Toast", "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c", "time": "15 min"},
    ]
    result = {"ingredients": recognized, "recipes": recipes, "image_url": payload.image_url}
    _save_history({"type": "ingredients", "result": result, "image_url": payload.image_url})
    return {"status": "ok", "data": result}

@app.post("/api/scan-product")
def scan_product(payload: BarcodePayload | ImagePayload):
    # If barcode provided, use that; else use image
    if isinstance(payload, BarcodePayload):
        code = payload.barcode
    else:
        code = payload.filename or "0000000000000"

    product = {
        "name": "Premium Greek Yogurt 2%",
        "brand": "Aurora",
        "barcode": code,
        "image_url": getattr(payload, "image_url", None),
        "nutrition_table": [
            {"label": "Energy", "value": "260 kJ / 62 kcal"},
            {"label": "Fat", "value": "2.0 g"},
            {"label": "- of which saturates", "value": "1.3 g"},
            {"label": "Carbohydrate", "value": "3.6 g"},
            {"label": "- of which sugars", "value": "3.6 g"},
            {"label": "Protein", "value": "5.5 g"},
            {"label": "Salt", "value": "0.10 g"},
        ],
        "warnings": [
            {"type": "info", "text": "Contains dairy"}
        ]
    }
    _save_history({"type": "product", "result": product, "image_url": getattr(payload, "image_url", None)})
    return {"status": "ok", "data": product}

@app.get("/api/history")
def get_history(limit: int = 25):
    return {"status": "ok", "data": _list_history(limit)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
