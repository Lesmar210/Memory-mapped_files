import argparse
import os
import tempfile

from archivo import crear_archivo
from benchmark import benchmark
from demo_basico import mmap_como_arreglo, page_faults


def main():
    ap = argparse.ArgumentParser(description="Demo mmap vs read()")
    ap.add_argument("--size-mb", type=int, default=512)
    ap.add_argument("--path", default=None)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    size = args.size_mb * 1024 * 1024
    path = args.path or os.path.join(tempfile.gettempdir(), "demo_mmap.bin")

    mmap_como_arreglo()

    crear_archivo(path, size)
    try:
        page_faults(path)
        benchmark(path, size)
    finally:
        if not args.keep and os.path.exists(path):
            os.remove(path)
            print(f"\nArchivo temporal borrado: {path}")


if __name__ == "__main__":
    main()