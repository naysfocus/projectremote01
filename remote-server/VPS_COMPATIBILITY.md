# Kesesuaian VPS Target

Target:

- Ubuntu 22.04.5 LTS;
- ARM64/AArch64 Neoverse-N1;
- 2 CPU dan RAM 11 GiB;
- Docker 29.6.2;
- Docker Compose v5.3.1;
- Tailscale aktif pada `100.113.142.11`.

Port yang telah digunakan aplikasi lain tidak disentuh. Remote Server menggunakan:

```text
100.113.142.11:8800 → container server:8000
```

Database dan seluruh pengaturan persisten berada pada volume:

```text
volume persisten lama (dipertahankan otomatis saat upgrade)
```

Image menggunakan base image multi-architecture untuk ARM64 dan AMD64. Binary `cloudflared` diambil dari image resmi multi-architecture saat Docker build.
