$token = [Environment]::GetEnvironmentVariable('VERCEL_TOKEN','User')
Write-Host "Token length: $($token.Length)"

# Query projects list
try {
    $result = Invoke-WebRequest -Uri 'https://api.vercel.com/v9/projects' -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing -ErrorAction Stop
    Write-Host "=== Projects List ==="
    Write-Host $result.Content
} catch {
    Write-Host "Error querying projects: $($_.Exception.Message)"
}

# Try to inspect specific projects
$projects = @('frontend', 'ai-kill-cancer-zqpi')
foreach ($project in $projects) {
    try {
        $result = Invoke-WebRequest -Uri "https://api.vercel.com/v9/projects/$project" -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing -ErrorAction Stop
        Write-Host "=== Project: $project ==="
        Write-Host $result.Content
    } catch {
        Write-Host "Error querying project '$project': $($_.Exception.Message)"
    }
}
