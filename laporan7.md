# Laporan Analisis Reverse Engineering `libmoba.so` (Bagian 7 / Ekstra)
## Topik: Analisis Teoritis Pembuatan Skrip Eksternal (Bot/Eksploitasi Jaringan)

Pada laporan tambahan ini, kita membahas hasil penyelidikan terhadap ide untuk "mengintervensi pertandingan dengan skrip pihak ketiga (misalnya Python) di luar APK". Berdasarkan *reverse engineering* pada file `libmoba.so`, kita akan mengevaluasi mengapa hal ini hampir **mustahil dilakukan secara stabil tanpa modifikasi klien (*Client-Modding*)**.

Terdapat 4 rintangan teknis atau mekanisme pertahanan yang diungkap oleh kode aslinya:

### Rintangan 1: Absennya Fungsi Otentikasi (Handshake & Session Token)
Kami mencoba mencari fungsionalitas pembuatan *Sesi Pertandingan* (seperti `Login`, `Auth`, `Token`, `Handshake`) di dalam `libmoba.so`.
- **Hasil Disassembly:** Tidak ada satupun fungsi tingkat rendah yang menangani *handshake* otentikasi.
- **Analisis Teoritis:** Aplikasi memisahkan tanggung jawabnya dengan ketat. Pembuatan *Session Token* (*Matchmaking*) diselesaikan melalui HTTPS (TCP) oleh *engine* Unity (C#) atau Android (Java). Setelah mendapat IP server, *Port*, dan *Secret Token*, barulah C# Unity menyerahkan parameter tersebut ke `libmoba.so` untuk membuka soket UDP via KCP.
- **Konsekuensi Eksploitasi:** Sebuah skrip Python di luar aplikasi tidak akan pernah mengetahui *Secret Token* pertempuran secara otomatis kecuali ia berhasil meniru seluruh proses otentikasi REST API game tersebut, yang mana dilindungi kuat oleh enkripsi SSL/TLS.

### Rintangan 2: Checksum Header 6-Byte Kustom
Di `laporan3.md`, kita menemukan fungsi `encodePacket` menyisipkan 6-byte *header*. Pada penelusuran lebih lanjut di alamat `0xccfc8` s/d `0xccfe0`:
```assembly
bfi w8, w9, #6, #26  // Operasi Bitfield Insert (Bitwise)
strb w8, [x19]       // Menyimpan byte konfigurasi
add w8, w23, #0x6    // Menambahkan panjang Payload + 6
```
- **Analisis Teoritis:** Operasi pergeseran dan penyisipan *Bitwise* (`bfi`) digunakan untuk menyandikan *flag* ukuran dan kompresi. Namun, 6 byte ini juga harus selaras dengan panjang paket dan algoritma LZ4/Zlib. Jika skrip Python mencoba "menembak" struktur ini tanpa meniru identik algoritma C++ tersebut, server KCP akan menolak paketnya karena dianggap korup di tingkat *UDP payload parser*.

### Rintangan 3: Sinkronisasi KCP (Sequence Number / `sn`)
UDP adalah protokol *stateless* (tanpa memori urutan). KCP dibangun untuk memberikan fitur *Sequence Number (sn)* agar setiap paket memiliki identitas urutan.
Dari pembedahan rutin `ikcp_send` (di sekitar alamat `0xceb40` - `0xcebc0`):
- KCP menghitung sisa memori MSS (*Maximum Segment Size*).
- Jika data `OperType_Battle_Move` besar, akan difragmentasi (*malloc* memori kecil) menjadi rantai *linked-list*.
- Setiap serpihan KCP ini diberi nilai `sn` (nomor urut).
- **Konsekuensi Eksploitasi:** Server melacak nilai `sn` dari HP Anda secara *real-time*. Jika skrip Python mencoba menyisipkan paket ke tengah-tengah pertempuran, nomor urut dari Python akan bertabrakan *(desync)* dengan nomor urut asli HP Anda. Server akan langsung melakukan operasi `makeCmdDisconnect` atau men-*drop* koneksi ganda tersebut. Mengakali ini mengharuskan peretas bertindak sebagai sistem *Man-in-the-Middle (MitM)* aktif, bukan sekadar "pengirim paket tambahan".

### Rintangan 4: Server-Side Authority (Anti-Teleport & Anti-Speed Hack)
Sebuah pencarian komprehensif untuk simbol terkait `Server` dan `Validation` di dalam *client library* ini memberikan hasil mutlak: **Nihil (0 hit)**.
- **Analisis Teoritis:** Game ini memiliki sifat arsitektur *Dumb Client* (Klien bodoh) di aspek legalitas gerakan. `libmoba.so` hanya bertugas mengirim `OperType_Battle_Move` berisi Float X, Y, Z. Tidak ada kode yang berbunyi `if (jarak_gerak > max_speed)`.
- **Konsekuensi Eksploitasi:** Jika Anda berhasil membuat *bot* Python yang mengirim paket Move palsu berjarak ribuan meter (Teleport Hack), *backend server* (yang memiliki peta navigasi asli) akan menolak jarak tersebut dan menarik paksa *(rubberbanding)* karakter Anda kembali ke posisi terakhir yang sah.

---
### Kesimpulan Eksekutif Laporan 7
Mengintervensi pertandingan (*live match*) dari aplikasi pihak ketiga (seperti skrip Python eksternal) berhadapan dengan barikade *Otentikasi Token*, sinkronisasi urutan KCP secara *real-time*, enkapsulasi bitwise yang spesifik, dan arsitektur *Server-Side Validation*.

Oleh karena itu, satu-satunya cara para peretas membuat *cheat* (*Map Hack* / *Auto-Aim*) adalah **bukan dengan membuat aplikasi luar yang bersaing dengan jaringan asli, melainkan dengan memodifikasi (Client-Modding/Hooking) file `libmoba.so` itu sendiri** saat berjalan di RAM ponsel (menggunakan *Frida*, *Xposed*, atau *Re-packed APK*) agar aplikasi asli yang secara sah melakukan semua pekerjaan jaringan tersebut.