# Repository path: rti_backend/app/api/routes/legal_knowledge.py
"""Admin review and user retrieval APIs for legal principle memory."""

import psycopg
from fastapi import APIRouter, Header, HTTPException, Query, Request
from uuid import UUID

from app.core.database import get_connection
from app.core.admin_auth import require_admin
from app.models.legal_principle import PrincipleCreate, PrincipleReview
from app.repositories.legal_principles import (
    create_pending_principle, list_pending_principles, review_principle,
    search_verified_principles,
)

router = APIRouter(prefix="/knowledge/principles", tags=["कानूनी सिद्धांत-स्मृति"])


@router.post("", summary="समीक्षा के लिए कानूनी सिद्धांत दर्ज करें")
def create_principle(payload: PrincipleCreate, request: Request,
                     x_csrf_token: str | None = Header(default=None)) -> dict:
    require_admin(request, x_csrf_token)
    try:
        result = create_pending_principle(payload.model_dump(mode="json"))
        return {"created": True, **result,
                "message": "सिद्धांत pending_review में सुरक्षित हुआ; अभी उपयोगकर्ता उत्तरों में लागू नहीं होगा।"}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Legal knowledge store unavailable") from exc


@router.get("/pending", summary="मानव समीक्षा की प्रतीक्षा में सिद्धांत")
def pending_principles(request: Request, limit: int = Query(default=50, ge=1, le=100)) -> dict:
    require_admin(request)
    try:
        items = list_pending_principles(limit)
        return {"items": items, "count": len(items)}
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Legal knowledge store unavailable") from exc


@router.post("/{principle_id}/review", summary="सिद्धांत की कानूनी स्थिति की मानव समीक्षा")
def review_one(principle_id: UUID, payload: PrincipleReview, request: Request,
               x_csrf_token: str | None = Header(default=None)) -> dict:
    session = require_admin(request, x_csrf_token)
    try:
        result = review_principle(
            principle_id=principle_id, status=payload.legal_status.value,
            reviewer_note=payload.reviewer_note, reviewer=session["sub"],
            superseded_by_document_id=payload.superseded_by_document_id,
            subsequent_treatment=payload.subsequent_treatment,
        )
        if not result:
            raise HTTPException(status_code=404, detail="सिद्धांत नहीं मिला या स्रोत verified नहीं है")
        return {"reviewed": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Legal knowledge store unavailable") from exc


@router.get("/search", summary="केवल वर्तमान सत्यापित ratio decidendi खोजें")
def search_principles(query: str = Query(min_length=2, max_length=250),
                      limit: int = Query(default=8, ge=1, le=20)) -> dict:
    try:
        items = search_verified_principles(query, limit)
        return {"query": query, "items": items, "count": len(items),
                "note": "केवल मानव-सत्यापित वर्तमान ratio; obiter और बाद के उपचार से बदले सिद्धांत स्वतः शामिल नहीं।"}
    except (psycopg.Error, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Legal knowledge search unavailable") from exc
