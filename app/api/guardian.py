from fastapi import APIRouter, Response
from app.core.config import settings
import csv, io

router = APIRouter(prefix=f"{settings.API_V1_STR}/guardian", tags=["guardian"])

@router.post("/export")
def export_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["trace_id","status","decision_hash"])
    # stub demo
    w.writerow(["RUN-0001","done","abcd1234"])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition":"attachment; filename=guardian.csv"})
