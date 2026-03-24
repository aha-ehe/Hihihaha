# Laporan Analisis Lanjutan Reverse Engineering `libmoba.so`
## Topik: Struktur Paket Jaringan (SDP - Serialization Data Protocol)

Melanjutkan analisis dari `laporan.md`, kita melakukan pendalaman (*deep dive*) terhadap protokol jaringan serialisasi yang digunakan oleh game ini, yaitu **SDP** (berada di namespace C++ `mfw::`). Pendekatan yang dilakukan adalah dengan mengekstrak dan menganalisis instruksi *Assembly ARM64* (Disassembly) dari fungsi pembongkar paket (*Unpacker*).

### Konsep Dasar SDP dalam Game ini
SDP bekerja dengan cara yang sangat mirip dengan Protocol Buffers (Protobuf). Setiap *field* (kolom data) dalam sebuah pesan dikenali melalui dua elemen:
1. **Tag/Index:** Nomor urut data (misalnya 0, 1, 2, 3).
2. **Tipe Data:** Jenis data (misalnya `float`, `unsigned int`, `double`, `string`).

Untuk menghemat *bandwidth* secara ekstrem, nama variabel (seperti "koordinat_x" atau "skill_id") tidak dikirimkan. Melalui *disassembly*, kita dapat memetakan kembali struktur paket berdasarkan urutan pemanggilan fungsi `unpack`.

---

### 1. Struktur Paket: Pergerakan Karakter (`mfw::OperType_Battle_Move`)
Berdasarkan analisis *disassembly* pada fungsi `mfw::OperType_Battle_Move::visit(mfw::SdpUnpacker, bool)`, game melakukan deserialisasi (unpack) data dengan pola sebagai berikut:

```assembly
// Potongan Assembly (pseudo)
bl mfw::SdpUnpacker::unpack(..., w1 = 0, float&)  // Membaca Index 0 -> Float
bl mfw::SdpUnpacker::unpack(..., w1 = 1, float&)  // Membaca Index 1 -> Float
bl mfw::SdpUnpacker::unpack(..., w1 = 2, float&)  // Membaca Index 2 -> Float
```

**Rekonstruksi Struktur (Pseudo-code C++):**
```cpp
struct OperType_Battle_Move {
    float x; // index 0
    float y; // index 1
    float z; // index 2
};
```
**Analisis:** Saat pemain menggunakan joystick/analog, game tidak mengirimkan input mentah (seperti arah "Atas" atau "Bawah"), melainkan langsung mengirimkan koordinat/vektor desimal (*float*) `X, Y, Z` tujuan atau rotasi pergerakan. Tiga nilai float = `3 x 4 bytes = 12 bytes` data mentah. Sangat kecil dan efisien.

---

### 2. Struktur Paket: Penggunaan Skill/Keahlian (`mfw::OperType_Battle_CastSkill`)
Berdasarkan analisis *disassembly* pada fungsi `mfw::OperType_Battle_CastSkill::visit(mfw::SdpUnpacker, bool)`, polanya sedikit berbeda dan lebih panjang:

```assembly
// Potongan Assembly (pseudo)
bl mfw::SdpUnpacker::unpack(..., w1 = 0, unsigned int&) // Membaca Index 0 -> Unsigned Int
bl mfw::SdpUnpacker::unpack(..., w1 = 1, float&)        // Membaca Index 1 -> Float
bl mfw::SdpUnpacker::unpack(..., w1 = 2, float&)        // Membaca Index 2 -> Float
bl mfw::SdpUnpacker::unpack(..., w1 = 3, float&)        // Membaca Index 3 -> Float
...
```

**Rekonstruksi Struktur (Pseudo-code C++):**
```cpp
struct OperType_Battle_CastSkill {
    unsigned int skillId; // index 0 (ID dari skill yang ditekan)
    float target_x;       // index 1
    float target_y;       // index 2
    float target_z;       // index 3
    // (diikuti kemungkinan data float lain untuk rotasi atau jarak)
};
```
**Analisis:** Ketika pemain menggunakan skill (terutama skill yang perlu diarahkan/ *aim*), game mengirimkan paket yang memuat **ID Skill** (bilangan bulat positif tak bertanda) dan setidaknya **tiga koordinat desimal** sasaran lemparan/cast.

---

### Kesimpulan Analisis Jaringan
1. **Zero-Overhead Serialization:** Protokol SDP pada game ini dioptimalkan sedemikian rupa agar tidak membawa *meta-data* berlebih, melainkan langsung ke *raw bytes* (Float 4 byte, Integer 4 byte) yang dikemas menggunakan KCP.
2. **Deterministic Lockstep / State Sync:** Fakta bahwa tipe operasi (*Operation Type*) dikategorikan dengan kelas-kelas spesifik seperti `Move` dan `CastSkill` yang sangat padat mengindikasikan kuat bahwa game ini berjalan menggunakan algoritma *Deterministic Lockstep* (atau varian *Server-Authoritative State Sync* yang ringkas) agar semua pemain di dalam *room* pertempuran melihat keadaan yang persis sama berdasarkan kalkulasi *float* presisi.