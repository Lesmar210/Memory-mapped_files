import mmap
import os
import random
import time
import zlib

from archivo import BLOCK, PAGE, faults, vaciar_cache

SEQ_CHUNK = 64 * 1024
N_RANDOM = 20_000
SEED = 42


def seq_read(path):
    crc = 0
    with open(path, "rb", buffering=0) as f:
        while True:
            b = f.read(SEQ_CHUNK)
            if not b:
                break
            crc = zlib.crc32(b, crc)
    return crc


def seq_mmap(path):
    crc = 0
    with open(path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            if hasattr(mm, "madvise") and hasattr(mmap, "MADV_SEQUENTIAL"):
                mm.madvise(mmap.MADV_SEQUENTIAL)
            for off in range(0, len(mm), SEQ_CHUNK):
                crc = zlib.crc32(mm[off:off + SEQ_CHUNK], crc)
    return crc


def rand_read(path, offsets):
    crc = 0
    fd = os.open(path, os.O_RDONLY)
    try:
        for off in offsets:
            crc = zlib.crc32(os.pread(fd, BLOCK, off), crc)
    finally:
        os.close(fd)
    return crc


def rand_mmap(path, offsets):
    crc = 0
    with open(path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            if hasattr(mm, "madvise") and hasattr(mmap, "MADV_RANDOM"):
                mm.madvise(mmap.MADV_RANDOM)
            for off in offsets:
                crc = zlib.crc32(mm[off:off + BLOCK], crc)
    return crc


def medir(nombre, fn, resultados):
    min0, maj0 = faults()
    t0 = time.perf_counter()
    check = fn()
    dt = time.perf_counter() - t0
    min1, maj1 = faults()
    resultados.append((nombre, dt, min1 - min0, maj1 - maj0, check))


def imprimir(titulo, resultados):
    print(f"\n--- {titulo} ---")
    print(f"{'metodo':<26}{'tiempo (s)':>12}{'minor flt':>12}{'major flt':>12}")
    for nombre, dt, mi, ma, _ in resultados:
        print(f"{nombre:<26}{dt:>12.3f}{mi:>12}{ma:>12}")
    if len(resultados) == 2 and resultados[0][4] != resultados[1][4]:
        print("ATENCION: los checksums no coinciden")


def escenario(path, offsets, tipo, fria):
    res = []
    if fria:
        vaciar_cache(path)
    if tipo == "seq":
        medir("read() chunks 64 KiB", lambda: seq_read(path), res)
    else:
        medir("pread() 4 KiB", lambda: rand_read(path, offsets), res)
    if fria:
        vaciar_cache(path)
    if tipo == "seq":
        medir("mmap (MADV_SEQUENTIAL)", lambda: seq_mmap(path), res)
    else:
        medir("mmap (MADV_RANDOM)", lambda: rand_mmap(path, offsets), res)
    return res


def benchmark(path, size_bytes):
    print("\n=== Benchmark mmap vs read() ===")
    print(f"Pagina del SO: {PAGE} bytes | lecturas aleatorias: {N_RANDOM} x {BLOCK} bytes")

    rng = random.Random(SEED)
    max_page = (size_bytes - BLOCK) // PAGE
    offsets = [rng.randint(0, max_page) * PAGE for _ in range(N_RANDOM)]

    if not vaciar_cache(path):
        print("AVISO: este SO no soporta posix_fadvise; la cache fria no es confiable.")

    imprimir("SECUENCIAL - cache fria", escenario(path, offsets, "seq", True))
    imprimir("ALEATORIO  - cache fria", escenario(path, offsets, "rand", True))

    seq_read(path)
    imprimir("SECUENCIAL - cache caliente", escenario(path, offsets, "seq", False))
    imprimir("ALEATORIO  - cache caliente", escenario(path, offsets, "rand", False))