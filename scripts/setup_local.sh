#!/usr/bin/env bash
# Lokal tek-seferlik kurulum: notebook çıktıları git'e girmesin (pull çakışması fix).
# Kullanım:  bash scripts/setup_local.sh
set -e

cd "$(dirname "$0")/.."

echo ">> nbstripout kuruluyor..."
if command -v conda >/dev/null 2>&1; then
  conda install -c conda-forge nbstripout -y || pip install nbstripout
else
  pip install nbstripout
fi

echo ">> git filtresi bağlanıyor (nbstripout --install)..."
nbstripout --install

echo ">> durum:"
nbstripout --status

echo
echo "Tamam. Artık notebook'ları çalıştırsan bile 'git pull'/'push' çakışmaz;"
echo "notebook çıktıları otomatik yok sayılır (commit edilmez)."
