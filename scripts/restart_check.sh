#!/usr/bin/env bash
set -e
cd "/c/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room"
set -a; source .env.local; set +a

echo "token_len=${#JARVIS_DASHBOARD_DEV_TOKEN}"
H="Authorization: Bearer *** -H "X-Forwarded-User: jarvis"
URL="http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1"

echo "---GET /skills (with Bearer)---"
curl -s -m 3 -H "$H" "$URL/skills" | python -c "import json,sys; d=json.loads(sys.stdin.read()); print('skills count:', len(d.get('skills',[]))); print('sample:', d.get('skills',[{}])[0].get('name','?'))"

echo "---GET /agents/skills (with Bearer)---"
curl -s -m 3 -H "$H" "$URL/agents/skills" | python -c "import json,sys; d=json.loads(sys.stdin.read()); a=d.get('assignments',[]); print('assignments count:', len(a)); print('agents in assignments:', sorted({x.get('agent') for x in a if x.get('agent')}))"

echo "---GET /agents/proposals (with Bearer)---"
curl -s -m 3 -H "$H" "$URL/agents/proposals" | python -c "import json,sys; d=json.loads(sys.stdin.read()); print('proposals count:', len(d.get('proposals',[])))"
