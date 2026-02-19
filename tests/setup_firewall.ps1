# Check if running as Admin
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "This script requires Administrator privileges!"
    Write-Warning "Please right-click PowerShell and select 'Run as Administrator'"
    exit
}

$ruleName = "CamPark FTP"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existing) {
    Write-Host "✅ Firewall rule '$ruleName' already exists."
} else {
    Write-Host "Creating firewall rule '$ruleName'..."
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort 21,30000-30009 `
        -Profile Any
    Write-Host "✅ Firewall rule created successfully."
}

Write-Host "Verifying rule..."
Get-NetFirewallRule -DisplayName $ruleName | Select-Object DisplayName, Action, Direction, Enabled
