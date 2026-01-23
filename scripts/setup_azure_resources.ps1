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
#   .\scripts\setup_azure_resources.ps1 -ResourceGroup "my-rg" -Location "eastus"
#
# =============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$CosmosAccountName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$DatabaseName = "db001",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipCosmosAccount,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipRBAC
)

# Generate a unique name if not provided
if (-not $CosmosAccountName) {
    $suffix = -join ((48..57) + (97..122) | Get-Random -Count 8 | ForEach-Object { [char]$_ })
    $CosmosAccountName = "cosmos-orderreturns-$suffix"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Order Returns - Azure Resource Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group:    $ResourceGroup"
Write-Host "  Location:          $Location"
Write-Host "  Cosmos Account:    $CosmosAccountName"
Write-Host "  Database:          $DatabaseName"
Write-Host ""

# =============================================================================
# 1. Create Resource Group
# =============================================================================

Write-Host "Step 1: Creating resource group..." -ForegroundColor Green
az group create --name $ResourceGroup --location $Location --output none
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create resource group" -ForegroundColor Red
    exit 1
}
Write-Host "  Resource group '$ResourceGroup' created/verified" -ForegroundColor Gray

# =============================================================================
# 2. Create Cosmos DB Account (Serverless)
# =============================================================================

if (-not $SkipCosmosAccount) {
    Write-Host ""
    Write-Host "Step 2: Creating Cosmos DB account (serverless)..." -ForegroundColor Green
    Write-Host "  This may take 5-10 minutes..." -ForegroundColor Gray
    
    az cosmosdb create `
        --name $CosmosAccountName `
        --resource-group $ResourceGroup `
        --locations regionName=$Location `
        --capabilities EnableServerless `
        --default-consistency-level Session `
        --output none
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create Cosmos DB account" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Cosmos DB account '$CosmosAccountName' created" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "Step 2: Skipping Cosmos DB account creation (--SkipCosmosAccount)" -ForegroundColor Yellow
}

# =============================================================================
# 3. Create Database
# =============================================================================

Write-Host ""
Write-Host "Step 3: Creating database..." -ForegroundColor Green

az cosmosdb sql database create `
    --account-name $CosmosAccountName `
    --resource-group $ResourceGroup `
    --name $DatabaseName `
    --output none

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create database" -ForegroundColor Red
    exit 1
}
Write-Host "  Database '$DatabaseName' created" -ForegroundColor Gray

# =============================================================================
# 4. Create Retail Data Containers
# =============================================================================

Write-Host ""
Write-Host "Step 4: Creating retail data containers..." -ForegroundColor Green

$retailContainers = @(
    @{ Name = "Retail_Products"; PartitionKey = "/id" },
    @{ Name = "Retail_Customers"; PartitionKey = "/id" },
    @{ Name = "Retail_Orders"; PartitionKey = "/id" },
    @{ Name = "Retail_ReturnReasons"; PartitionKey = "/code" },
    @{ Name = "Retail_ResolutionOptions"; PartitionKey = "/code" },
    @{ Name = "Retail_ShippingOptions"; PartitionKey = "/code" },
    @{ Name = "Retail_DiscountOffers"; PartitionKey = "/code" },
    @{ Name = "Retail_Returns"; PartitionKey = "/id" },
    @{ Name = "Retail_CustomerNotes"; PartitionKey = "/customer_id" },
    @{ Name = "Retail_DemoScenarios"; PartitionKey = "/name" }
)

foreach ($container in $retailContainers) {
    Write-Host "  Creating $($container.Name)..." -ForegroundColor Gray
    az cosmosdb sql container create `
        --account-name $CosmosAccountName `
        --database-name $DatabaseName `
        --resource-group $ResourceGroup `
        --name $container.Name `
        --partition-key-path $container.PartitionKey `
        --output none 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    Container may already exist, continuing..." -ForegroundColor Yellow
    }
}
Write-Host "  10 retail containers created" -ForegroundColor Gray

# =============================================================================
# 5. Create ChatKit Containers
# =============================================================================

Write-Host ""
Write-Host "Step 5: Creating ChatKit containers..." -ForegroundColor Green

$chatkitContainers = @(
    @{ Name = "ChatKit_Threads"; PartitionKey = "/id" },
    @{ Name = "ChatKit_Items"; PartitionKey = "/thread_id" },
    @{ Name = "ChatKit_Feedback"; PartitionKey = "/thread_id" }
)

foreach ($container in $chatkitContainers) {
    Write-Host "  Creating $($container.Name)..." -ForegroundColor Gray
    az cosmosdb sql container create `
        --account-name $CosmosAccountName `
        --database-name $DatabaseName `
        --resource-group $ResourceGroup `
        --name $container.Name `
        --partition-key-path $container.PartitionKey `
        --output none 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    Container may already exist, continuing..." -ForegroundColor Yellow
    }
}
Write-Host "  3 ChatKit containers created" -ForegroundColor Gray

# =============================================================================
# 6. Configure RBAC (optional)
# =============================================================================

if (-not $SkipRBAC) {
    Write-Host ""
    Write-Host "Step 6: Configuring RBAC for current user..." -ForegroundColor Green
    
    # Get current user's object ID
    $currentUser = az ad signed-in-user show --query id -o tsv 2>$null
    
    if ($currentUser) {
        # Get Cosmos DB account resource ID
        $cosmosResourceId = az cosmosdb show `
            --name $CosmosAccountName `
            --resource-group $ResourceGroup `
            --query id -o tsv
        
        # Assign Cosmos DB Data Contributor role
        Write-Host "  Assigning 'Cosmos DB Built-in Data Contributor' role..." -ForegroundColor Gray
        az cosmosdb sql role assignment create `
            --account-name $CosmosAccountName `
            --resource-group $ResourceGroup `
            --role-definition-id "00000000-0000-0000-0000-000000000002" `
            --principal-id $currentUser `
            --scope "/" `
            --output none 2>$null
        
        Write-Host "  RBAC configured for user $currentUser" -ForegroundColor Gray
    } else {
        Write-Host "  Could not determine current user, skipping RBAC" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Step 6: Skipping RBAC configuration (--SkipRBAC)" -ForegroundColor Yellow
}

# =============================================================================
# Summary
# =============================================================================

$endpoint = az cosmosdb show `
    --name $CosmosAccountName `
    --resource-group $ResourceGroup `
    --query documentEndpoint -o tsv

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Resources Created:" -ForegroundColor Yellow
Write-Host "  - Cosmos DB Account: $CosmosAccountName"
Write-Host "  - Database: $DatabaseName"
Write-Host "  - Containers: 13 total (10 retail + 3 ChatKit)"
Write-Host ""
Write-Host "Cosmos DB Endpoint:" -ForegroundColor Yellow
Write-Host "  $endpoint"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Update shared/cosmos_config.py with the new endpoint:"
Write-Host "     COSMOS_ENDPOINT = `"$endpoint`""
Write-Host ""
Write-Host "  2. Populate sample data:"
Write-Host "     python scripts/populate_cosmosdb.py"
Write-Host ""
Write-Host "  3. Configure Azure OpenAI and run the application:"
Write-Host "     python main_retail.py"
Write-Host ""
