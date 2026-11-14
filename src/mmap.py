import mmap
import os
import random
import time

TAM_MB = 256          # tamano del archivo grande
BLOQUE = 4096         # bytes que se leen cada vez
LECTURAS = 50000
ARCHIVO = "archivo_grande.txt"


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


def crear_archivo():
    print("\nCreando archivo de", TAM_MB, "MB...")
    n_lineas = TAM_MB * 1024 * 1024 // 64
    with open(ARCHIVO, "w", newline="\n") as f:
        for i in range(n_lineas):
            f.write(f"Linea {i:09d}: el SO mapea este archivo".ljust(63) + "\n")


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


def main():
    demo_basico()
    benchmark()


if __name__ == "__main__":
    main()