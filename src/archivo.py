import mmap
import os
import resource

PAGE = mmap.PAGESIZE
BLOCK = 4096


def crear_archivo(path, size_bytes):
    print(f"Creando {path} ({size_bytes / 2**20:.0f} MiB)...")
    chunk = os.urandom(1024 * 1024)
    with open(path, "wb") as f:
        escritos = 0
        while escritos < size_bytes:
            n = min(len(chunk), size_bytes - escritos)
            f.write(chunk[:n])
            escritos += n
        f.flush()
        os.fsync(f.fileno())


def vaciar_cache(path):
    if not hasattr(os, "posix_fadvise"):
        return False
    fd = os.open(path, os.O_RDONLY)
    try:
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)
    try:
        if os.geteuid() == 0:
            os.sync()
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3\n")
    except (AttributeError, OSError):
        pass
    return True


def faults():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_minflt, r.ru_majflt


def info_archivo(path):
    st = os.stat(path)
    print(f"Inodo               : {st.st_ino}")
    print(f"Tamano              : {st.st_size} bytes")
    print(f"Tamano de bloque FS : {st.st_blksize} bytes")
    print(f"Bloques asignados   : {st.st_blocks} (de 512 bytes)")
    print(f"Tamano de pagina SO : {PAGE} bytes")
    print(f"Paginas del archivo : {st.st_size // PAGE}")