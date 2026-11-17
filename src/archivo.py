TAM_MB = 256          # tamano del archivo grande
ARCHIVO = "archivo_grande.txt"


def crear_archivo():
    print("\nCreando archivo de", TAM_MB, "MB...")
    n_lineas = TAM_MB * 1024 * 1024 // 64
    with open(ARCHIVO, "w", newline="\n") as f:
        for i in range(n_lineas):
            f.write(f"Linea {i:09d}: el SO mapea este archivo".ljust(63) + "\n")