# Isolate Sandbox - To'liq Qo'llanma

## Isolate nima?

Isolate - bu dasturlash musobaqalari (IOI, ICPC) uchun maxsus ishlab chiqilgan sandbox muhiti. U ishonchsiz kodlarni xavfsiz bajarish imkonini beradi va quyidagi cheklovlarni qo'yadi:
- Vaqt cheklovi (time limit)
- Xotira cheklovi (memory limit)
- Fayl tizimiga kirish
- Tarmoq kirishi
- Jarayonlar soni

## O'rnatish

### 1. Talablar
```bash
sudo apt-get update
sudo apt-get install -y gcc make pkg-config libcap-dev libsystemd-dev
```

### 2. Manba koddan o'rnatish
```bash
# Repositoriyani klonlash
git clone https://github.com/ioi/isolate.git
cd isolate

# Kompilyatsiya qilish
make isolate

# O'rnatish (root huquqlari kerak)
sudo make install

# Konfiguratsiya faylini yaratish
sudo make CONFIG
```

### 3. Debian/Ubuntu paketidan o'rnatish
```bash
# Repozitoriy kalitini o'rnatish
sudo mkdir -p /etc/apt/keyrings
curl https://www.ucw.cz/isolate/debian/signing-key.asc | sudo tee /etc/apt/keyrings/isolate.asc

# Repozitoriyni qo'shish
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/isolate.asc] http://www.ucw.cz/isolate/debian/ bookworm-isolate main" | sudo tee /etc/apt/sources.list.d/isolate.list

# O'rnatish
sudo apt update
sudo apt install isolate
```

## Asosiy buyruqlar

### Sandbox yaratish
```bash
# Box yaratish (0-999 oralig'ida ID)
isolate --box-id=0 --init

# Box yo'lini ko'rish
isolate --box-id=0 --init
# Output: /var/local/lib/isolate/0/box
```

### Fayllarni sandbox'ga ko'chirish
```bash
# C++ dasturini sandbox'ga joylashtirish
cp solution.cpp /var/local/lib/isolate/0/box/

# Yoki --dir parametri bilan
isolate --box-id=0 --dir=/etc:noexec --run -- /bin/ls
```

### Dasturni kompilyatsiya qilish
```bash
isolate --box-id=0 \
    --time=10 \
    --wall-time=20 \
    --mem=262144 \
    --run -- /usr/bin/g++ -O2 -std=c++17 solution.cpp -o solution
```

### Dasturni bajarish
```bash
isolate --box-id=0 \
    --time=1 \
    --wall-time=2 \
    --mem=262144 \
    --stdin=input.txt \
    --stdout=output.txt \
    --stderr=error.txt \
    --meta=meta.txt \
    --run -- ./solution
```

### Sandbox'ni tozalash
```bash
isolate --box-id=0 --cleanup
```

## Muhim parametrlar

### Vaqt cheklovlari
- `--time=<seconds>` - CPU vaqti (soniyada)
- `--wall-time=<seconds>` - Real vaqt (soniyada)
- `--extra-time=<seconds>` - Qo'shimcha vaqt (default: 1s)

### Xotira cheklovlari
- `--mem=<kilobytes>` - Xotira limiti (KB)
- `--stack=<kilobytes>` - Stack hajmi (default: unlimited)

### Jarayonlar
- `--processes=<count>` - Maksimal jarayonlar soni
- `--processes` (qiymatsiz) - Bir nechta jarayonga ruxsat berish

### Kiritish/Chiqarish
- `--stdin=<file>` - Standart kirish
- `--stdout=<file>` - Standart chiqish
- `--stderr=<file>` - Xato chiqishi
- `--stderr-to-stdout` - Xatolarni stdout ga yo'naltirish

### Fayl tizimi
- `--dir=<path>:<options>` - Qo'shimcha kataloglarni ulash
  - Options: `rw` (o'qish/yozish), `ro` (faqat o'qish), `noexec` (bajarish yo'q)
- `--chdir=<path>` - Ishchi katalogni o'zgartirish

### Meta ma'lumotlar
- `--meta=<file>` - Natija statistikasini saqlash fayli

## To'liq dastur namunasi

### 1. C++ dasturni test qilish

```bash
#!/bin/bash

BOX_ID=0
TIME_LIMIT=1
MEMORY_LIMIT=262144  # 256 MB in KB

# Sandbox'ni yaratish
isolate --box-id=$BOX_ID --init

# Box yo'lini olish
BOX_DIR=$(isolate --box-id=$BOX_ID --init)

# Dasturni ko'chirish
cp solution.cpp $BOX_DIR/solution.cpp
cp input.txt $BOX_DIR/input.txt

# Kompilyatsiya
isolate --box-id=$BOX_ID \
    --time=10 \
    --wall-time=20 \
    --mem=524288 \
    --stderr=compile_error.txt \
    --run -- /usr/bin/g++ -O2 -std=c++17 solution.cpp -o solution

if [ $? -eq 0 ]; then
    echo "Kompilyatsiya muvaffaqiyatli!"
    
    # Bajarish
    isolate --box-id=$BOX_ID \
        --time=$TIME_LIMIT \
        --wall-time=$((TIME_LIMIT * 2)) \
        --mem=$MEMORY_LIMIT \
        --stdin=input.txt \
        --stdout=output.txt \
        --stderr=runtime_error.txt \
        --meta=meta.txt \
        --run -- ./solution
    
    RESULT=$?
    
    # Natijalarni ko'rish
    cat $BOX_DIR/output.txt
    echo ""
    echo "Meta ma'lumotlar:"
    cat meta.txt
    
    # Natijani tahlil qilish
    if [ $RESULT -eq 0 ]; then
        echo "Status: OK"
    elif [ $RESULT -eq 1 ]; then
        echo "Status: Runtime Error"
    elif [ $RESULT -eq 2 ]; then
        echo "Status: Time Limit Exceeded"
    fi
else
    echo "Kompilyatsiya xatosi!"
    cat compile_error.txt
fi

# Tozalash
isolate --box-id=$BOX_ID --cleanup
```

### 2. Python dasturni test qilish

```bash
#!/bin/bash

BOX_ID=1

# Sandbox yaratish
isolate --box-id=$BOX_ID --init
BOX_DIR=$(isolate --box-id=$BOX_ID --init)

# Python dasturini ko'chirish
cp solution.py $BOX_DIR/solution.py
cp input.txt $BOX_DIR/input.txt

# Bajarish
isolate --box-id=$BOX_ID \
    --time=2 \
    --wall-time=5 \
    --mem=262144 \
    --stdin=input.txt \
    --stdout=output.txt \
    --meta=meta.txt \
    --run -- /usr/bin/python3 solution.py

# Natijani ko'rish
cat $BOX_DIR/output.txt

# Tozalash
isolate --box-id=$BOX_ID --cleanup
```

### 3. Meta faylini tahlil qilish

```python
def parse_meta(meta_file):
    """Meta fayldan ma'lumotlarni o'qish"""
    meta = {}
    with open(meta_file, 'r') as f:
        for line in f:
            key, value = line.strip().split(':', 1)
            meta[key] = value
    return meta

# Misol:
meta = parse_meta('meta.txt')
print(f"Vaqt: {meta.get('time', 'N/A')} s")
print(f"Xotira: {meta.get('cg-mem', 'N/A')} KB")
print(f"Status: {meta.get('status', 'N/A')}")
print(f"Exit kod: {meta.get('exitcode', 'N/A')}")
```

## Meta fayl ma'lumotlari

Meta faylda quyidagi ma'lumotlar bo'ladi:
- `time` - CPU vaqti (soniyada)
- `time-wall` - Real vaqt (soniyada)
- `max-rss` - Maksimal xotira (KB)
- `cg-mem` - Control group xotirasi (KB)
- `status` - Status (RE, SG, TO, XX)
  - `RE` - Runtime Error
  - `SG` - Signal (masalan, SIGSEGV)
  - `TO` - Time Out
  - `XX` - Internal Error
- `exitcode` - Chiqish kodi
- `exitsig` - Signal raqami
- `killed` - O'ldirish signali
- `message` - Xato xabari

## Xavfsizlik sozlamalari

### Tarmoqni o'chirish
```bash
isolate --box-id=0 --share-net=0 --run -- ./solution
```

### Faqat kerakli kataloglarni ulash
```bash
isolate --box-id=0 \
    --dir=/etc:noexec \
    --dir=/usr:noexec \
    --dir=/lib:noexec \
    --dir=/lib64:noexec \
    --run -- ./solution
```

### Jarayonlarni cheklash
```bash
# Faqat bitta jarayon
isolate --box-id=0 --processes=1 --run -- ./solution

# Jarayonlarni butunlay taqiqlash
isolate --box-id=0 --processes --run -- ./solution
```

## Muammolar va yechimlar

### 1. Permission denied
```bash
# isolate ni root sifatida o'rnatganligingizga ishonch hosil qiling
sudo make install
```

### 2. Box already exists
```bash
# Avval cleanup qiling
isolate --box-id=0 --cleanup
isolate --box-id=0 --init
```

### 3. Memory limit oshdi
```bash
# cgroup uchun swap ni o'chirish kerak
# /etc/default/grub faylida:
# GRUB_CMDLINE_LINUX="swapaccount=1"
sudo update-grub
sudo reboot
```

### 4. Katalog topilmadi
```bash
# Box katalogini to'g'ri ko'rsating
BOX_DIR=$(isolate --box-id=0 --init | grep -oP '/var/local/lib/isolate/\d+/box')
echo $BOX_DIR
```

## Foydali havolalar

- [Official Documentation](http://www.ucw.cz/isolate/isolate.1.html)
- [Isolate Design Paper](https://mj.ucw.cz/papers/isolate.pdf)
- [GitHub Repository](https://github.com/ioi/isolate)
- [CMS - Contest Management System](https://github.com/cms-dev/cms)

## Qo'shimcha maslahatlar

1. **Har bir test uchun alohida box ishlatish** - Bir vaqtning o'zida bir nechta test ishlatish uchun turli box-id lar ishlatish mumkin (0-999 oralig'ida)

2. **Kompilyatsiya va bajarishni ajratish** - Kompilyatsiya uchun ko'proq vaqt va xotira ajrating

3. **Meta faylni doim ishlating** - Qanday xato yuz berganini aniqlash uchun meta fayl juda foydali

4. **Fayllarni nisbiy yo'l bilan kiriting** - `--chdir=/box` parametrini ishlating

5. **Xavfsizlik uchun minimal ruxsatlar bering** - Faqat kerakli kataloglarni `ro` (read-only) rejimida ulang