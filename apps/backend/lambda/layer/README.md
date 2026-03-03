# Lambda Layer - KB Dependencies

이 디렉토리는 AWS Lambda 함수에서 사용할 Python 의존성 레이어를 관리합니다.

## 📦 포함된 패키지

- `opensearch-py`: OpenSearch 클라이언트
- `requests-aws4auth`: AWS 서명 v4 인증

## 🛠️ 빌드 방법

### Docker 사용 (권장)

Docker가 설치되어 있으면 Lambda 환경과 호환되는 패키지가 빌드됩니다:

```bash
cd apps/backend/lambda/layer
./scripts/build_layer.sh
```

### Docker 없이 빌드

로컬 Python 환경으로 빌드 (MacOS/Windows에서는 Lambda와 호환되지 않을 수 있음):

```bash
pip install -r requirements.txt -t python/
zip -r kb-dependencies-layer.zip python/
```

## 📁 구조

```
layer/
├── requirements.txt          # 의존성 정의
├── scripts/
│   └── build_layer.sh       # 빌드 스크립트
├── .gitignore               # Git 제외 파일
├── README.md                # 이 파일
├── python/                  # 빌드된 패키지 (gitignore)
└── kb-dependencies-layer.zip # 최종 zip (gitignore)
```

## 🚀 Terraform 배포

Terraform 코드에서 다음과 같이 사용:

```hcl
resource "terraform_data" "lambda_layer_build" {
  triggers_replace = {
    requirements = filemd5("${path.module}/../../apps/backend/lambda/layer/requirements.txt")
  }

  provisioner "local-exec" {
    command = "bash ${path.module}/../../apps/backend/lambda/layer/scripts/build_layer.sh"
  }
}

resource "aws_lambda_layer_version" "kb_dependencies" {
  filename            = "${path.module}/../../apps/backend/lambda/layer/kb-dependencies-layer.zip"
  layer_name          = "kb-dependencies"
  compatible_runtimes = ["python3.11"]

  depends_on = [terraform_data.lambda_layer_build]
}
```

## 🔄 의존성 업데이트

1. `requirements.txt` 수정
2. 빌드 스크립트 실행: `./scripts/build_layer.sh`
3. Git에 `requirements.txt`만 커밋

## 📝 주의사항

- `*.zip`과 `python/` 디렉토리는 Git에 포함되지 않음
- Lambda와 호환되려면 Linux 환경에서 빌드해야 함 (Docker 사용 권장)
- 최대 레이어 크기: 50MB (압축), 250MB (압축 해제)
