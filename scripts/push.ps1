$wwwroot = '/var/www/html/chriscarl.com/src'
$src = [IO.Path]::GetFullPath("$PSScriptRoot/../src")

Write-Host -ForegroundColor Yellow "Deleting '$wwwroot'"
$cmd = "ssh ubuntu@chriscarl.com `"rm -rf '$wwwroot'`""
Write-Host -ForegroundColor Cyan $cmd
Invoke-Expression $cmd
$cmd = "ssh ubuntu@chriscarl.com `"mkdir -p '$wwwroot'`""
Write-Host -ForegroundColor Cyan $cmd
Invoke-Expression $cmd

Write-Host -ForegroundColor Yellow "Pushing '$src'"
Get-ChildItem -Path $src -Recurse | ForEach-Object {
    $relpath = $_.FullName.Substring($src.Length)
    $nixrelp = $relpath.Replace('\', '/')
    $nixpath = "$wwwroot$nixrelp"

    $item = Get-Item $_.FullName
    if ($item.PSIsContainer) {
        $cmd = "ssh ubuntu@chriscarl.com `"mkdir -p '$nixpath'`""
    } else {
        # scp "$src/**" ubuntu@chriscarl.com:/var/www/html/chriscarl.com/src/
        $cmd = "scp `"$($_.FullName)`" ubuntu@chriscarl.com:$nixpath"
    }
    Write-Host -ForegroundColor Cyan $cmd
    Invoke-Expression $cmd
}
Write-Host -ForegroundColor Green "Done!"
