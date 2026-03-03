"""KB REST API Controller - 파일 업로드 및 버전 관리"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
import json
import logging

from app.config import settings
from app.middleware.auth import verify_okta_token
from ..application.service import KBApplicationService
from ..infrastructure.repositories.dynamodb_kb_repository import DynamoDBKBRepository
from ..infrastructure.repositories.dynamodb_version_repository import DynamoDBVersionRepository
from ..infrastructure.repositories.mock_kb_repository import MockKBRepository
from ..infrastructure.repositories.mock_version_repository import MockVersionRepository
from ..dto.request import CreateKBRequest, UpdateKBRequest, KBStatusUpdate
from ..dto.response import (
    KBResponse, KBListResponse, KBVersionListResponse,
    KBFilesResponse
)
from ..exception.exceptions import KBNotFoundException

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_mock_mode() -> bool:
    """Mock 모드 여부 확인"""
    return settings.ENVIRONMENT in ("dev", "development", "local")


def get_kb_service() -> KBApplicationService:
    """KB Service 의존성 주입"""
    if _is_mock_mode() and not settings.DYNAMODB_KB_TABLE:
        logger.info("📦 Using MockKBRepository (demo mode)")
        kb_repository = MockKBRepository()
        version_repository = MockVersionRepository()
    else:
        kb_repository = DynamoDBKBRepository()
        version_repository = DynamoDBVersionRepository()
    return KBApplicationService(kb_repository, version_repository)


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_kb(
    name: str = Form(...),
    description: str = Form(...),
    team_tags: str = Form("[]"),  # JSON string
    files: List[UploadFile] = File(...),
    token_payload: dict = Depends(verify_okta_token),
    service: KBApplicationService = Depends(get_kb_service)
):
    """KB 생성 (파일 업로드)"""
    import json
    import traceback

    try:
        user_id = token_payload["sub"]
        team_tags_list = json.loads(team_tags)

        print(f"📦 Creating KB: {name} with {len(files)} files")
        kb = await service.create_kb_with_files(name, description, team_tags_list, files, user_id)
        print(f"✅ KB created successfully: {kb.id}")
        return {"data": kb.dict(), "status": 201}
    except Exception as e:
        print(f"❌ Error creating KB: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create KB: {str(e)}"
        )


@router.get("/{kb_id}", response_model=dict)
async def get_kb(
    kb_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: KBApplicationService = Depends(get_kb_service)
):
    """KB 상세 조회"""
    try:
        kb = await service.get_kb(kb_id)
        return {"data": kb.dict(), "status": 200}
    except KBNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=dict)
async def list_kbs(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    status: str = None,
    token_payload: dict = Depends(verify_okta_token),
    service: KBApplicationService = Depends(get_kb_service)
):
    """KB 목록 조회 (검색, 상태 필터 지원)"""
    result = await service.list_kbs(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        team_tags=None
    )
    return {
        "data": [item.dict() for item in result.items],
        "pagination": {
            "page": result.page,
            "pageSize": result.page_size,
            "totalItems": result.total,
            "totalPages": (result.total + result.page_size - 1) // result.page_size
        }
    }


@router.put("/{kb_id}", response_model=dict)
async def update_kb(
    kb_id: str,
    request: UpdateKBRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: KBApplicationService = Depends(get_kb_service)
):
    """KB 메타정보 수정"""
    try:
        user_id = token_payload["sub"]
        response = await service.update_kb(kb_id, request, user_id)
        return {"data": response.dict(), "status": 200}
    except KBNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{kb_id}/status", response_model=dict)
async def change_kb_status(
    kb_id: str,
    request: KBStatusUpdate,
    token_payload: dict = Depends(verify_okta_token),
    service: KBApplicationService = Depends(get_kb_service)
):
    """KB 상태 변경 (enabled/disabled)"""
    try:
        kb = await service.change_kb_status(kb_id, request.enabled)
        return {"data": kb.dict(), "status": 200}
    except KBNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{kb_id}/versions", response_model=dict)
async def get_kb_versions(
    kb_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: KBApplicationService = Depends(get_kb_service)
):
    """KB 버전 목록 조회"""
    try:
        result = await service.get_kb_versions(kb_id)
        return {"data": result.dict(), "status": 200}
    except KBNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{kb_id}/files", response_model=dict)
async def get_kb_files(
    kb_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: KBApplicationService = Depends(get_kb_service)
):
    """KB 현재 파일 목록 조회"""
    try:
        result = await service.get_kb_files(kb_id)
        return {"data": result.dict(), "status": 200}
    except KBNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{kb_id}/files", response_model=dict)
async def update_kb_files(
    kb_id: str,
    files: Optional[List[UploadFile]] = File(None),
    deleted_files: str = Form("[]"),  # JSON string of file names to delete
    token_payload: dict = Depends(verify_okta_token),
    service: KBApplicationService = Depends(get_kb_service)
):
    """KB 파일 업데이트 (추가/삭제)"""
    try:
        user_id = token_payload["sub"]
        deleted_file_names = json.loads(deleted_files)

        kb = await service.update_kb_files(
            kb_id=kb_id,
            new_files=files or [],
            deleted_file_names=deleted_file_names,
            user_id=user_id
        )
        return {"data": kb.dict(), "status": 200}
    except KBNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
