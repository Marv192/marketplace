
KIBANA_URL="http://kibana:5601"
IMPORT_FILE="/usr/share/kibana/data/auth_dashboard.ndjson"


if [ -f "$IMPORT_FILE" ]; then
  curl -s -X POST "$KIBANA_URL/api/saved_objects/_import?overwrite=true" \
    -H "kbn-xsrf: true" \
    --form file=@"$IMPORT_FILE"

  echo "Dashboard imported"
else
  echo "Dashboard import failed"
fi