# Upgrade Remote Server v1.5.1 langsung ke v1.7

```bash
cd ~/server/remote-server.v1.5.1 && docker compose down && cd ~/server && unzip remote-server.v1.7.zip && cd remote-server.v1.7 && docker compose up -d --build
```

Migration berjalan berurutan sampai revision `0006`. Jangan gunakan `docker compose down -v`; volume lama `scaleup_server_data` tetap dipakai.
