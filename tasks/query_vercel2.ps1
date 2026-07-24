$token = [Environment]::GetEnvironmentVariable('VERCEL_TOKEN','User')
Write-Host "Token length: $($token.Length)"

# Try to get user info first
try {
    $result = Invoke-WebRequest -Uri 'https://api.vercel.com/v2/user' -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing -ErrorAction Stop
    $user = $result.Content | ConvertFrom-Json
    Write-Host "=== User Info ==="
    Write-Host "User: $($user.user.name) ($($user.user.email))"
    Write-Host "UID: $($user.user.uid)"
} catch {
    Write-Host "Error getting user info: $($_.Exception.Message)"
    try {
        $result = $_.Exception.Response
        $reader = New-Object System.IO.StreamReader($result.GetResponseStream())
        Write-Host "Response: $($reader.ReadToEnd())"
    } catch {}
}

# Try to get teams
try {
    $result = Invoke-WebRequest -Uri 'https://api.vercel.com/v2/teams' -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing -ErrorAction Stop
    Write-Host "=== Teams ==="
    Write-Host $result.Content
} catch {
    Write-Host "Error getting teams: $($_.Exception.Message)"
}

# Try different team IDs from env or common ones
# Try with team ID from env
$teamId = [Environment]::GetEnvironmentVariable('VERCEL_TEAM_ID','User')
if (-not $teamId) { $teamId = [Environment]::GetEnvironmentVariable('VERCEL_ORG_ID','User') }
if ($teamId) {
    Write-Host "Trying with team ID: $teamId"
    try {
        $result = Invoke-WebRequest -Uri 'https://api.vercel.com/v9/projects' -Headers @{ Authorization = "Bearer $token"; "x-vercel-team-id" = $teamId } -UseBasicParsing -ErrorAction Stop
        Write-Host "=== Projects (with team) ==="
        Write-Host $result.Content
    } catch {
        Write-Host "Error with team: $($_.Exception.Message)"
    }
}
