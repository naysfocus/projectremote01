# Quick Start Remote Server v1.7

## Upgrade dari v1.6

```bash
cd ~/server/remote-server.v1.6
docker compose down
cd ~/server
unzip remote-server.v1.7.zip
cd remote-server.v1.7
docker compose up -d --build
docker compose ps
```

Jangan menambahkan `-v` pada `docker compose down`.

Sesudah tiga container sehat, jalankan Remote HP v1.48. Sinkronisasi pertama akan mengisi inventaris dan histori secara otomatis. Buka:

```text
https://remote.darda.uk/login
Device → pilih Remote HP → Lihat progres lengkap
```
