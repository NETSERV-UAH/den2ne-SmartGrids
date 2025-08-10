#!/usr/bin/env bash
set -euo pipefail

# Nombre del fichero grande a eliminar del historial (ruta relativa en repo)
TARGET_PATH="src/ccomplex/topo.zip"

# Remote a usar
REMOTE_NAME="origin"

# Backup mirror dir (se crea al lado del repo)
REPO_ROOT=$(git rev-parse --show-toplevel)
BACKUP_MIRROR="${REPO_ROOT}-backup-$(date +%Y%m%d-%H%M%S).git"
TAR_BACKUP="${REPO_ROOT}-backup-$(date +%Y%m%d-%H%M%S).tar.gz"

echo "Repo root detectado: ${REPO_ROOT}"
echo "Fichero a eliminar del historial: ${TARGET_PATH}"
echo
read -p "¿Continuar? Esto reescribirá el historial y requerirá push forzado. (s/N) " -r
if [[ "${REPLY}" != "s" && "${REPLY}" != "S" ]]; then
    echo "Abortando."
    exit 1
fi

# 1) Comprobar working tree limpio
cd "${REPO_ROOT}"
if [[ -n "$(git status --porcelain)" ]]; then
    echo "ERROR: Working tree no está limpio. Haz commit o stashing antes de continuar."
    git status --porcelain
    exit 1
fi

# 2) Hacer backup espejo (mirror)
echo
echo "[1/8] Creando backup espejo (clone --mirror) en: ${BACKUP_MIRROR}"
git clone --mirror "${REPO_ROOT}" "${BACKUP_MIRROR}"

echo "[2/8] También creando tar.gz del repo actual en: ${TAR_BACKUP}"
tar -czf "${TAR_BACKUP}" -C "$(dirname "${REPO_ROOT}")" "$(basename "${REPO_ROOT}")"

# 3) Mostrar blobs grandes como comprobación (opcional, puede tardar)
echo
echo "[3/8] Buscando blobs grandes (esto puede tardar unos segundos)..."
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | sed -n 's/^blob //p' \
  | sort -k2 -n -r \
  | head -n 10 || true

# 4) Verificar que git filter-repo esté disponible
if ! command -v git-filter-repo >/dev/null 2>&1 && ! command -v git-filter-repo.py >/dev/null 2>&1; then
    echo
    echo "ERROR: git filter-repo no está instalado."
    echo "Instálalo con: pip install git-filter-repo"
    echo "o revisa https://github.com/newren/git-filter-repo"
    exit 1
fi

# 5) Ejecutar git filter-repo para eliminar TARGET_PATH
echo
echo "[4/8] Ejecutando git filter-repo para eliminar '${TARGET_PATH}' del historial..."
# usamos --invert-paths para eliminar la ruta indicada
git filter-repo --path "${TARGET_PATH}" --invert-paths

# 6) Añadir .gitignore (evita reincidir) y commitear (solo si no está ya)
if ! grep -Fxq "${TARGET_PATH}" .gitignore 2>/dev/null; then
    echo
    echo "[5/8] Añadiendo ${TARGET_PATH} a .gitignore y commiteando"
    echo "${TARGET_PATH}" >> .gitignore
    git add .gitignore
    git commit -m "Ignore large file ${TARGET_PATH} (added after history cleanup)"
else
    echo "[5/8] ${TARGET_PATH} ya estaba en .gitignore"
fi

# 7) Limpiar objetos y compactar
echo
echo "[6/8] Limpiando reflogs y ejecutando git gc (prune aggressive)..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 8) Push forzado de ramas y tags
echo
echo "[7/8] Preparado para push forzado al remoto '${REMOTE_NAME}'."
read -p "¿Hacer git push --force origin --all y --tags ahora? (s/N) " -r
if [[ "${REPLY}" != "s" && "${REPLY}" != "S" ]]; then
    echo "Puedes hacer manualmente:"
    echo "  git push --force ${REMOTE_NAME} --all"
    echo "  git push --force ${REMOTE_NAME} --tags"
    echo "FIN (no se hizo push)."
    exit 0
fi

echo "[8/8] Haciendo push forzado de todas las ramas y tags..."
git push --force "${REMOTE_NAME}" --all
git push --force "${REMOTE_NAME}" --tags

echo
echo "TERMINADO. Resumen:"
echo " - Backup espejo creado: ${BACKUP_MIRROR}"
echo " - Tar.gz backup: ${TAR_BACKUP}"
echo " - Fichero eliminado del historial: ${TARGET_PATH}"
echo
echo "IMPORTANTE: todos los colaboradores deben volver a clonar el repo o resetear sus clones:"
echo "  git fetch && git reset --hard ${REMOTE_NAME}/main"
echo
echo "Si quieres, puedo generar el comando para forzar a los colaboradores (o ayudar a automatizar limpieza local)."

exit 0
