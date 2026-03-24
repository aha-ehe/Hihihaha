# Laporan Analisis Reverse Engineering `libmoba.so` (Bagian 4)
## Topik: C++ Move Logic, Hot-Update Patching, dan Keamanan Aset (Anti-Modding)

Pada sesi terakhir laporan analisis *deep dive* untuk library MOBA ini, kita membongkar 3 komponen krusial yang berhubungan langsung dengan pengalaman bermain (*Gameplay*) dan manajemen integritas aset di luar aspek jaringan server.

### 1. Pergerakan Karakter: C++ *vs* C# (`Java_com_moba_..._nativeSupportMoveLogic`)
Pernahkah Anda bertanya-tanya mengapa pergerakan hero pada game MOBA besar (seperti MLBB, HoK, AoV) terasa jauh lebih mulus, responsif, dan akurat dibandingkan dengan game MOBA *indie* buatan pemula di Unity?

Jawabannya terungkap dari pembedahan fungsi `Java_com_moba_unityplugin_UnityConfig_nativeSupportMoveLogic`:
```assembly
// Disassembly aarch64
a7c84: mov w0, #0x1  // Isi return (w0) dengan 1 (True)
a7c88: ret           // Return ke Java/C#
```
Fungsi di atas ini memberitahu Unity bahwa: *"Ya, game ini mendukung Native Move Logic!"*.

Dalam arsitektur Unity biasa, gerakan *joystick* diproses di dalam skrip `Update()` di C#. C# berjalan di atas *Garbage Collector*, yang berarti terkadang bisa terjadi *micro-stutter* (lag kecil milidetik) saat RAM dibersihkan, merusak presisi klik untuk menghindar dari *skill* lawan.

Pengembang game ini mengakalinya dengan membangun modul pergerakan **sepenuhnya di dalam C++ (Native)**. Unity hanya bertugas "menggambar" *(rendering)* dan mengirim sinyal analog ke C++. Di level C++ inilah posisi desimal Float (`x, y, z` dari Laporan ke-2) dikalkulasi ulang menggunakan algoritma prediksi murni *(client-side prediction)* sehingga pergerakan menjadi super *smooth* dan bebas dari anomali *garbage collection*.

### 2. Rahasia Download Tambahan yang Kecil (Sistem BSDiff & 7Zip)
Setiap game MOBA memiliki pembaruan besar. Jika developer mengandalkan update Google Play Store, pengguna harus mendownload ulang game berukuran Gigabyte.

Fungsi `BSPatch_PatchFile` di dalam `libmoba.so` adalah jawaban kenapa *update in-game* bisa berukuran sekecil 5MB.
```assembly
// Potongan fungsi BSPatch_PatchFile
bl fopen         // Membuka file Aset lama di disk
...
bl std::string::assign  // Melakukan validasi nama file
...
bl (loop penerapan patch BSDiff)
```
**Analisis Delta Patching:**
Game ini tidak mendownload aset *skin* atau model baru secara utuh. Jika ada *skin* yang dirilis dengan tambahan tekstur beberapa kilobyte, server akan membuat file `.patch` biner yang sangat kecil berisi perbedaan (*delta*) instruksi antara tekstur lama dan tekstur baru.
Saat pemain membuka game, `libmoba.so` akan mengunduh file *patch* ini, lalu menggunakan `BSPatch_PatchFile` untuk menambalnya secara otomatis ke dalam memori ponsel Anda, kemudian menyimpannya kembali tanpa mengganggu jalannya antarmuka (UI). Semuanya dikompresi kuat dengan pustaka `SevenZip` (LZMA) untuk memangkas *bandwidth* unduhan seminimal mungkin.

### 3. Keamanan File Lokal dan Anti-Cheat Sederhana
MOBA adalah mangsa empuk bagi *modder* (misalnya: membuat *Drone View*, *Skin Hack*, atau *Map Hack* dengan cara menimpa file aset asli dengan file aset transparan).

Game ini tidak mengandalkan keamanan tingkat Kernel Android, melainkan **File System Polling via C++**:
```assembly
// Disassembly IsAssetsFileExists
bl AAssetManager_open // Buka aset lewat NDK C++
cbz x0, <exit>        // Jika nol (tidak ada), tutup
bl AAsset_getLength   // Cek BESI/Ukuran Asli File
```
Langkah pertahanan mereka:
1. **Pemeriksaan via NDK:** Alih-alih mengecek file menggunakan fungsi Java `File.exists()`, yang sangat mudah dikelabuhi oleh alat semacam *Xposed Framework/Frida* karena berjalan di level *Dalvik/ART*, game memanggil fungsi `AAssetManager` dari NDK C++ yang jauh lebih tersembunyi.
2. **Validasi Panjang File:** Tidak cukup hanya memeriksa eksistensi file, ukuran file (`AAsset_getLength`) dicek. Jika *modder* memodifikasi file *shader* agar tembus pandang, ukurannya hampir pasti berubah.
3. **Penyapuan Hash:** Setelah file divalidasi dan dimuat, *buffer* file dilempar ke fungsi `MD5Update` atau `SHA1Update` yang mengkalkulasi sidik jari (Hash) memori tersebut dengan *checksum* rahasia yang dikirim dari server saat otentikasi.

### Kesimpulan Akhir Reverse Engineering `libmoba.so`
Melalui 4 laporan komprehensif ini, dapat disimpulkan bahwa *developer* game ini telah mendesain arsitektur *backend client* berstandar AAA (*Triple-A*). Mereka sukses membuat kerangka kerja *(framework)* yang memisahkan grafis Unity dari logika murni, mendelegasikan beban komputasi berat (Jaringan UDP/KCP, Serialisasi data Float murni SDP, Patching BSDiff, Prediksi gerak Native C++, dan File Hashing anti-mod) ke dalam *Native Shared Object* (`libmoba.so`) untuk efisiensi CPU ARM64 kelas *mobile*.