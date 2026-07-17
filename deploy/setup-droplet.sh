#!/usr/bin/env bash
# One-time bootstrap for a fresh DigitalOcean Ubuntu 24.04 Droplet: installs
# Docker Engine + the Compose plugin via Docker's official repo (more
# current and reliable than Ubuntu's own `docker.io`/`docker-compose-v2`
# packages), then prints next steps. Does NOT touch the firewall or clone
# the repo — those are deliberate choices left to you (see docs/DeveloperGuide.md).
#
# Usage: curl -fsSL <raw-url-to-this-file> | sudo bash
#    or: sudo bash deploy/setup-droplet.sh
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root (or with sudo)." >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Docker + Compose plugin already installed:"
  docker --version
  docker compose version
  exit 0
fi

echo "==> Installing prerequisites"
apt-get update -y
apt-get install -y ca-certificates curl gnupg

echo "==> Adding Docker's official apt repository"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

. /etc/os-release
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

echo "==> Installing Docker Engine + Compose plugin"
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

echo "==> Done"
docker --version
docker compose version

cat <<'EOF'

Next steps:
  git clone <your-repo-url> tradetown && cd tradetown
  cp .env.example .env        # optional — every var has a working default
  docker compose up -d --build

Then open http://<this-droplet-ip> in a browser.

If you're not deploying as root, add your user to the docker group so you
don't need sudo for every command, then log out/in for it to take effect:
  usermod -aG docker <your-user>

Firewall (not configured by this script): if you're using DigitalOcean
Cloud Firewalls, allow inbound 22/tcp (SSH) and 80/tcp (HTTP), plus 443/tcp
once you add TLS (see deploy/nginx/tradetown.conf.example). If you're using
ufw instead, remember to `ufw allow OpenSSH` before enabling it, or you'll
lock yourself out.
EOF
