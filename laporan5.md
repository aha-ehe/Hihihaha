# Laporan Analisis Reverse Engineering `libmoba.so` (Bagian 5)
## Topik: Arsitektur Low-Level Jaringan Server-Client (TCP Fallback, KCP Tuning, & Heartbeat)

Sesi ke-5 dari analisis reverse engineering `libmoba.so` ini akan mengupas tuntas *"Jalan Tol"* atau infrastruktur jalur data yang menopang game. Komponen-komponen ini berfungsi di belakang layar dan sangat menentukan apakah seorang pemain akan mengalami "Lag/Patah-patah" atau bermain mulus dengan "Ping Hijau".

### 1. Sistem Keselamatan: TCP Fallback (`UdpPipeManager`)
Pada game MOBA modern, komunikasi data *gameplay* (seperti tembakan, langkah, dan status HP) murni dijalankan di atas **UDP** melalui protokol `KCP` karena UDP tidak membutuhkan proses *Handshake* dan tidak menunggu paket yang hilang sehingga bebas dari masalah antrean (*Head-of-Line Blocking*).

Namun, ada kelemahan UDP: **Beberapa WiFi Publik atau Provider Seluler (ISP) secara agresif memblokir *traffic* UDP yang tidak lazim**.

Game ini memiliki mekanisme pertahanan otomatis (Fallback) pada level *Native C++*.
- Berdasarkan *disassembly* di kelas `UdpPipeManager`, ketika soket mendeteksi *timeout* beruntun dalam `createNewRemoteUdp`, terdapat pemanggilan kondisi (berdasarkan evaluasi flag dan *state offset* `[x22, #268]`) yang akan segera menjalankan rutin:
  ```cpp
  UdpPipeManager::startConnectTcp(std::shared_ptr<PipeConnection>)
  ```
- **Analisis:** Jika UDP diblokir atau sinyal UDP terlalu banyak hilang *(Packet Loss tinggi)*, klien secara transparan dan otomatis akan menginisiasi socket TCP (`startConnectTcp`). Hal ini menjamin bahwa pemain yang bermain di jaringan restriktif (seperti WiFi Kampus/Kantor) masih dapat masuk ke dalam pertandingan, meski dengan risiko *delay* TCP biasa.

### 2. KCP Anti-Lag Tuning (Setelan Ekstrem)
`KCP` merupakan varian *Reliable UDP*. Keunggulannya adalah *developer* dapat mengatur tingkat ke-agresif-annya (*tuning*). Game yang berorientasi performa tinggi akan mengkonfigurasi KCP untuk membuang batas-batas efisiensi jaringan agar mendapatkan kecepatan murni.

Di dalam fungsi inisialisasi `mfw::ReliableUdp::init(mfw::ReliableUdp::KcpOptions const&)`, terjadi pemanggilan serangkaian pengaturan API dari pustaka `skywind3000/kcp`:
1. **`ikcp_nodelay`:** Fungsi ini dimuat dengan parameter agar algoritma Nagle dinonaktifkan (`nodelay=1`) dan interval timer dibuat sangat sempit (biasanya 10-20ms).
2. **`ikcp_wndsize`:** Menyetel besaran *Window Size* pengiriman dan penerimaan. Ini membolehkan *client* untuk menjejalkan puluhan paket ke dalam jaringan tanpa harus menunggu balasan (*ACK*) dari server.
3. **`ikcp_setmtu`:** Game mengatur Maximum Transmission Unit (MTU) KCP-nya, kemungkinan berada di rentang 1300-1400 bytes, yang lebih kecil dari MTU jaringan normal (1500) agar UDP ini bisa melewati berbagai macam lapisan *router* (VPN/NAT) tanpa perlu difragmentasi.

### 3. Deteksi Putus Koneksi (Heartbeat & Disconnect)
Bagaimana jika tiba-tiba listrik padam atau pemain menaiki lift (*loss signal*)?

Dalam rutin `UdpPipeManager::updateRUdpLoopTime`, `libmoba.so` selalu memelihara antrean *timer* presisi menggunakan:
```cpp
mfw::CTimeQueue<unsigned int, unsigned long>::add(...)
```
Fungsi ini adalah sistem *Watchdog* atau *Heartbeat*. Setiap kali siklus waktu (dalam milidetik) tercapai, aplikasi akan mendeteksi apakah *client* masih saling berkirim paket *ping/pong* dengan server.

Jika timer ini lewat batas (berarti data masuk terhenti selama beberapa detik), *client* akan memanggil `UdpPipeManager::sendDisconnectPacket(...)` dan `makeCmdDisconnect`. Fitur pemutus seketika *(immediate disconnect)* ini memberi tahu *game engine* Unity di lapisan atas agar langsung menampilkan logo *"Reconnecting..."* di layar, bukannya membiarkan karakter diam mematung tanpa status yang jelas.

### Kesimpulan Sesi 5
Infrastruktur transmisi pada game ini ditulis dengan sangat hati-hati pada bahasa C++. Menggunakan manajemen koneksi ganda (`UdpPipeManager` / TCP Fallback), setelan transmisi ekstrem (`ikcp_nodelay`), dan sinkronisasi waktu siklus jaringan (`CTimeQueue`), *developer* berhasil menjamin bahwa selama pemain memiliki kuota internet dengan rute *(routing)* minimal yang berfungsi, mereka tetap dapat bertanding.

Fitur *Reconnect* dan sinkronisasi UDP-nya diatur di tingkat soket *socket layer* murni untuk melewati hambatan Java GC dan OS *overhead*.