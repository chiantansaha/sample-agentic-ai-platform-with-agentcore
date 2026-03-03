"""Dependency Bundler - ARM64 의존성 다운로드 및 번들링

AgentCore Runtime은 ARM64 환경에서 실행되므로,
의존성을 ARM64 호환 wheel로 다운로드하고 번들링합니다.
"""
import os
import io
import shutil
import logging
import tempfile
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 기본 의존성 목록 (AgentCore Runtime에 필요)
BASE_DEPENDENCIES = [
    "bedrock-agentcore>=1.0.0",
    "boto3>=1.34.0",
    # OpenTelemetry SDK (provides contextvars_context entry point required by opentelemetry-api)
    "opentelemetry-sdk>=1.20.0",
    # AWS Distro for OpenTelemetry (required for Strands in AgentCore Runtime)
    # See: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html
    "aws-opentelemetry-distro>=0.10.0",
]

# Strands Agent 의존성 (복잡한 Agent용)
STRANDS_DEPENDENCIES = [
    "strands-agents>=0.1.0",
]


class DependencyBundler:
    """의존성 번들러

    ARM64 호환 Python 패키지를 다운로드하고 캐싱합니다.
    """

    def __init__(self, cache_dir: str = None):
        """
        Args:
            cache_dir: 의존성 캐시 디렉토리 (기본값: /tmp/agentcore-deps)
        """
        self.cache_dir = Path(cache_dir or "/tmp/agentcore-deps")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_dependencies(
        self,
        dependencies: list[str] = None,
        include_strands: bool = True,
        force_refresh: bool = False
    ) -> Path:
        """ARM64 의존성 다운로드

        Args:
            dependencies: 추가 의존성 목록
            include_strands: Strands Agent 포함 여부
            force_refresh: 캐시 무시하고 다시 다운로드

        Returns:
            다운로드된 패키지 디렉토리 경로
        """
        # 의존성 목록 준비
        all_deps = list(BASE_DEPENDENCIES)
        if include_strands:
            all_deps.extend(STRANDS_DEPENDENCIES)
        if dependencies:
            all_deps.extend(dependencies)

        # 캐시 키 생성 (의존성 목록 기반)
        cache_key = self._generate_cache_key(all_deps)
        packages_dir = self.cache_dir / cache_key / "packages"

        # 캐시 확인
        if packages_dir.exists() and not force_refresh:
            logger.info(f"Using cached dependencies from {packages_dir}")
            return packages_dir

        # 새로 다운로드
        logger.info(f"Downloading ARM64 dependencies: {all_deps}")
        packages_dir.parent.mkdir(parents=True, exist_ok=True)

        # 임시 디렉토리에 다운로드
        temp_dir = packages_dir.parent / "temp_packages"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)

        try:
            self._download_with_uv(all_deps, temp_dir)

            # 성공하면 캐시로 이동
            if packages_dir.exists():
                shutil.rmtree(packages_dir)
            shutil.move(str(temp_dir), str(packages_dir))

            logger.info(f"Downloaded dependencies to {packages_dir}")
            return packages_dir

        except Exception as e:
            logger.error(f"Failed to download dependencies: {e}")
            # Fallback: pip 사용
            try:
                self._download_with_pip(all_deps, temp_dir)
                if packages_dir.exists():
                    shutil.rmtree(packages_dir)
                shutil.move(str(temp_dir), str(packages_dir))
                return packages_dir
            except Exception as e2:
                logger.error(f"Pip fallback also failed: {e2}")
                raise RuntimeError(f"Failed to download dependencies: {e}") from e

    def _download_with_uv(self, dependencies: list[str], target_dir: Path) -> None:
        """uv를 사용하여 ARM64 의존성 다운로드"""
        cmd = [
            "uv", "pip", "install",
            "--python-platform", "aarch64-manylinux2014",
            "--python-version", "3.13",
            "--target", str(target_dir),
            "--no-compile",
        ]
        cmd.extend(dependencies)

        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )

        if result.returncode != 0:
            logger.error(f"uv pip install failed: {result.stderr}")
            raise RuntimeError(f"uv pip install failed: {result.stderr}")

        logger.info(f"uv pip install succeeded")

    def _download_with_pip(self, dependencies: list[str], target_dir: Path) -> None:
        """pip를 사용하여 의존성 다운로드 (Fallback)

        Note: pip는 cross-platform 다운로드를 지원하지 않으므로,
        현재 플랫폼의 패키지가 다운로드됩니다.
        ARM64 환경에서 실행하거나, 호환 가능한 pure Python 패키지만 사용하세요.
        """
        cmd = [
            "pip", "install",
            "--target", str(target_dir),
            "--no-compile",
            "--only-binary", ":all:",  # 바이너리 wheel만 사용
        ]
        cmd.extend(dependencies)

        logger.info(f"Running pip fallback: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            logger.error(f"pip install failed: {result.stderr}")
            raise RuntimeError(f"pip install failed: {result.stderr}")

    def create_bundle(
        self,
        source_files: dict[str, str],
        packages_dir: Path = None,
        include_strands: bool = True
    ) -> bytes:
        """소스 파일과 의존성을 번들링하여 ZIP 생성

        Args:
            source_files: {filename: content} 형태의 소스 파일
            packages_dir: 패키지 디렉토리 (없으면 다운로드)
            include_strands: Strands Agent 포함 여부

        Returns:
            ZIP 파일 바이트
        """
        # 의존성 다운로드 (필요시)
        if packages_dir is None:
            packages_dir = self.download_dependencies(include_strands=include_strands)

        # ZIP 파일 생성
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 소스 파일 추가
            for filename, content in source_files.items():
                # requirements.txt는 제외 (이미 번들링됨)
                if filename == "requirements.txt":
                    continue
                zf.writestr(filename, content)
                logger.debug(f"Added source file: {filename}")

            # 패키지 추가
            package_count = 0
            for root, dirs, files in os.walk(packages_dir):
                # 불필요한 디렉토리 제외
                dirs[:] = [d for d in dirs if not d.startswith('__pycache__')]

                for file in files:
                    # 불필요한 파일 제외
                    if file.endswith(('.pyc', '.pyo', '.dist-info', '.egg-info')):
                        continue

                    file_path = Path(root) / file
                    arcname = file_path.relative_to(packages_dir)

                    # 일부 메타데이터 디렉토리 제외
                    if '.dist-info' in str(arcname) or '.egg-info' in str(arcname):
                        continue

                    zf.write(file_path, arcname)
                    package_count += 1

            logger.info(f"Added {package_count} package files to bundle")

        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()

        logger.info(f"Created bundle: {len(zip_bytes) / 1024 / 1024:.2f} MB")
        return zip_bytes

    def _generate_cache_key(self, dependencies: list[str]) -> str:
        """의존성 목록 기반 캐시 키 생성"""
        import hashlib
        deps_str = ",".join(sorted(dependencies))
        return hashlib.md5(deps_str.encode(), usedforsecurity=False).hexdigest()[:12]

    def clear_cache(self) -> None:
        """캐시 삭제"""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            logger.info(f"Cleared cache: {self.cache_dir}")
