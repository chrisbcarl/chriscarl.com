[CmdletBinding()]
param (
    [Parameter()][String]$ImagePath
)

$ImageDirpath = [IO.Path]::GetDirectoryName($ImagePath)
$FavPath = [IO.Path]::GetFullPath("$ImageDirpath/favicon.ico")

# https://usage.imagemagick.org/thumbnails/#favicon
magick $ImagePath -alpha off -resize 256x256 -define icon:auto-resize="256,128,96,64,48,32,16" $FavPath
