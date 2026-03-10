# Laporan Analisis Reverse Engineering `libmoba.so` (Bagian 6 / Final)
## Topik: Celah Tersembunyi (Debugging, Memory Management, Hash, & Hardware Profiling)

Di sesi penutup ini, kita menjelajahi area-area *niche* (ceruk) dari `libmoba.so` yang jarang tersentuh dalam operasi standar (kurang dari 15% logika tersisa). Detail-detail kecil ini memvalidasi bahwa aplikasi ini memiliki kelas arsitektur komersial kelas menengah-atas.

### 1. Sistem Pelacakan Jejak Terpusat (Trace Logging)
Dalam dunia pengembangan game, sangat lumrah jika log *debug* dihapus sepenuhnya di versi produksi *(Release)* untuk menghemat memori. Namun di `libmoba.so`:
- Fungsi `startJNICTraceRoute` dipanggil ketika ada error JNI.
- Ada pemanggilan `mainTracePath` untuk menyimpan rekaman ke dalam file lokal secara diam-diam.
**Kesimpulan:** Pengembang masih meninggalkan mekanisme *Crash Reporting/Tracing* bawaan C++ (*C-Trace Route*), mungkin agar jika ada eror JNI/NDK di peranti tertentu, gamenya dapat melempar data (crash dump) via fungsi `GetTraceLog` kepada pengembang. Bagi modder/hacker, file *trace* ini bisa menjadi sasaran empuk untuk membaca alur error game.

### 2. Pertahanan Melawan Memory Leak (LuaStackPoper)
Library C++ di game ini melakukan ribuan pertukaran paket LUA setiap menit (via `LuaSdpMapReader` dkk). Bagaimana agar RAM HP pemain tidak bocor (bengkak)?
- Melalui *disassembly* `LuaStackPoper::~LuaStackPoper()`, kita melihat rutinitas:
  ```cpp
  lua_settop(lua_State_pointer, -1) // -1 berarti pop/bersihkan tumpukan teratas
  ```
- **Analisis:** Menggunakan idiom C++ **RAII** (*Resource Acquisition Is Initialization*), objek pembantu LUA dibuat saat data diterima, dan ketika fungsi selesai (objek C++ dihancurkan), *destructor*-nya otomatis membersihkan tumpukan (`stack`) milik LUA C-API. Ini sangat ampuh menangkis *Memory Leak*.

### 3. Kriptografi: Standard vs Custom (MD5)
Banyak game memakai *Custom Hashing* (seperti Tencent) di mana nilai dasar inisialisasi Hash (`Magic Numbers`) mereka acak agar tak bisa diretas dengan kalkulator *Hash* gratisan.
- Melalui pembedahan `.rodata` (Read-Only Data) dari fungsi `MD5Init`:
  ```assembly
  01234567 89abcdef fedcba98 76543210
  ```
- **Fakta:** Game ini masih menggunakan algoritma MD5 yang **standar dan belum dimodifikasi** (Sesuai dengan RFC 1321). Gamenya menggunakan ini sekadar sebagai *"Checksum"* lokal biasa untuk mengecek keutuhan file, bukan untuk melindungi kerahasiaan payload tingkat tinggi (*Data Confidentiality*).

### 4. Profiling CPU yang "Licik" (`MOBA_GetCPUArchitecture`)
Fungsi `MOBA_GetCPUArchitecture` seolah-olah terlihat canggih di mana game mengumpulkan informasi mengenai chipset pemain. Namun, disassemblinya mengatakan hal lain:
- **Assembly:**
  ```assembly
  mov w0, #0x3  // Kembalikan angka 3
  ret
  ```
- **Kenyataannya:** Gamenya tidak membaca `/proc/cpuinfo` sama sekali! Karena `libmoba.so` ini di-*compile* murni hanya untuk arsitektur ARM64 (*aarch64*), pengembang malas membuat *profiler* dinamis dan langsung me-*hardcode* kembalian nilainya menjadi `3` (ID untuk ARM64 di beberapa skema platform). Ini adalah trik pengoptimalan yang "licik" namun masuk akal, menghemat beberapa siklus CPU saat *loading screen* Unity.

### Penutup Seluruh Eksplorasi
Laporan bagian ke-6 ini merangkum dan menutup eksplorasi kita terhadap `libmoba.so`. Melalui 6 tahap analisis mendalam, kita telah membedah:
1. Peta fungsionalitas game (Jaringan, SDP, LUA, JNI).
2. Format protokol SDP yang minim *overhead* (Float & Int).
3. Penggunaan KCP (UDP) berlapis *Header* 6-byte, TCP *Fallback*, tanpa Enkripsi berat.
4. *Offloading* kalkulasi C# (Unity) ke C++ untuk pergerakan pemain *anti-lag*.
5. Mekanisme *Delta Update/Patching* rahasia via BSDiff.
6. Penanganan memori *garbage-free* LUA dan Hardcoded Profiling.

File *shared object* ini adalah mahakarya efisiensi untuk arsitektur *Mobile Multiplayer*.