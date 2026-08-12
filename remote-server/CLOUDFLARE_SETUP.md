# Panduan Cloudflare Tunnel v1.5

## Yang dilakukan di Cloudflare

1. Buka **Networking → Tunnels → Create a Tunnel**.
2. Beri nama tunnel.
3. Pada pilihan environment, pilih **Docker**.
4. Klik ikon salin pada perintah yang berisi `--token eyJ...`.
5. Jangan jalankan perintah tersebut di VPS.

## Yang dilakukan di Remote Server

1. Buka **Integrasi → Cloudflare Tunnel**.
2. Tempel seluruh perintah Docker ke kolom **Perintah Docker atau Tunnel Token**.
3. Pilih mode **Auto**.
4. Centang **Aktifkan Cloudflare Tunnel**.
5. Hostname boleh dikosongkan dahulu.
6. Klik **Simpan dan terapkan Cloudflare**.
7. Tunggu status menjadi **Terhubung**.

## Membuat alamat HTTPS

Setelah connector terhubung:

1. Buka tunnel di Cloudflare.
2. Pilih **Routes → Add route → Published application**.
3. Pilih subdomain dan domain, misalnya `remote.domainkamu.com`.
4. Service type: `HTTP`.
5. Service URL: `http://server:8000`.
6. Simpan route.
7. Kembali ke web app.
8. Isi hostname `remote.domainkamu.com`.
9. Klik **Simpan dan terapkan Cloudflare**.
10. Klik **Uji alamat HTTPS**.

## Bila port 7844 diblokir

Cloudflare Tunnel membutuhkan koneksi keluar port 7844:

- UDP untuk QUIC;
- TCP untuk HTTP/2.

Gunakan mode **Auto** terlebih dahulu. Web app akan menampilkan diagnosis dari log connector. Bila TCP dan UDP sama-sama diblokir, masalah berada pada firewall, WARP, kebijakan jaringan VPS, atau upstream provider dan tidak dapat diperbaiki secara aman dengan memberi container akses penuh ke host.

## Keamanan token

Tunnel Token memberi connector akses untuk menjalankan tunnel. Rotasi token bila pernah terlihat pada screenshot, chat, atau log.
