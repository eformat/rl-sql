#!/usr/bin/env bash
#
# Deploy Trino with NNDSS data for RL reward validation.
#
# Deploys: MinIO → Trino → loads NNDSS tables → Trino Query UI
# Prereqs: oc, helm, python3 with trino/pandas/openpyxl
#
# Usage:
#   ./deploy/deploy-trino.sh                    # deploy
#   ./deploy/deploy-trino.sh --uninstall        # tear down
#
# Environment:
#   NAMESPACE          Target namespace (default: user's current project)
#   MINIO_PVC_SIZE     MinIO PVC size (default: 5Gi)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -x "${REPO_DIR}/venv/bin/python3" ]; then
  PYTHON="${REPO_DIR}/venv/bin/python3"
else
  PYTHON="python3"
fi

NAMESPACE="${NAMESPACE:-$(oc project -q 2>/dev/null || echo rl-sql)}"
MINIO_NAMESPACE="${NAMESPACE}"
export MINIO_PVC_SIZE="${MINIO_PVC_SIZE:-5Gi}"

# ── Uninstall ────────────────────────────────────────────────
if [ "${1:-}" = "--uninstall" ]; then
  echo "==> Uninstalling Trino + MinIO from ${NAMESPACE}"
  helm uninstall trino-query-ui -n "${NAMESPACE}" 2>/dev/null || true
  helm uninstall trino -n "${NAMESPACE}" 2>/dev/null || true
  oc delete deployment nessie -n "${NAMESPACE}" 2>/dev/null || true
  oc delete service nessie -n "${NAMESPACE}" 2>/dev/null || true
  oc delete job minio-create-bucket -n "${NAMESPACE}" 2>/dev/null || true

  # Delete MinIO resources
  for f in "${SCRIPT_DIR}"/trino-chart/minio/base/minio-*.yaml; do
    oc delete -f "$f" -n "${NAMESPACE}" 2>/dev/null || true
  done

  # Delete routes
  oc delete route trino-coordinator trino-query-ui minio -n "${NAMESPACE}" 2>/dev/null || true

  echo "Done. PVCs are preserved — delete manually if needed:"
  echo "  oc delete pvc -l app.kubernetes.io/name=minio -n ${NAMESPACE}"
  exit 0
fi

echo "============================================"
echo "  Trino + NNDSS Data — Deploy"
echo "============================================"
echo "Namespace:      ${NAMESPACE}"
echo "MinIO PVC size: ${MINIO_PVC_SIZE}"
echo ""

# ── 1. Deploy Trino ──────────────────────────────────────────
echo "==> 1. Deploying Trino (Iceberg on MinIO)"
cd "${SCRIPT_DIR}/trino-chart"
SKIP_DATA=true \
  SKIP_UI=true \
  MINIO_NAMESPACE="${MINIO_NAMESPACE}" \
  TRINO_NAMESPACE="${NAMESPACE}" \
  S3_BUCKET="nndss-data" \
  ./install.sh
cd "${REPO_DIR}"

echo "Waiting for Trino coordinator to start..."
oc rollout status deployment/trino-coordinator -n "${NAMESPACE}" --timeout=180s

# ── 2. Load NNDSS data into Trino ────────────────────────────
echo "==> 2. Loading NNDSS data into Trino"
# Service name is "trino" (Helm release name), deployment is "trino-coordinator"
oc port-forward svc/trino -n "${NAMESPACE}" 8090:8080 &
PF_PID=$!
sleep 8

echo "  Loading annual notifications..."
TRINO_HOST=localhost TRINO_PORT=8090 \
  DATA_DIR="${SCRIPT_DIR}/nndss-data" \
  $PYTHON "${SCRIPT_DIR}/scripts/load-nndss-trino.py"

echo "  Loading population data..."
TRINO_HOST=localhost TRINO_PORT=8090 \
  $PYTHON "${SCRIPT_DIR}/scripts/load-population-trino.py"

echo "  Loading fortnightly notifications..."
TRINO_HOST=localhost TRINO_PORT=8090 \
  DATA_DIR="${SCRIPT_DIR}/nndss-data" \
  $PYTHON "${SCRIPT_DIR}/scripts/load-fortnightly-trino.py" 2>/dev/null || \
  echo "  (fortnightly loading skipped — optional)"

kill $PF_PID 2>/dev/null || true

# ── 3. Verify ────────────────────────────────────────────────
echo ""
echo "==> 3. Verifying Trino tables"
oc port-forward svc/trino -n "${NAMESPACE}" 8090:8080 &
PF_PID=$!
sleep 5

$PYTHON -c "
from trino.dbapi import connect
conn = connect(host='localhost', port=8090, user='admin', catalog='lakehouse', schema='nndss')
cur = conn.cursor()
for table in ['notifications', 'population', 'fortnightly_notifications']:
    try:
        cur.execute(f'SELECT COUNT(*) FROM lakehouse.nndss.{table}')
        count = cur.fetchone()[0]
        print(f'  {table}: {count} rows')
    except Exception as e:
        print(f'  {table}: not loaded ({e})')
conn.close()
"

kill $PF_PID 2>/dev/null || true

# ── 4. Deploy Trino Query UI ─────────────────────────────────
echo ""
echo "==> 4. Deploying Trino Query UI"
if [ -d "${SCRIPT_DIR}/trino-query-ui" ]; then
  helm upgrade --install trino-query-ui "${SCRIPT_DIR}/trino-query-ui" \
    -n "${NAMESPACE}" \
    --set trinoUpstream="trino:8080"
  oc rollout status deployment/trino-query-ui -n "${NAMESPACE}" --timeout=120s
  QUERY_UI_URL=$(oc get route trino-query-ui -n "${NAMESPACE}" -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
else
  echo "  trino-query-ui chart not found, skipping"
  QUERY_UI_URL=""
fi

echo ""
echo "============================================"
echo "  Trino Ready"
echo "============================================"
echo ""
echo "Port-forward for notebook access:"
echo "  oc port-forward svc/trino -n ${NAMESPACE} 8090:8080"
echo ""
echo "In-cluster service address:"
echo "  trino.${NAMESPACE}.svc.cluster.local:8080"
if [ -n "${QUERY_UI_URL:-}" ]; then
echo ""
echo "Trino Query UI:"
echo "  https://${QUERY_UI_URL}"
fi
echo ""
echo "To uninstall:"
echo "  ./deploy/deploy-trino.sh --uninstall"
