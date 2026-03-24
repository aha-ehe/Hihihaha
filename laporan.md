# Laporan Analisis Reverse Engineering `libmoba.so`

## Informasi Berkas
- **Nama Berkas**: `libmoba.so`
- **Arsitektur**: ARM aarch64 (ELF 64-bit LSB shared object)
- **Framework Utama**: C++ & Android NDK (diindikasikan dengan `libandroid.so`, `liblog.so`, dll.)
- **Integrasi**: Unity Engine & Java (JNI)

## Pemetaan Kegunaan Secara Umum
Berdasarkan analisis pemetaan simbol (*exported symbols*) yang telah dilakukan, library ini adalah **library native / core logic** untuk game bergenre MOBA yang dibangun menggunakan **Unity**. Fungsinya difokuskan untuk menangani *backend logic* yang kritis secara performa dan jaringan, di luar *game engine* Unity itu sendiri.

Ini sangat umum dalam game multiplayer yang kompetitif seperti MOBA (misalnya Mobile Legends, Arena of Valor) karena operasi jaringan, serialisasi, dan optimasi bahasa pemrograman native (C/C++) jauh lebih efisien untuk mencegah latensi tinggi, memfasilitasi ukuran paket data sekecil mungkin, serta perlindungan dasar (obfuscation dari layer Java).

Berikut adalah pemetaan fungsi-fungsi di dalam file tersebut:

### 1. JNI / Java Interfaces (Penghubung Native - Java/Unity)
Fungsi-fungsi ini bertugas sebagai jembatan yang dipanggil oleh kode Java atau C# di Unity untuk mengeksekusi *core logic* pada library C++.
- `Java_com_moba_unityplugin_UnityConfig_nativeSupportMoveLogic`: Mengatur logika pergerakan (kemungkinan pergerakan analog/joystick atau prediksi gerakan) di sisi C++ agar lebih presisi.
- `Java_com_moba_unityplugin_NativeUtility_invokeFunctionSetAssetManager`: Mengelola Asset Manager Android langsung dari layer native untuk memuat aset file dengan performa maksimal.
- `MOBAJNI_Init`, `JNI_OnLoad`: Siklus hidup standar inisialisasi ketika game memuat `libmoba.so`.

### 2. KCP & Reliable UDP (Protokol Jaringan / Network)
Game MOBA sangat bergantung pada jaringan yang responsif (anti-lag). Library ini mengimplementasikan **KCP Protocol**, yaitu protokol berbasis UDP yang memberikan keandalan TCP namun dengan latensi yang jauh lebih rendah.
- *Fungsi Utama*: Terdapat lebih dari 160+ fungsi KCP dan implementasi `ReliableUDP` kustom, seperti:
  - `ikcp_create`, `ikcp_send`, `ikcp_recv`, `ikcp_update`: Core logic dari perpustakaan *skywind3000/kcp* standar.
  - `UdpPipeManager`: Manajer *socket* UDP yang terintegrasi (contoh: `getSocketBufSize`, `sendTcpData`, `readTcpData`) yang menandakan adanya *fallback* ke TCP jika UDP gagal.

### 3. LUA Bindings (Scripting & Hot-Update)
Lebih dari 280+ fungsi merujuk pada integrasi **Lua**. Dalam game mobile, Lua digunakan agar developer bisa memperbarui logika game (*hot-update*) tanpa perlu merilis *update* APK di Play Store.
- *Fungsi Utama*: `Lua_Open`, `Lua_Close`, `Lua2LuaC`. Selain itu ada juga konversi (*binding*) dari tipe data C++ ke Lua (`LuaSdpValue`, `LuaSdpStruct`, `LuaSdpMapReader`) sehingga Lua bisa membaca paket jaringan secara langsung.

### 4. SDP (Serialization Data Protocol)
Game kompetitif memerlukan ukuran *bandwidth* sekecil mungkin. Alih-alih menggunakan JSON atau XML, game ini menggunakan SDP (mirip dengan Protocol Buffers/Protobuf). Terdapat hampir 100 fungsi terkait ini.
- *Fungsi Utama*:
  - `SDP_NativeParseCastSkillOp`: Melakukan *parsing* paket ketika pemain *menggunakan skill* (Cast Skill Operation).
  - `SDP_NativeParseMoveOp`: Melakukan *parsing* paket ketika pemain *bergerak*.
  - `mfw::SdpUnpacker::unpackNumber`: Membaca paket biner yang masuk dari jaringan.

### 5. Kompresi (LZ4 & Zlib)
Paket yang dikirim ke server maupun file yang disimpan di lokal dikompres menggunakan LZ4 (yang sangat cepat untuk *realtime*) dan Zlib. Terdapat sekitar 109 fungsi terkait ini.
- *Fungsi Utama*: `LZ4_compress`, `LZ4_decompress_fast`, dan utilitas *wrapper* `mfw::UtilLZ4::lz4_compress` serta `zlib_compress`.

### 6. Hashing & Kriptografi
Untuk integritas data aset atau pengecekan *checksum* paket. Tidak ditemukan indikasi implementasi Anti-Cheat yang canggih (seperti ACE/Tencent Anti-Cheat), melainkan lebih ke validasi file dan enkripsi standar.
- *Fungsi Utama*: `MD5Init`, `SHA1Update`, dan `XXH32` (xxHash, sangat populer untuk mengecek *integrity* dengan sangat cepat di memory).

### 7. File, Asset Management & Patching
Library ini memiliki peran penting untuk menambal/memperbarui game (*Delta Patching*).
- *Fungsi Utama*:
  - `BSPatch_PatchFile` dan keluarga `bsdiff_*`: Digunakan untuk menggabungkan file `.apk` atau `.obb` lama dengan versi baru, sehingga ukuran *download update* pemain jadi sangat kecil.
  - `SevenZip_ExtractFile`: Menandakan game menggunakan arsip 7z (LZMA) untuk memampatkan aset gamenya.

### 8. Utilitas Game Lainnya
Fungsi-fungsi pembantu umum.
- `MOBA_GetLanguageString`, `MOBA_SetupRoleNameTable`, `MOBA_GetRandomRoleName`: Berfungsi mengambil string lokalisasi bahasa (untuk tampilan multi-bahasa) serta men-*generate* nama pemain secara acak.
- `MOBA_GetCPUArchitecture`: Deteksi arsitektur HP Android yang digunakan pemain.

## Kesimpulan
File `libmoba.so` adalah "Otak" (*Core Native Extension*) untuk sebuah game Unity. Pengembang mendelegasikan bagian-bagian terberat di dalam game—yaitu **Komunikasi Jaringan Realtime (UDP/KCP)**, **Parsing Paket (SDP)**, **Algoritma Pergerakan dan Skill**, serta **Sistem Hot-Update Aset (BSDiff/7Zip/Lua)**—ke bahasa C++ (*Native*) agar game dapat berjalan dengan performa terbaik dan *ping* sekecil mungkin di perangkat genggam/HP.