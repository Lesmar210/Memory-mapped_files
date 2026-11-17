import mmap
import os
import random
import time

from archivo import ARCHIVO, crear_archivo

BLOQUE = 4096         # bytes que se leen cada vez
LECTURAS = 50000


def acceso_directo():
    with open(ARCHIVO, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        k = 1000000
        print("Linea", k, "->", mm[k * 64:(k + 1) * 64].decode().strip())
        mm.close()


def secuencial_read(posiciones):
    with open(ARCHIVO, "rb") as f:
        while True:
            datos = f.read(BLOQUE)
            if not datos:
                break


def secuencial_mmap(posiciones):
    with open(ARCHIVO, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        for i in range(0, len(mm), BLOQUE):
            datos = mm[i:i + BLOQUE]
        mm.close()


def aleatorio_read(posiciones):
    with open(ARCHIVO, "rb") as f:
        for pos in posiciones:
            f.seek(pos)
            datos = f.read(BLOQUE)


def aleatorio_mmap(posiciones):
    with open(ARCHIVO, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        for pos in posiciones:
            datos = mm[pos:pos + BLOQUE]
        mm.close()


def medir(funcion, posiciones):
    inicio = time.perf_counter()
    funcion(posiciones)
    return time.perf_counter() - inicio


def benchmark():
    print("\nPARTE 2: mmap vs read()")
    crear_archivo()
    acceso_directo()

    random.seed(42)
    n_bloques = os.path.getsize(ARCHIVO) // BLOQUE
    posiciones = [random.randrange(n_bloques) * BLOQUE for _ in range(LECTURAS)]

    pruebas = [
        ("Secuencial read()", secuencial_read),
        ("Secuencial mmap  ", secuencial_mmap),
        ("Aleatorio  read()", aleatorio_read),
        ("Aleatorio  mmap  ", aleatorio_mmap),
    ]

    print("\nPrueba              1a vez   2a vez   3a vez   (segundos)")
    for nombre, funcion in pruebas:
        t = [medir(funcion, posiciones) for _ in range(3)]
        print(f"{nombre}   {t[0]:.4f}   {t[1]:.4f}   {t[2]:.4f}")

    os.remove(ARCHIVO)