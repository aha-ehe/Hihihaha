# Laporan Analisis Reverse Engineering `libmoba.so` (Bagian 3)
## Topik: Mekanisme Keamanan dan Kompresi Jaringan (Reliable UDP & KCP)

Pada analisis sesi ketiga ini, fokus kita dialihkan dari "Apa isi data yang dikirim?" menjadi **"Bagaimana data tersebut dibungkus dan dilindungi saat melintasi jaringan internet?"**

Analisis difokuskan pada *disassembly* fungsi `mfw::ReliableUdp::encodePacket` dan `mfw::ReliableUdp::decodePacket`. Fungsi-fungsi ini adalah gerbang terakhir sebelum data game masuk ke dalam soket (`sendto` / `recvfrom`) via protokol KCP/UDP.

### Temuan Utama: Evolusi Header dan Kompresi Dinamis

#### 1. Pembatasan Ukuran dan Header (Threshold)
Game ini menerapkan pembatasan dinamis terhadap paket jaringan:
```assembly
cmp w8, #0x7   // Jika ukuran packet < 7 byte, abaikan/kembalikan error
sub w25, w8, #0x6  // Ukuran data aktual = Ukuran Packet - 6 Bytes (HEADER)
cmp w25, #0x40 // Cek apakah ukuran payload aktual >= 64 byte (0x40)
```
- **Kesimpulan 1:** Setiap paket yang keluar atau masuk dari server memiliki **Header Jaringan Kustom sebesar 6 Bytes** yang ditambahkan di atas data SDP (Serialization Data Protocol).
- **Kesimpulan 2:** Fungsi `encodePacket` dan `decodePacket` hanya melakukan operasi lanjutan (seperti kompresi) **hanya jika** ukuran data SDP (payload) bernilai 64 byte (`0x40`) atau lebih besar. Paket kecil seperti (Koordinat Move) yang ukurannya hanya belasan byte, **tidak akan dikompresi sama sekali** untuk menghemat siklus CPU *(Cycle Time)*.

#### 2. Mekanisme Kompresi (Conditional LZ4 vs Zlib)
Jika paket yang akan dikirim (contoh: paket besar seperti sinkronisasi state atau informasi profil pemain) melewati ukuran 64 byte, maka program akan mengecek *flag* kompresi yang ada pada konfigurasi *connection* (di-*load* dengan `ldrb w9, [x0, #28]`):
- **Jika Flag = 1:** Paket akan dikompres menggunakan `mfw::UtilLZ4::lz4_compress`. (Sangat cepat, cocok untuk Real-time Action).
- **Jika Flag != 1:** Paket akan dikompres menggunakan `mfw::UtilZlib::zlib_compress`. (Rasio kompresi lebih tinggi, cocok untuk data statis yang besar).

Ukuran *buffer* maksimum untuk kompresi/dekompresi telah dipatok sebesar `1048576 bytes` (1 MB) via register `mov w3, #0x100000`.

#### 3. Keamanan & Enkripsi (*The Surprising Fact*)
Dalam game kompetitif modern, biasanya pengembang menyelipkan *XOR Encryption* ringan atau algoritma simetris yang cepat (seperti *ChaCha20* atau *AES-NI*) untuk menghindari pembuatan program *Radar Hack* atau *Map Hack*.

Namun, dari pembongkaran instruksi fungsi encoding dan decoding `libmoba.so` ini, **tidak ditemukan** pemanggilan library enkripsi komersial, blok *XOR Cipher* manual, maupun algoritma hashing (*MD5/XXH32* pada layer `encodePacket`).

Ini berarti:
1. **Keamanan bertumpu pada Obfuscation SDP dan KCP:** Sulitnya men-*sniff* paket ini bukan karena paketnya di-enkripsi, melainkan karena protokol aslinya di-*layer* menggunakan dua algoritma (*wrapper*) berturut-turut:
   - **SDP:** Payload isinya hanya byte float/int murni tanpa metadata variabel.
   - **KCP Protocol:** KCP sendiri memiliki format paketnya sendiri (Segment Header) untuk *Reliable UDP*.
   Bagi *sniffer* jaringan awam seperti Wireshark, tumpukan *SDP* di dalam *KCP* akan terlihat seperti "sampah" / *garbage bytes* UDP biasa yang tidak ada maknanya.

### Kesimpulan Keseluruhan Jaringan Game
Arsitektur backend jaringan game ini dirancang **100% untuk performa maksimal dan ping serendah mungkin**. Pengembang menghindari enkripsi tingkat mesin yang memakan siklus instruksi CPU ARM yang berharga. Sebaliknya, mereka menerapkan batas cerdas:
- Jika ukuran <= 64 Byte (Operasi cepat seperti Move/Skill) -> Kirim *Raw Bytes* via KCP.
- Jika ukuran > 64 Byte (Data statis) -> Lakukan kompresi LZ4, baru dikirim.