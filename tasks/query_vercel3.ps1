$token = [Environment]::GetEnvironmentVariable('VERCEL_TOKEN','User')
try {
    $response = Invoke-WebRequest -Uri 'https://api.vercel.com/v2/user' -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing -ErrorAction Stop
    Write-Host $response.Content
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "Status code: $statusCode"
    try {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        Write-Host "Body: $($reader.ReadToEnd())"
    } catch {
        Write-Host "Could not read response body"
    }
}
