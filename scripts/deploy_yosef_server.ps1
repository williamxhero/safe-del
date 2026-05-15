$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DeployRoot = Join-Path $ProjectRoot ".safe-del-deploy"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$PackagePath = Join-Path $DeployRoot "safe-del-$Stamp.tar"
$RemoteScriptPath = Join-Path $DeployRoot "deploy-$Stamp.sh"
$RemotePackagePath = "/tmp/safe-del-deploy-$Stamp.tar"
$RemoteScriptRemotePath = "/tmp/safe-del-deploy-$Stamp.sh"

New-Item -ItemType Directory -Force -Path $DeployRoot | Out-Null

Push-Location $ProjectRoot
try {
    tar -cf $PackagePath pyproject.toml README.md README_EN.md src scripts
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
scp $PackagePath "yosef-server:$RemotePackagePath"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$RemoteScript = @"
set -eu

release_id="safe-del-release-$Stamp"
release_dir="/srv/safe-del/releases/`$release_id"
venv_dir="/srv/safe-del/venv"

sudo -n mkdir -p /srv/safe-del/releases /srv/safe-del/bin /srv/safe-del/scripts
sudo -n chown -R "`$USER:`$USER" /srv/safe-del
mkdir -p "`$release_dir"

data_trash="/data/.Trash-`$(id -u)"
sudo -n mkdir -p "`$data_trash/files" "`$data_trash/info"
sudo -n chown -R "`$USER:`$USER" "`$data_trash"
sudo -n chmod 700 "`$data_trash"
chmod 700 "`$data_trash/files" "`$data_trash/info"

tar -xf "$RemotePackagePath" -C "`$release_dir"

if ! python3 -m venv "`$venv_dir" >/dev/null 2>&1; then
    sudo -n apt-get update
    sudo -n apt-get install -y python3-venv
    python3 -m venv "`$venv_dir"
fi

"`$venv_dir/bin/python" -m pip install "`$release_dir"
ln -sfn "`$release_dir" /srv/safe-del/current

sudo -n ln -sfn "`$venv_dir/bin/safe-del" /usr/local/bin/safe-del
sudo -n ln -sfn "`$venv_dir/bin/safe-del-install" /usr/local/bin/safe-del-install
sudo -n ln -sfn "`$venv_dir/bin/safe-del-empty-trash" /usr/local/bin/safe-del-empty-trash

"`$venv_dir/bin/safe-del-install"

for command_name in rm rmdir unlink del erase rd; do
    shim_path="/srv/safe-del/bin/`$command_name"
    cat > "`$shim_path" <<'SH'
#!/bin/sh
exec /usr/local/bin/safe-del "$@"
SH
    chmod 0755 "`$shim_path"
    sudo -n install -m 0755 "`$shim_path" "/usr/local/bin/`$command_name"
done

cat > /srv/safe-del/scripts/empty-trash.sh <<'SH'
#!/bin/sh
set -eu
exec /usr/local/bin/safe-del-empty-trash "$@"
SH
chmod 0755 /srv/safe-del/scripts/empty-trash.sh

command -v safe-del
command -v safe-del-empty-trash
command -v rm
safe-del --version
rm --version
safe-del-empty-trash --help >/dev/null
/srv/safe-del/scripts/empty-trash.sh --help >/dev/null
"@

$RemoteScript = $RemoteScript -replace "`r", ""
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($RemoteScriptPath, $RemoteScript, $Utf8NoBom)

scp $RemoteScriptPath "yosef-server:$RemoteScriptRemotePath"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

ssh yosef-server "bash $RemoteScriptRemotePath"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
