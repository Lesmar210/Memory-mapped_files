import mmap
import os
import tempfile

from archivo import PAGE, faults, info_archivo, vaciar_cache


def mmap_como_arreglo():
    print("\n=== mmap como arreglo de bytes ===")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Hola, mundo mapeado en memoria!" + b"\x00" * (PAGE - 31))
        path = tmp.name

    with open(path, "r+b") as f:
        with mmap.mmap(f.fileno(), 0) as mm:
            print(f"Tamano del mapeo : {len(mm)} bytes")
            print(f"Primeros bytes   : {mm[:31]!r}")
            print(f"Byte 0           : {mm[0]}")
            mm[0:4] = b"HOLA"
            mm.flush()

    with open(path, "rb") as f:
        print(f"Releido con read(): {f.read(31)!r}")
    os.remove(path)


def page_faults(path):
    print("\n=== Mapeo y page faults ===")
    info_archivo(path)

    n = 1000
    with open(path, "rb") as f:
        vaciar_cache(path)
        min0, maj0 = faults()
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        min1, maj1 = faults()
        print(f"\nDespues de mmap()        : minor={min1 - min0}, major={maj1 - maj0}")

        for i in range(n):
            _ = mm[i * PAGE]
        min2, maj2 = faults()
        print(f"Al tocar {n} paginas     : minor={min2 - min1}, major={maj2 - maj1}")

        for i in range(n):
            _ = mm[i * PAGE]
        min3, maj3 = faults()
        print(f"Al releer esas {n}       : minor={min3 - min2}, major={maj3 - maj2}")
        mm.close()