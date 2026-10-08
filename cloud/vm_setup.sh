#!/usr/bin/env bash
# Startup script for every VM (Ubuntu 24.04). Installs Java 21, Besu 24.7.0, the repo, and (client only)
# Node + Python dependencies. Touches /opt/ready when finished.
set -euo pipefail
exec > /var/log/vm_setup.log 2>&1
ROLE=$(curl -s -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/role)
REPO=$(curl -s -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/repo)
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y openjdk-21-jre-headless git curl python3-psutil python3-pip python3-venv
mkdir -p /opt && cd /opt
curl -sL -o besu.tgz https://github.com/hyperledger/besu/releases/download/24.7.0/besu-24.7.0.tar.gz
tar xzf besu.tgz && rm besu.tgz
git clone "$REPO" /opt/repo
if [ "$ROLE" = "client" ]; then
  apt-get install -y nodejs npm
  mkdir -p /opt/nd && cd /opt/nd && npm install --no-audit --no-fund solc@0.8.20 ethers@6
  pip3 install --break-system-packages web3 fastapi "uvicorn[standard]" requests pandas numpy scipy
fi
touch /opt/ready
