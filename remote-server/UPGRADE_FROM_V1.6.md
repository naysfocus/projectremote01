# Upgrade Remote Server v1.6 ke v1.7

```bash
cd ~/server/remote-server.v1.6 && docker compose down && cd ~/server && unzip remote-server.v1.7.zip && cd remote-server.v1.7 && docker compose up -d --build
```

Jangan gunakan `docker compose down -v`. Volume `scaleup_server_data` dipakai kembali sehingga database, device, otorisasi, lokasi, tag, token integrasi, password admin, dan backup tetap ada.

Periksa dengan:

```bash
docker compose ps
```
