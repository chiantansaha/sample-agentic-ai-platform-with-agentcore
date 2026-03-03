"""KB Application Service - 파일 업로드 및 버전 관리

파일 업로드를 통한 KB 생성 및 버전 관리를 지원합니다.
"""
from typing import List, Optional
from fastapi import UploadFile
import threading
import traceback

from ..domain.repositories.kb_repository import KBRepository
from ..domain.repositories.version_repository import VersionRepository
from ..infrastructure.repositories.dynamodb_version_repository import DynamoDBVersionRepository
from ..dto.request import CreateKBRequest, UpdateKBRequest
from ..dto.response import (
    KBResponse, KBListResponse, KBVersionResponse,
    KBVersionListResponse, KBFilesResponse, KBFileResponse,
    VersionChangesResponse
)
from .mapper import KBMapper
from ..exception.exceptions import KBNotFoundException
from ..infrastructure.clients import BedrockKBClient, S3FileClient
from ..domain.value_objects import KBStatus
from ..domain.value_objects.knowledge_base_file import KnowledgeBaseFile
from ..domain.value_objects.version_changes import VersionChanges
from ..domain.entities.knowledge_base_version import KnowledgeBaseVersion
from ..domain.value_objects.sync_status import SyncStatus

from app.config import settings
from app.shared.utils.timestamp import now_timestamp


class KBApplicationService:
    """KB Use Cases - 파일 업로드 및 버전 관리"""

    def __init__(
        self,
        kb_repository: KBRepository,
        version_repository: Optional[VersionRepository] = None
    ):
        self.kb_repository = kb_repository
        self.version_repository = version_repository or DynamoDBVersionRepository()
        self.mapper = KBMapper()
        self.bedrock_client = BedrockKBClient()
        self.s3_client = S3FileClient()

    async def create_kb_with_files(
        self,
        name: str,
        description: str,
        team_tags: List[str],
        files: List[UploadFile],
        user_id: str
    ) -> KBResponse:
        """파일 업로드를 통한 KB 생성 (SQS + Lambda 방식)"""

        # 1. KB 메타정보 생성 (CREATING 상태)
        kb = self.mapper.to_entity_for_creation(name, description, team_tags, user_id)
        kb.status = KBStatus.CREATING
        kb_id = kb.id.value

        print(f"📦 Creating KB: {name} with {len(files)} files")
        print(f"🔍 S3_KB_FILES_BUCKET from settings: '{settings.S3_KB_FILES_BUCKET}'")

        try:
            # 2. S3에 파일 업로드 (먼저 수행)
            s3_bucket = settings.S3_KB_FILES_BUCKET
            s3_prefix = f"kb-{kb_id}/v1/"  # 버전 포함
            kb_files = []

            for file in files:
                s3_key = f"{s3_prefix}{file.filename}"
                s3_url, checksum = self.s3_client.upload_file(file, s3_key, s3_bucket)

                kb_file = KnowledgeBaseFile(
                    name=file.filename,
                    size=file.size,
                    content_type=file.content_type,
                    s3_key=s3_key,
                    checksum=checksum,
                    uploaded_at=now_timestamp(),
                    status="uploaded"
                )
                kb_files.append(kb_file)

            print(f"✅ Uploaded {len(kb_files)} files to S3")

            # 3. 초기 버전 생성 및 저장
            kb.increment_version()

            version = KnowledgeBaseVersion(
                kb_id=kb_id,
                version=1,
                files=kb_files,
                change_log="Initial creation",
                changes=VersionChanges(
                    added=[f.name for f in kb_files],
                    deleted=[],
                    modified=[]
                ),
                sync_status=SyncStatus.UPLOADED,
                created_by=user_id,
                created_at=now_timestamp()
            )
            await self.version_repository.save(version)
            print(f"✅ KB 버전 저장 완료: {kb_id}, 버전: 1, 파일 수: {len(kb_files)}")

            # 4. KB 메타정보 저장 (모든 업로드 성공 후)
            await self.kb_repository.save(kb)
            print(f"✅ KB 메타정보 저장 완료: {kb_id}")

            # 5. SQS에 메시지 전송 (Lambda가 처리)
            import boto3
            import json

            # boto3 Session을 사용하여 AWS_PROFILE 적용
            if settings.AWS_PROFILE:
                session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
                sqs = session.client('sqs')
            else:
                sqs = boto3.client('sqs', region_name=settings.AWS_REGION)

            queue_url = settings.SQS_KB_CREATION_QUEUE_URL

            message = {
                'kb_id': kb_id,
                'kb_name': name,
                'description': description,
                's3_bucket': s3_bucket,
                's3_prefix': s3_prefix,
                'opensearch_endpoint': settings.OPENSEARCH_COLLECTION_ENDPOINT,
                'opensearch_collection_arn': settings.OPENSEARCH_COLLECTION_ARN,
                'embedding_model_arn': settings.EMBEDDING_MODEL_ARN,
                'bedrock_kb_role_arn': settings.BEDROCK_KB_ROLE_ARN
            }

            try:
                sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(message)
                )
                print(f"✅ SQS 메시지 전송 완료: {kb_id}")
            except Exception as e:
                print(f"❌ SQS 메시지 전송 실패: {e}")
                # SQS 실패 시 KB 상태를 FAILED로 변경
                kb.status = KBStatus.FAILED
                await self.kb_repository.save(kb)
                raise

            # 6. 즉시 응답 반환 (CREATING 상태)
            return self.mapper.to_response(kb)

        except Exception as e:
            # 에러 발생 시 생성된 리소스 정리
            print(f"❌ KB 생성 중 에러 발생: {e}")
            print(f"❌ 에러 상세: {traceback.format_exc()}")

            # 이미 저장된 KB 메타정보가 있으면 삭제
            try:
                existing_kb = await self.kb_repository.find_by_id(kb_id)
                if existing_kb:
                    await self.kb_repository.delete(kb_id)
                    print(f"✅ 실패한 KB 메타정보 삭제: {kb_id}")
            except:
                pass  # 삭제 실패는 무시

            raise
    
    
    async def get_kb(self, kb_id: str) -> KBResponse:
        """KB 메타정보 조회"""
        kb = await self.kb_repository.find_by_id(kb_id)
        if not kb:
            raise KBNotFoundException(kb_id)

        response = self.mapper.to_response(kb)

        try:
            # 최신 버전 정보 추가
            latest_version = await self.version_repository.find_latest_by_kb_id(kb_id)
            if latest_version:
                response.file_count = len(latest_version.files)
                response.sync_status = latest_version.sync_status.value
                response.sync_started_at = latest_version.sync_started_at
                response.sync_completed_at = latest_version.sync_completed_at
        except Exception as e:
            # 버전 정보가 없거나 에러 발생 시 무시
            print(f"Warning: Failed to fetch version for KB {kb_id}: {e}")
            pass

        return response

    async def list_kbs(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str = None,
        status: str = None,
        team_tags: List[str] = None
    ) -> KBListResponse:
        """KB 목록 조회 (검색, 상태, 팀 태그 필터 지원) - 성능 최적화 버전"""

        # 1. Repository에서 status 필터링 (GSI 활용)
        kbs, total = await self.kb_repository.find_all(page=1, page_size=1000, status=status)

        # 2. 나머지 필터링은 메모리에서 처리 (검색, 팀 태그)
        filtered_kbs = kbs

        if search:
            search_lower = search.lower()
            filtered_kbs = [
                kb for kb in filtered_kbs
                if search_lower in kb.name.lower() or
                   (kb.description and search_lower in kb.description.lower())
            ]

        if team_tags:
            filtered_kbs = [
                kb for kb in filtered_kbs
                if any(tag in kb.team_tags for tag in team_tags)
            ]

        # 3. 페이지네이션 적용
        total_filtered = len(filtered_kbs)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_kbs = filtered_kbs[start:end]

        # 4. 배치로 버전 정보 조회 (N+1 문제 해결)
        kb_ids = [kb.id.value for kb in paginated_kbs]
        versions_map = await self.version_repository.batch_find_latest_by_kb_ids(kb_ids)

        # 5. 응답 생성
        items = []
        for kb in paginated_kbs:
            response = self.mapper.to_response(kb)

            # 배치 조회 결과에서 버전 정보 가져오기
            latest_version = versions_map.get(kb.id.value)
            if latest_version:
                response.file_count = len(latest_version.files)
                response.sync_status = latest_version.sync_status.value
                response.sync_started_at = latest_version.sync_started_at
                response.sync_completed_at = latest_version.sync_completed_at

            items.append(response)

        return KBListResponse(
            items=items,
            total=total_filtered,
            page=page,
            page_size=page_size
        )

    async def update_kb(self, kb_id: str, request: UpdateKBRequest, user_id: str) -> KBResponse:
        """KB 메타정보 수정"""
        kb = await self.kb_repository.find_by_id(kb_id)
        if not kb:
            raise KBNotFoundException(kb_id)

        kb.update(
            name=request.name,
            description=request.description,
            team_tags=request.team_tags,
            user_id=user_id
        )

        updated_kb = await self.kb_repository.save(kb)
        return self.mapper.to_response(updated_kb)

    async def change_kb_status(self, kb_id: str, enabled: bool) -> KBResponse:
        """KB 상태 변경 (enabled/disabled)"""
        kb = await self.kb_repository.find_by_id(kb_id)
        if not kb:
            raise KBNotFoundException(kb_id)

        if enabled:
            kb.enable()
        else:
            kb.disable()

        updated_kb = await self.kb_repository.save(kb)
        return self.mapper.to_response(updated_kb)

    async def get_kb_versions(self, kb_id: str) -> KBVersionListResponse:
        """KB 버전 목록 조회"""
        kb = await self.kb_repository.find_by_id(kb_id)
        if not kb:
            raise KBNotFoundException(kb_id)

        versions = await self.version_repository.find_by_kb_id(kb_id)

        version_responses = []
        for version in versions:
            version_response = KBVersionResponse(
                kb_id=version.kb_id,
                version=version.version,
                files=[
                    KBFileResponse(
                        name=f.name,
                        size=f.size,
                        content_type=f.content_type,
                        s3_key=f.s3_key,
                        checksum=f.checksum,
                        uploaded_at=f.uploaded_at
                    )
                    for f in version.files
                ],
                change_log=version.change_log,
                changes=VersionChangesResponse(
                    added=version.changes.added,
                    deleted=version.changes.deleted,
                    modified=version.changes.modified
                ),
                sync_status=version.sync_status.value,
                sync_job_id=version.sync_job_id,
                sync_started_at=version.sync_started_at,
                sync_completed_at=version.sync_completed_at,
                created_at=version.created_at,
                created_by=version.created_by
            )
            version_responses.append(version_response)

        return KBVersionListResponse(
            kb_id=kb_id,
            current_version=kb.current_version,
            versions=version_responses,
            total=len(version_responses)
        )

    async def get_kb_files(self, kb_id: str) -> KBFilesResponse:
        """KB 현재 파일 목록 조회 (S3 + DynamoDB)"""
        kb = await self.kb_repository.find_by_id(kb_id)
        if not kb:
            raise KBNotFoundException(kb_id)

        # 1. DynamoDB에서 버전 정보 조회 시도
        try:
            latest_version = await self.version_repository.find_latest_by_kb_id(kb_id)
            if latest_version and latest_version.files:
                files = [
                    KBFileResponse(
                        name=f.name,
                        size=f.size,
                        content_type=f.content_type,
                        s3_key=f.s3_key,
                        checksum=f.checksum,
                        uploaded_at=f.uploaded_at,
                        status=getattr(f, 'status', 'uploaded')
                    )
                    for f in latest_version.files
                ]
                
                return KBFilesResponse(
                    kb_id=kb_id,
                    current_version=kb.current_version,
                    files=files,
                    total_size=sum(f.size for f in latest_version.files),
                    sync_status=latest_version.sync_status.value if latest_version.sync_status else "unknown"
                )
        except Exception as e:
            print(f"⚠️ DynamoDB 조회 실패, S3에서 직접 조회: {e}")
        
        # 2. DynamoDB에 없으면 S3에서 직접 조회 (현재 버전만)
        s3_bucket = settings.S3_KB_FILES_BUCKET
        s3_prefix = f"kb-{kb_id}/v{kb.current_version}/"

        try:
            import boto3
            # boto3 Session을 사용하여 AWS_PROFILE 적용
            if settings.AWS_PROFILE:
                session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
                s3_client = session.client('s3')
            else:
                s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
            response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_prefix)
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # 폴더는 제외
                    if obj['Key'].endswith('/'):
                        continue
                    
                    filename = obj['Key'].split('/')[-1]
                    files.append(KBFileResponse(
                        name=filename,
                        size=obj['Size'],
                        content_type='application/octet-stream',
                        s3_key=obj['Key'],
                        checksum='',
                        uploaded_at=int(obj['LastModified'].timestamp()),
                        status='uploaded'
                    ))
            
            return KBFilesResponse(
                kb_id=kb_id,
                current_version=kb.current_version,
                files=files,
                total_size=sum(f.size for f in files),
                sync_status='uploaded'
            )
        except Exception as e:
            print(f"❌ S3 조회 실패: {e}")
            return KBFilesResponse(
                kb_id=kb_id,
                current_version=kb.current_version,
                files=[],
                total_size=0,
                sync_status='unknown'
            )

    async def update_kb_files(
        self,
        kb_id: str,
        new_files: List[UploadFile],
        deleted_file_names: List[str],
        user_id: str
    ) -> KBResponse:
        """KB 파일 업데이트 (추가/삭제) - SQS + Lambda 방식"""
        kb = await self.kb_repository.find_by_id(kb_id)
        if not kb:
            raise KBNotFoundException(kb_id)

        # 현재 버전 가져오기
        latest_version = await self.version_repository.find_latest_by_kb_id(kb_id)
        if not latest_version:
            current_files = []
        else:
            current_files = list(latest_version.files)

        # 삭제할 파일 제거
        remaining_files = [
            f for f in current_files
            if f.name not in deleted_file_names
        ]

        # 새 버전 번호 (Decimal을 int로 변환)
        new_version = int(kb.current_version + 1)

        # 새 파일 업로드
        new_kb_files = []
        new_file_names = [file.filename for file in new_files]
        s3_bucket = settings.S3_KB_FILES_BUCKET
        s3_prefix = f"kb-{kb_id}/v{new_version}/"  # 버전별 폴더

        # 새로 업로드할 파일과 같은 이름의 기존 파일은 제거 (덮어쓰기 방지)
        remaining_files = [
            f for f in remaining_files
            if f.name not in new_file_names
        ]

        for file in new_files:
            s3_key = f"{s3_prefix}{file.filename}"
            s3_url, checksum = self.s3_client.upload_file(file, s3_key, s3_bucket)

            kb_file = KnowledgeBaseFile(
                name=file.filename,
                size=file.size,
                content_type=file.content_type,
                s3_key=s3_key,
                checksum=checksum,
                uploaded_at=now_timestamp(),
                status="uploaded"
            )
            new_kb_files.append(kb_file)

        # 모든 파일 합치기 (이제 중복 없음)
        all_files = remaining_files + new_kb_files

        # 변경사항 계산
        added_names = [f.name for f in new_kb_files]
        deleted_names = deleted_file_names

        # 새 버전 생성 및 저장
        kb.increment_version()
        new_version_entity = KnowledgeBaseVersion(
            kb_id=kb_id,
            version=new_version,
            files=all_files,
            change_log=f"Added {len(added_names)} files, deleted {len(deleted_names)} files",
            changes=VersionChanges(
                added=added_names,
                deleted=deleted_names,
                modified=[]
            ),
            sync_status=SyncStatus.UPLOADED,
            created_by=user_id,
            created_at=now_timestamp()
        )
        await self.version_repository.save(new_version_entity)
        print(f"✅ KB 버전 저장 완료: {kb_id}, 버전: {new_version}, 파일 수: {len(all_files)}")

        # KB 메타정보 저장
        await self.kb_repository.save(kb)
        print(f"✅ KB 메타정보 저장 완료: {kb_id}")

        # SQS에 파일 업데이트 메시지 전송 (Lambda가 Data Source 업데이트 + Ingestion Job 처리)
        import boto3
        import json

        # boto3 Session을 사용하여 AWS_PROFILE 적용
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
            sqs = session.client('sqs')
        else:
            sqs = boto3.client('sqs', region_name=settings.AWS_REGION)

        queue_url = settings.SQS_KB_CREATION_QUEUE_URL

        message = {
            'kb_id': kb_id,
            'action': 'update_files',  # 파일 업데이트 액션
            's3_bucket': s3_bucket,
            's3_prefix': s3_prefix,  # 새 버전 폴더
            'version': new_version
        }

        try:
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
            print(f"✅ SQS 메시지 전송 완료 (파일 업데이트): {kb_id}, 버전: {new_version}")
        except Exception as e:
            print(f"❌ SQS 메시지 전송 실패: {e}")
            raise

        print(f"✅ KB 파일 업로드 완료: {kb_id}, 버전: {new_version}, 파일 수: {len(all_files)}")
        print(f"   - 추가된 파일: {added_names}")
        print(f"   - 삭제된 파일: {deleted_names}")
        print(f"   - Sync 상태: {new_version_entity.sync_status.value}")

        # 즉시 응답 반환 (UPLOADED 상태)
        response = self.mapper.to_response(kb)
        response.file_count = len(all_files)
        response.sync_status = new_version_entity.sync_status.value

        return response

    async def get_kb_stats(self) -> dict:
        """KB 통계 조회 (Dashboard용)

        Returns:
            dict: {
                'total': int - 전체 KB 수,
                'enabled': int - 활성화된 KB 수,
                'totalDocuments': int - 전체 문서(파일) 수
            }
        """
        # 전체 KB 조회
        all_kbs, total_count = await self.kb_repository.find_all(page=1, page_size=10000)

        # enabled 상태 KB 수
        enabled_count = sum(1 for kb in all_kbs if kb.status.value == 'enabled')

        # 전체 문서(파일) 수 계산 - 각 KB의 최신 버전에서 파일 수 합산
        total_documents = 0
        kb_ids = [kb.id.value for kb in all_kbs]
        if kb_ids:
            try:
                versions_map = await self.version_repository.batch_find_latest_by_kb_ids(kb_ids)
                for kb_id, version in versions_map.items():
                    if version and version.files:
                        total_documents += len(version.files)
            except Exception as e:
                print(f"⚠️ Failed to fetch document counts: {e}")

        return {
            "total": total_count,
            "enabled": enabled_count,
            "totalDocuments": total_documents
        }

