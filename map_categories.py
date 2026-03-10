import sys

def categorize():
    with open('exported_symbols.txt', 'r') as f:
        lines = f.readlines()

    categories = {
        'JNI / Java Interfaces': [],
        'KCP & Reliable UDP (Network)': [],
        'LUA Bindings': [],
        'SDP (Serialization Data Protocol)': [],
        'Compression (LZ4 / Zlib)': [],
        'Hashing & Crypto (MD5 / SHA1)': [],
        'File & Asset Management': [],
        'MOBA Game Logic & Utilities': [],
        'Other': []
    }

    for line in lines:
        if ' U ' in line: continue
        name = line.split(' ', 2)[-1].strip()
        if 'JNI' in name or 'Java_' in name or 'GetJNIEnv' in name:
            categories['JNI / Java Interfaces'].append(name)
        elif 'KCP' in name or 'ikcp' in name or 'ReliableUdp' in name or 'UdpPipe' in name or 'PipeConnection' in name:
            categories['KCP & Reliable UDP (Network)'].append(name)
        elif 'Lua' in name or 'lua_' in name:
            categories['LUA Bindings'].append(name)
        elif 'Sdp' in name or 'SDP' in name:
            categories['SDP (Serialization Data Protocol)'].append(name)
        elif 'LZ4' in name or 'zlib' in name or 'compress' in name.lower():
            categories['Compression (LZ4 / Zlib)'].append(name)
        elif 'MD5' in name or 'SHA1' in name or 'XXH' in name:
            categories['Hashing & Crypto (MD5 / SHA1)'].append(name)
        elif 'Asset' in name or 'File' in name or 'Patch' in name or 'bsdiff' in name or 'SevenZip' in name:
            categories['File & Asset Management'].append(name)
        elif 'MOBA' in name or 'Unity' in name:
            categories['MOBA Game Logic & Utilities'].append(name)
        else:
            # We skip standard C++ library for brevity in summary, but count them
            categories['Other'].append(name)

    for cat, items in categories.items():
        if cat != 'Other':
            print(f"### {cat} ({len(items)} functions)")
            for item in items[:5]: # Show max 5 examples
                print(f"  - {item}")
            if len(items) > 5:
                print(f"  - ... and {len(items)-5} more")

categorize()
