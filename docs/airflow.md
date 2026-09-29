
## Prerequisites

The Airflow container shells out to `docker exec` for each task. It needs
access to the host's Docker socket:

```bash
sudo chmod 666 /var/run/docker.sock
Without this, tasks fail with permission denied because the container's
airflow user (UID 50000) cannot read the socket.

Why this is needed: the Docker socket is owned by root:docker with mode
0660. The Airflow container runs as UID 50000 with no docker group access.
chmod 666 opens it up — acceptable for local development, but for production
you'd use a socket proxy (e.g., tecnativa/docker-socket-proxy).

Verifying
After sudo chmod 666 /var/run/docker.sock:

bash
docker exec openbi-airflow docker ps
# → should list running containers

docker exec openbi-airflow airflow tasks test \
  openbi_smoke check_monthly_revenue 2026-09-29
# → monthly_revenue rows: 132
