import mmap
import os


def demo_basico():
    print("PARTE 1: mmap como arreglo de bytes")

    with open("pequeno.txt", "wb") as f:
        f.write(b"Hola mundo desde un archivo mapeado a memoria")

    with open("pequeno.txt", "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        print("Tamano:", len(mm), "bytes")
        print("mm[0]:", mm[0])
        print("mm[0:4]:", mm[0:4])
        print("find 'mundo':", mm.find(b"mundo"))
        mm[0:4] = b"HOLA"
        mm.flush()
        mm.close()

    with open("pequeno.txt", "rb") as f:
        print("Leido con read():", f.read())
    os.remove("pequeno.txt")