# Jenkins + True Docker-in-Docker (DinD) — with explicit containerd startup
FROM jenkins/jenkins:lts

USER root

# Default storage driver for Docker Desktop (more compatible than overlay2)
ENV DOCKER_DRIVER=vfs

# Prereqs
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      gnupg \
      lsb-release \
      iptables \
      tini \
      procps \
    && rm -rf /var/lib/apt/lists/*

# Docker repo + install engine (multi-arch safe)
RUN set -eux; \
    install -m 0755 -d /etc/apt/keyrings; \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg; \
    chmod a+r /etc/apt/keyrings/docker.gpg; \
    ARCH="$(dpkg --print-architecture)"; \
    CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"; \
    echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${CODENAME} stable" > /etc/apt/sources.list.d/docker.list; \
    apt-get update -y; \
    apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io; \
    rm -rf /var/lib/apt/lists/*

# Allow Jenkins to use Docker socket (inside the container)
RUN groupadd -f docker && usermod -aG docker jenkins

# State dirs
RUN mkdir -p /var/lib/docker /var/run/docker /run/containerd
VOLUME /var/lib/docker

# DinD entrypoint script (starts containerd -> dockerd -> jenkins)
RUN cat > /usr/local/bin/dind-jenkins-entrypoint.sh <<'EOF'
#!/bin/sh
set -e

# Clean stale pid/sockets
rm -f /var/run/docker.pid /var/run/docker.sock || true
rm -f /run/containerd/containerd.sock /run/containerd/containerd.sock.ttrpc || true

# Kill any leftover containerd just in case
pkill -x containerd 2>/dev/null || true

# Start containerd explicitly (with logs)
containerd > /var/log/containerd.log 2>&1 &
CONTAINERD_PID=$!

# Wait for containerd socket (up to 60s)
i=0
until [ -S /run/containerd/containerd.sock ]; do
  i=$((i+1))
  if [ "$i" -gt 60 ]; then
    echo "containerd did not start within 60s. Showing containerd logs:" >&2
    tail -n 200 /var/log/containerd.log >&2 || true
    exit 1
  fi
  sleep 1
done

# Start dockerd using the containerd socket
dockerd \
  --host=unix:///var/run/docker.sock \
  --containerd=/run/containerd/containerd.sock \
  --storage-driver=${DOCKER_DRIVER:-vfs} \
  > /var/log/dockerd.log 2>&1 &
DOCKERD_PID=$!

# Ensure daemons stop on exit
trap 'kill $DOCKERD_PID 2>/dev/null || true; kill $CONTAINERD_PID 2>/dev/null || true' INT TERM EXIT

# Wait for Docker daemon to be ready (up to 120s)
i=0
until docker info >/dev/null 2>&1; do
  i=$((i+1))
  if [ "$i" -gt 120 ]; then
    echo "Docker did not start within 120s. Showing dockerd logs:" >&2
    tail -n 200 /var/log/dockerd.log >&2 || true
    echo "Showing containerd logs:" >&2
    tail -n 200 /var/log/containerd.log >&2 || true
    exit 1
  fi
  sleep 1
done

# Start Jenkins as jenkins user (keep this script alive)
su -s /bin/sh -c "/usr/local/bin/jenkins.sh $*" jenkins &
JENKINS_PID=$!

wait $JENKINS_PID
EOF

# Fix CRLF if any + make executable
RUN sed -i 's/\r$//' /usr/local/bin/dind-jenkins-entrypoint.sh && \
    chmod +x /usr/local/bin/dind-jenkins-entrypoint.sh

EXPOSE 8080 50000

ENTRYPOINT ["tini", "--", "/usr/local/bin/dind-jenkins-entrypoint.sh"]