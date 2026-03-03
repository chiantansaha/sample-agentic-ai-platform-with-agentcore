# 고우선순위 기능 명세 (상 우선순위)

## 1. MCP 관리

### 1.1 MCP 조회
- **1.1.1 MCP 조회**: MCP명, 엔드포인트, 설명, 버전, 툴 개수, Internal/External, Enable/disable
- **1.1.2 MCP 검색**
  - 1.1.2.1 MCP명
  - 1.1.2.2 내부/외부
  - 1.1.2.3 Enabled/Disabled
- **1.1.3 MCP Enable/Disable**
- **1.1.4 MCP 상세 조회**: overview, tool리스트, 버전

### 1.2 외부 MCP 등록
- **1.2.1 MCP명 입력**
- **1.2.2 MCP Description 입력**
- **1.2.3.1 MCP Endpoint 입력**
- **1.2.3.2 인증방식 선택**
  - 1.2.3.2.1 None
  - 1.2.3.2.2 OAuth
  - 1.2.3.2.3 API Key
- **1.2.4 생성**: 외부Gateway에 Target으로 추가

### 1.3 내부 MCP 등록
- **1.3.1 MCP명 입력**
- **1.3.2 MCP Description 입력**
- **1.3.3 컨테이너 이미지 업로드**
- **1.3.4 등록**: Runtime배포

### 1.4 내부 MCP 생성
- **1.4.1 MCP명 입력**
- **1.4.2 MCP Description 입력**
- **1.4.1.1.1.1 API 정보 입력**: 엔드포인트, 스키마, 인증url
- **1.4.3 생성**: Gateway생성

### 1.5 MCP 수정
- **1.5.1.2 Gateway 버전 업데이트**: aws agentcore gateway 버져닝 정책에 맞춰서
- **1.5.2 MCP Disable**

## 2. KB 관리

### 2.1 KnowledgeBase 조회
- **2.1.1 Knowledgebase 조회**
- **2.1.2 Knowledgebase 검색**
  - 2.1.2.1 Knowledgebase명
  - 2.1.2.3 disabled/enabled

### 2.2 KnowledgeBase 생성
- **2.2.1 KnowledgeBase명 입력**
- **2.2.2 KnowledgeBase Description 입력**
- **2.2.3.1 텍스트파일(.md) 업로드**: 업로드 시 버킷 저장
- **2.2.5 생성**: sync같이해주기, vector store(Opensearch) 저장

### 2.3 KnowledgeBase 수정/삭제
- **2.3.1.1 Datasource 수정**: sync같이 해주기
- **2.3.2.2 KnowledgeBase Disable**

## 3. Agent 관리

### 3.1 Agent 조회
- **3.1.1 Agent 조회**: 노출 컬럼 상세화 필요, 에이전트 상세 페이지 필요(버젼, 오버뷰-연결된 툴, KB등의 메타 정보 보임)
- **3.1.2 Agent 검색**
  - 3.1.2.1 Agent명
  - 3.1.2.2 disabled/enabled

### 3.2 Agent 생성(Playground)
- **3.2.1.1 LLM 모델 선택**: LLM모델은 bedrock 모델만 사용
- **3.2.1.2 Instruction 작성**
- **3.2.1.3 Tool 선택**
  - 3.2.1.3.1 Knowledgebase선택
  - 3.2.1.3.2 외부 MCP 선택
  - 3.2.1.3.3 내부 MCP(Gateway) 선택
- **3.2.1.4.1 저장**: 에이전트의 스펙이 저장
- **3.2.1.6.1 prepare**: runtime에 띄우고
- **3.2.1.6.2 배포 완료되면 채팅하고**

### 3.3 Agent 수정/삭제
- **3.3.1.1 LLM 수정**
- **3.3.1.2 Instruction 수정**
- **3.3.1.3 Tool 수정**
- **3.3.1.4.1 저장**: 에이전트의 스펙이 저장, 버젼 업
- **3.3.2.1 prepare**: runtime에 띄우고
- **3.3.2.2 채팅하기**
- **3.3.3.1 Agent disabled**

## 4. Playground

### 4.1 Playground
- **4.1 Agent**
- **4.2 prepare**
- **4.3 채팅하기**

## 주요 특징
- 모니터링 기능(로그, 성능지표, 알림)은 MVP에서 제외

