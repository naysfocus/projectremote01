# Build & Deploy Remote HP Android v1.0.0 — dari nol

Dokumen ini sengaja dibuat untuk pengguna yang belum pernah memakai Android Studio.

## A. Yang perlu diinstal

1. Install **Android Studio** versi stabil terbaru.
2. Saat wizard pertama, pilih instalasi Standard agar Android SDK, Platform Tools, dan emulator tools ikut dipasang.
3. Restart Android Studio setelah komponen SDK selesai.

## B. Membuka project

1. Ekstrak `project-remote-v1.0.zip`.
2. Buka Android Studio.
3. Pilih **Open**.
4. Pilih folder `remote-hp-android`. Jangan memilih folder `app` di dalamnya.
5. Pilih **Trust Project** bila diminta.
6. Tunggu **Gradle Sync** selesai. Android Studio mungkin mengunduh Gradle/SDK pada pembukaan pertama.

Project menggunakan compileSdk 35, minSdk 26, Java 17, Kotlin, dan Android Gradle Plugin 8.5.2.

## C. Menyiapkan HP untuk instalasi development

1. Di Android: Settings → About phone → tekan **Build number** 7 kali hingga Developer Options aktif.
2. Settings → Developer options → aktifkan **USB debugging**.
3. Hubungkan HP ke PC dengan USB.
4. Saat HP menampilkan `Allow USB debugging?`, pilih **Allow**.
5. Di bagian atas Android Studio, HP harus muncul pada daftar target device.

## D. Install langsung dari Android Studio

1. Pastikan konfigurasi yang dipilih adalah `app`.
2. Pilih HP fisik pada target device.
3. Tekan tombol **Run ▶**.
4. Tunggu build dan instalasi.
5. Aplikasi **Remote HP Android** akan terbuka di HP.

## E. Pairing ke Remote HP PC

1. Pada PC jalankan `remote-hp-pc/jalankan-windows-lan.bat`.
2. Buka Remote HP PC → Pengaturan → Android Controller.
3. Pastikan sumber video di PC sudah benar, lalu klik **Refresh Cache Video Android**. Scan folder dilakukan dari tindakan admin PC ini; aplikasi Android tidak melakukan scan folder otomatis.
4. Pilih HP yang akan dikendalikan.
5. Buat QR pairing.
6. Scan QR menggunakan kamera Android.
7. Tautan `remotehp://pair?...` membuka Remote HP Android dan mengisi alamat PC + kode otomatis.
8. Periksa nama Android lalu tekan **PASANGKAN**.
9. Saat akan memakai overlay, Android akan meminta izin **Display over other apps**. Berikan izin tersebut.

QR hanya membawa alamat LAN dan kode pairing sekali pakai. Bearer token permanen dibuat setelah pairing dan disimpan melalui Android Keystore.

## F. Membuat APK debug untuk instalasi manual

Android Studio → **Build** → **Build APK(s)**.

Hasil umumnya berada di:

`app/build/outputs/apk/debug/app-debug.apk`

APK debug cocok untuk pengujian internal. Untuk distribusi production gunakan signed release APK.

## G. Membuat signed release APK

1. Android Studio → Build → **Generate Signed App Bundle or APK**.
2. Pilih **APK**.
3. Buat atau pilih keystore milik project.
4. Simpan keystore dan password di tempat aman dan jangan masukkan ke ZIP source.
5. Pilih build variant `release`.
6. Build.

Jangan kehilangan keystore production. Update APK dengan applicationId yang sama membutuhkan key penandatanganan yang sama.

## H. Error umum

- **Gradle Sync failed**: pastikan internet tersedia saat pembukaan pertama dan gunakan JDK bawaan Android Studio/Java 17.
- **SDK 35 missing**: Tools → SDK Manager → install Android SDK Platform 35.
- **Device unauthorized**: cabut/pasang USB dan setujui dialog USB debugging pada HP.
- **No devices**: cek kabel data, USB debugging, dan `adb devices`.
- **PC tidak terhubung**: pastikan mode LAN Remote HP PC aktif, PC/HP satu jaringan, dan firewall mengizinkan port 5001 pada Private Network.
- **Overlay tidak muncul**: Settings Android → Special app access → Display over other apps → izinkan Remote HP Android.

## I. Catatan keamanan

Aplikasi tidak meminta Accessibility Service, tidak menekan TikTok otomatis, dan tidak membaca password/form TikTok. Mobile API hanya untuk LAN tepercaya.

## J. Status validasi paket source ini

Source v1.0.0 telah diperiksa secara statis untuk struktur project, manifest, deep link pairing, permission overlay/foreground service, endpoint API dan state overlay. Lingkungan packaging Project Remote tidak memiliki Android SDK/device fisik, sehingga APK **belum dibangun di lingkungan packaging**. Build pertama dilakukan melalui Android Studio pada tahap certification.

Project menyertakan `gradle/wrapper/gradle-wrapper.properties` dengan Gradle 8.7. Jika Android Studio meminta komponen Gradle/SDK pada pembukaan pertama, izinkan Android Studio mengunduh komponen yang direkomendasikan. Jangan menaruh password keystore atau token pairing ke dalam source project.
