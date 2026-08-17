#!/usr/bin/env bash
#
# 서버 배포 스크립트 — 서버에서 `./update.sh` 하나만 실행하면 된다.
#   코드 받기 → 이미지 빌드 → 컨테이너 교체 → 살아났는지 확인
#
# 안전장치
#   · 빌드가 실패하면 거기서 멈춘다. 지금 돌고 있는 서버는 건드리지 않는다.
#   · `docker restart`가 아니라 rm -f 후 run 이다. --env-file 은 컨테이너를
#     만들 때 한 번만 읽으므로, restart 로는 바뀐 .env 가 반영되지 않는다.
#   · 전체를 main() 안에 넣었다. 이렇게 해야 bash 가 스크립트를 통째로 읽은 뒤
#     실행하므로, 실행 도중 git pull 이 이 파일을 바꿔도 꼬이지 않는다.
#     (단, update.sh 자체의 변경은 '다음 실행'부터 적용된다)
set -euo pipefail

main() {
  local REPO="${REPO:-$HOME/uplp_back}"
  local ENV_FILE=/etc/uplp/.env
  local UPLOADS=/var/uplp/uploads
  local IMAGE=uplp-back
  local NAME=uplp

  if [ ! -f "$ENV_FILE" ]; then
    echo "✗ $ENV_FILE 이 없다. 이 파일이 유일한 환경변수 원본이다." >&2
    exit 1
  fi

  cd "$REPO"

  echo "▶ 코드 받는 중"
  local before after
  before=$(git rev-parse --short HEAD)
  git pull --ff-only
  after=$(git rev-parse --short HEAD)
  if [ "$before" = "$after" ]; then
    echo "  변경 없음 ($after)"
  else
    echo "  $before → $after"
    git --no-pager log --oneline "$before..$after" | sed 's/^/    /'
  fi

  # 빌드를 먼저 끝낸다. 여기서 실패하면 아래로 내려가지 않으므로
  # 기존 컨테이너가 그대로 살아 있다.
  echo "▶ 이미지 빌드 중 (실패해도 현재 서버는 계속 돌아간다)"
  sudo docker build -t "$IMAGE" .

  echo "▶ 컨테이너 교체"
  sudo mkdir -p "$UPLOADS"
  sudo docker rm -f "$NAME" >/dev/null 2>&1 || true
  sudo docker run -d --name "$NAME" --restart=always \
    --env-file "$ENV_FILE" \
    -v "$UPLOADS":/app/uploads \
    -p 127.0.0.1:8000:10000 \
    "$IMAGE" >/dev/null

  echo "▶ 응답 확인"
  local i code
  for i in $(seq 1 20); do
    sleep 1
    code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/notices || true)
    if [ "$code" = "200" ]; then
      echo "✓ 배포 완료 ($after)"
      return 0
    fi
  done

  echo "✗ 20초 동안 응답이 없다. 로그를 확인할 것:" >&2
  echo "    sudo docker logs --tail 50 $NAME" >&2
  return 1
}

main "$@"
