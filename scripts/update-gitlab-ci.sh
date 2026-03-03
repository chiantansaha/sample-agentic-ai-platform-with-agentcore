#!/bin/bash
# =============================================================================
# GitLab CI/CD 설정 업데이트 스크립트
# Terraform output을 기반으로 .gitlab-ci.yml 파일을 업데이트합니다.
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GITLAB_CI_FILE="$PROJECT_ROOT/.gitlab-ci.yml"

# Usage
usage() {
    echo "Usage: $0 -p <aws_profile> -e <environment> [-s <state_file>]"
    echo ""
    echo "Options:"
    echo "  -p    AWS Profile name (required)"
    echo "  -e    Environment: dev or prod (required)"
    echo "  -s    Terraform state file path (optional)"
    echo ""
    echo "Example:"
    echo "  $0 -p my-profile -e dev"
    echo "  $0 -p my-profile -e dev -s terraform.tfstate.123456789012.us-west-2"
    exit 1
}

# Parse arguments
while getopts "p:e:s:h" opt; do
    case $opt in
        p) AWS_PROFILE="$OPTARG" ;;
        e) ENVIRONMENT="$OPTARG" ;;
        s) STATE_FILE="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Validate required arguments
if [ -z "$AWS_PROFILE" ] || [ -z "$ENVIRONMENT" ]; then
    echo -e "${RED}Error: AWS Profile and Environment are required${NC}"
    usage
fi

# Set terraform directory
TERRAFORM_DIR="$PROJECT_ROOT/infra/environments/$ENVIRONMENT"

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo -e "${RED}Error: Terraform directory not found: $TERRAFORM_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  GitLab CI/CD Configuration Updater${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "AWS Profile:  ${YELLOW}$AWS_PROFILE${NC}"
echo -e "Environment:  ${YELLOW}$ENVIRONMENT${NC}"
echo -e "Terraform Dir: ${YELLOW}$TERRAFORM_DIR${NC}"
echo ""

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Build state option
STATE_OPT=""
if [ -n "$STATE_FILE" ]; then
    STATE_OPT="-state=$STATE_FILE"
    echo -e "State File:   ${YELLOW}$STATE_FILE${NC}"
fi

# Get terraform outputs
echo -e "${YELLOW}Fetching Terraform outputs...${NC}"

AWS_ACCOUNT_ID=$(AWS_PROFILE=$AWS_PROFILE terraform output $STATE_OPT -raw aws_account_id 2>/dev/null || echo "")
AWS_REGION=$(AWS_PROFILE=$AWS_PROFILE terraform output $STATE_OPT -raw aws_region 2>/dev/null || echo "")
PROJECT_NAME=$(AWS_PROFILE=$AWS_PROFILE terraform output $STATE_OPT -raw project_name 2>/dev/null || echo "")
BASE_PROJECT_NAME=$(AWS_PROFILE=$AWS_PROFILE terraform output $STATE_OPT -raw base_project_name 2>/dev/null || echo "")

if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ] || [ -z "$PROJECT_NAME" ]; then
    echo -e "${RED}Error: Failed to get Terraform outputs${NC}"
    echo "Make sure terraform apply has been run and outputs are available."
    echo ""
    echo "Required outputs: aws_account_id, aws_region, project_name, base_project_name"
    exit 1
fi

# If base_project_name is not available, derive it from project_name (fallback)
if [ -z "$BASE_PROJECT_NAME" ]; then
    BASE_PROJECT_NAME=$(echo "$PROJECT_NAME" | sed 's/-dev$//' | sed 's/-prod$//')
    echo -e "${YELLOW}Warning: base_project_name not found in outputs, derived from project_name: $BASE_PROJECT_NAME${NC}"
fi

echo ""
echo -e "AWS Account ID:     ${GREEN}$AWS_ACCOUNT_ID${NC}"
echo -e "AWS Region:         ${GREEN}$AWS_REGION${NC}"
echo -e "Base Project Name:  ${GREEN}$BASE_PROJECT_NAME${NC}"
echo -e "Project Name:       ${GREEN}$PROJECT_NAME${NC}"
echo ""

# Backup original file
cp "$GITLAB_CI_FILE" "$GITLAB_CI_FILE.backup"
echo -e "${YELLOW}Backup created: .gitlab-ci.yml.backup${NC}"

# Update .gitlab-ci.yml
echo -e "${YELLOW}Updating .gitlab-ci.yml...${NC}"

# Update AWS_DEFAULT_REGION
sed -i.tmp "s/AWS_DEFAULT_REGION:.*/AWS_DEFAULT_REGION: $AWS_REGION/" "$GITLAB_CI_FILE"

# Update ECR_REGISTRY
sed -i.tmp "s|ECR_REGISTRY:.*|ECR_REGISTRY: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com|" "$GITLAB_CI_FILE"

# Update BASE_PROJECT_NAME (new pattern - CI/CD will generate PROJECT_NAME dynamically)
sed -i.tmp "s/BASE_PROJECT_NAME:.*/BASE_PROJECT_NAME: $BASE_PROJECT_NAME/" "$GITLAB_CI_FILE"

# Clean up temp files
rm -f "$GITLAB_CI_FILE.tmp"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Update Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Updated values in .gitlab-ci.yml:"
echo -e "  AWS_DEFAULT_REGION:  ${GREEN}$AWS_REGION${NC}"
echo -e "  ECR_REGISTRY:        ${GREEN}$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com${NC}"
echo -e "  BASE_PROJECT_NAME:   ${GREEN}$BASE_PROJECT_NAME${NC}"
echo ""
echo -e "${YELLOW}CI/CD will generate PROJECT_NAME dynamically:${NC}"
echo -e "  main branch:     ${GREEN}${BASE_PROJECT_NAME}-dev${NC}"
echo -e "  release/* branch: ${GREEN}${BASE_PROJECT_NAME}-prod${NC}"
echo ""
echo -e "${YELLOW}Note: You also need to set the following GitLab CI/CD variables:${NC}"
echo "  - AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
echo "  - AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY or OIDC)"
echo ""
echo -e "${YELLOW}To revert changes:${NC}"
echo "  cp .gitlab-ci.yml.backup .gitlab-ci.yml"
