# Upgrade dari server.v1.5 ke Remote Server v1.5.1

Perubahan nama berlaku pada aplikasi, dashboard, image, container, dan paket ZIP. Data lama tetap digunakan.

Volume Docker lama bernama `scaleup_server_data` dipertahankan secara internal agar database, password, token terenkripsi, backup, dan pengaturan tidak hilang. Nama teknis lama tersebut tidak lagi ditampilkan di web app.

Jalankan:

```bash
cd ~/server/server.v1.5
docker compose down
cd ~/server
unzip remote-server.v1.5.1.zip
cd remote-server.v1.5.1
docker compose up -d --build
```

Jangan gunakan `docker compose down -v`.

Container baru:

```text
remote-server
remote-scheduler
remote-integrations
```

Dashboard tetap dapat dibuka melalui:

```text
https://remote.darda.uk/login
```
