$src = [IO.Path]::GetFullPath("$PSScriptRoot/..")
$ignoreme = [IO.Path]::GetFullPath("$src/ignoreme/159.54.179.175/var/log")

New-Item -ItemType Directory -Path $ignoreme -ErrorAction SilentlyContinue

$cmd = "scp ubuntu@chriscarl.com:/var/log/auth.log `"$ignoreme\`""
Write-Host -ForegroundColor Cyan $cmd
Invoke-Expression $cmd

$cmd = "scp ubuntu@chriscarl.com:/var/log/nginx/* `"$ignoreme\nginx\`""
Write-Host -ForegroundColor Cyan $cmd
Invoke-Expression $cmd
