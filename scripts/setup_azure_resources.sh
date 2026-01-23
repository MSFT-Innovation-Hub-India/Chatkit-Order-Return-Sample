#!/bin/bash
# =============================================================================
# Azure Resource Setup Script for Order Returns Sample
# =============================================================================
# 
# This script creates all Azure resources needed to run the Order Returns sample
# in a new subscription. Run this before running populate_cosmosdb.py.
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Appropriate permissions to create resources
#
# Usage:
#   chmod +x scripts/setup_azure_resources.sh
#   ./scripts/setup_azure_resources.sh --resource-group "my-rg" --location "eastus"
#
# =============================================================================

set -e

# Default values
LOCATION="eastus"
DATABASE_NAME="db001"
COSMOS_ACCOUNT_NAME=""
SKIP_COSMOS_ACCOUNT=false
SKIP_RBAC=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -l|--location)
            LOCATION="$2"
            shift 2
            ;;
        -a|--cosmos-account)
            COSMOS_ACCOUNT_NAME="$2"
            shift 2
            ;;
        -d|--database)
            DATABASE_NAME="$2"
            shift 2
            ;;
        --skip-cosmos-account)
            SKIP_COSMOS_ACCOUNT=true
            shift
            ;;
        --skip-rbac)
            SKIP_RBAC=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 --resource-group <name> [options]"
            echo ""
            echo "Options:"
            echo "  -g, --resource-group   Resource group name (required)"
            echo "  -l, --location         Azure region (default: eastus)"
            echo "  -a, --cosmos-account   Cosmos DB account name (auto-generated if not provided)"
            echo "  -d, --database         Database name (default: db001)"
            echo "  --skip-cosmos-account  Skip Cosmos DB account creation"
            echo "  --skip-rbac            Skip RBAC configuration"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$RESOURCE_GROUP" ]; then
    echo -e "${RED}ERROR: --resource-group is required${NC}"
    exit 1
fi

# Generate a unique name if not provided
if [ -z "$COSMOS_ACCOUNT_NAME" ]; then
    SUFFIX=$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
    COSMOS_ACCOUNT_NAME="cosmos-orderreturns-$SUFFIX"
fi

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}Order Returns - Azure Resource Setup${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Resource Group:    $RESOURCE_GROUP"
echo "  Location:          $LOCATION"
echo "  Cosmos Account:    $COSMOS_ACCOUNT_NAME"
echo "  Database:          $DATABASE_NAME"
echo ""

# =============================================================================
# 1. Create Resource Group
# =============================================================================

echo -e "${GREEN}Step 1: Creating resource group...${NC}"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
echo -e "${GRAY}  Resource group '$RESOURCE_GROUP' created/verified${NC}"

# =============================================================================
# 2. Create Cosmos DB Account (Serverless)
# =============================================================================

if [ "$SKIP_COSMOS_ACCOUNT" = false ]; then
    echo ""
    echo -e "${GREEN}Step 2: Creating Cosmos DB account (serverless)...${NC}"
    echo -e "${GRAY}  This may take 5-10 minutes...${NC}"
    
    az cosmosdb create \
        --name "$COSMOS_ACCOUNT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --locations regionName="$LOCATION" \
        --capabilities EnableServerless \
        --default-consistency-level Session \
        --output none
    
    echo -e "${GRAY}  Cosmos DB account '$COSMOS_ACCOUNT_NAME' created${NC}"
else
    echo ""
    echo -e "${YELLOW}Step 2: Skipping Cosmos DB account creation (--skip-cosmos-account)${NC}"
fi

# =============================================================================
# 3. Create Database
# =============================================================================

echo ""
echo -e "${GREEN}Step 3: Creating database...${NC}"

az cosmosdb sql database create \
    --account-name "$COSMOS_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DATABASE_NAME" \
    --output none

echo -e "${GRAY}  Database '$DATABASE_NAME' created${NC}"

# =============================================================================
# 4. Create Retail Data Containers
# =============================================================================

echo ""
echo -e "${GREEN}Step 4: Creating retail data containers...${NC}"

declare -A RETAIL_CONTAINERS=(
    ["Retail_Products"]="/id"
    ["Retail_Customers"]="/id"
    ["Retail_Orders"]="/id"
    ["Retail_ReturnReasons"]="/code"
    ["Retail_ResolutionOptions"]="/code"
    ["Retail_ShippingOptions"]="/code"
    ["Retail_DiscountOffers"]="/code"
    ["Retail_Returns"]="/id"
    ["Retail_CustomerNotes"]="/customer_id"
    ["Retail_DemoScenarios"]="/name"
)

for container in "${!RETAIL_CONTAINERS[@]}"; do
    echo -e "${GRAY}  Creating $container...${NC}"
    az cosmosdb sql container create \
        --account-name "$COSMOS_ACCOUNT_NAME" \
        --database-name "$DATABASE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --name "$container" \
        --partition-key-path "${RETAIL_CONTAINERS[$container]}" \
        --output none 2>/dev/null || echo -e "${YELLOW}    Container may already exist, continuing...${NC}"
done

echo -e "${GRAY}  10 retail containers created${NC}"

# =============================================================================
# 5. Create ChatKit Containers
# =============================================================================

echo ""
echo -e "${GREEN}Step 5: Creating ChatKit containers...${NC}"

declare -A CHATKIT_CONTAINERS=(
    ["ChatKit_Threads"]="/id"
    ["ChatKit_Items"]="/thread_id"
    ["ChatKit_Feedback"]="/thread_id"
)

for container in "${!CHATKIT_CONTAINERS[@]}"; do
    echo -e "${GRAY}  Creating $container...${NC}"
    az cosmosdb sql container create \
        --account-name "$COSMOS_ACCOUNT_NAME" \
        --database-name "$DATABASE_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --name "$container" \
        --partition-key-path "${CHATKIT_CONTAINERS[$container]}" \
        --output none 2>/dev/null || echo -e "${YELLOW}    Container may already exist, continuing...${NC}"
done

echo -e "${GRAY}  3 ChatKit containers created${NC}"

# =============================================================================
# 6. Configure RBAC (optional)
# =============================================================================

if [ "$SKIP_RBAC" = false ]; then
    echo ""
    echo -e "${GREEN}Step 6: Configuring RBAC for current user...${NC}"
    
    # Get current user's object ID
    CURRENT_USER=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")
    
    if [ -n "$CURRENT_USER" ]; then
        echo -e "${GRAY}  Assigning 'Cosmos DB Built-in Data Contributor' role...${NC}"
        az cosmosdb sql role assignment create \
            --account-name "$COSMOS_ACCOUNT_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --role-definition-id "00000000-0000-0000-0000-000000000002" \
            --principal-id "$CURRENT_USER" \
            --scope "/" \
            --output none 2>/dev/null || true
        
        echo -e "${GRAY}  RBAC configured for user $CURRENT_USER${NC}"
    else
        echo -e "${YELLOW}  Could not determine current user, skipping RBAC${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}Step 6: Skipping RBAC configuration (--skip-rbac)${NC}"
fi

# =============================================================================
# Summary
# =============================================================================

ENDPOINT=$(az cosmosdb show \
    --name "$COSMOS_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query documentEndpoint -o tsv)

echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""
echo -e "${YELLOW}Resources Created:${NC}"
echo "  - Cosmos DB Account: $COSMOS_ACCOUNT_NAME"
echo "  - Database: $DATABASE_NAME"
echo "  - Containers: 13 total (10 retail + 3 ChatKit)"
echo ""
echo -e "${YELLOW}Cosmos DB Endpoint:${NC}"
echo "  $ENDPOINT"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Update shared/cosmos_config.py with the new endpoint:"
echo "     COSMOS_ENDPOINT = \"$ENDPOINT\""
echo ""
echo "  2. Populate sample data:"
echo "     python scripts/populate_cosmosdb.py"
echo ""
echo "  3. Configure Azure OpenAI and run the application:"
echo "     python main_retail.py"
echo ""
