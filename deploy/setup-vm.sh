#!/usr/bin/env bash
# One-shot setup for a fresh Ubuntu VM (tested layout: Oracle Cloud Always Free, ARM or x86).
# Usage: bash deploy/setup-vm.sh   (run from the cloned repo root, after creating deploy/.env)
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

# Oracle's Ubuntu images ship iptables rules that block 80/443 even when the cloud
# security list allows them.
if command -v iptables >/dev/null 2>&1; then
  sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
  sudo iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
  command -v netfilter-persistent >/dev/null 2>&1 && sudo netfilter-persistent save || true
fi

if [ ! -f deploy/.env ]; then
  echo "deploy/.env is missing. Copy deploy/.env.example to deploy/.env and fill it in first." >&2
  exit 1
fi

# Swap guards against OOM during the torch/sentence-transformers build and model load.
if [ ! -f /swapfile ]; then
  sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

sudo docker compose -f deploy/docker-compose.yml up -d --build
echo "Deployed. Check: curl -s https://\$(grep ^DOMAIN= deploy/.env | cut -d= -f2)/health/readiness"
