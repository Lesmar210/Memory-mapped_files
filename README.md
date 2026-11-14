# Memory-mapped_files
## Integrantes
- 323270258 - Aguilar Sánchez Carla Alexandra 
- N.Cuenta - Nombre
- N.Cuenta - Nombre
- 323274177 - Zacarias Guadalupe Leslie Marlene
  
## Objetivo  

El objetivo de este trabajo es mostrar cómo mapear un archivo al espacio de direcciones de un proceso para accederlo como un arreglo de bytes, y qué cambia frente a leerlo con read(). Además, se comparan los tiempos de acceso secuencial y aleatorio sobre un archivo grande, cuidando el efecto de la caché del sistema operativo, para identificar cuándo conviene mmap y cuándo read().

## Contexto y teoría
### ¿Que es mmap?
mmap (Memory-mapped files) es una llamada al sistema (system call) en sistemas operativos de tipo Unix/Linux que permite mapear (asociar) el contenido de un archivo directamente en el espacio de direcciones virtuales de un proceso. En lugar de leer un archivo utilizando los búferes tradicionales del sistema operativo y funciones iterativas, el archivo se proyecta de tal forma que leerlo o escribirlo equivale a interactuar directamente con un bloque de memoria RAM.

### ¿Qué significa mapear un archivo al espacio de direcciones virtuales de un proceso?
Significa que el sistema operativo asigna un rango de direcciones de memoria virtual dentro del proceso para que represente los bytes del archivo en disco. Cuando el proceso lee o escribe en esa dirección de memoria asignada, el kernel del sistema operativo se encarga automáticamente de sincronizar esos cambios con el archivo físico en disco en segundo plano, logrando que la memoria y el almacenamiento secundario trabajen como si fueran una sola entidad transparente.

### ¿Qué ventajas tiene acceder a un archivo como si fuera un arreglo de bytes?
- Simplicidad y naturalidad en el código: Permite manipular el archivo utilizando índices o operaciones de slicing (por ejemplo, buffer[0] o buffer[10:20]), eliminando la necesidad de escribir bucles complejos de lectura y escritura o llamadas repetitivas a read() y write().
- Eliminación de copias redundantes: En los métodos tradicionales de lectura (read), los datos se copian primero del disco al espacio de búfer del kernel y luego al espacio de memoria del usuario. Con mmap, el proceso accede directamente a la memoria donde el kernel cargó el archivo, evitando copias innecesarias de datos y mejorando la eficiencia.

### ¿Qué relación existe entre mmap, la memoria virtual y el sistema de archivos?
mmap es el puente directo entre estos tres componentes de la arquitectura del sistema operativo:

- Utiliza el sistema de archivos para localizar el archivo físico en disco y sus bloques correspondientes.
- Se apoya en el subsistema de memoria virtual para otorgarle al proceso un rango de direcciones y manejar la traducción de direcciones lógicas a físicas.
- Permite que el almacenamiento persistente (disco) y la memoria volátil (RAM) se entrelacen mediante la abstracción de bloques de datos.

## Demo

El programa se encuentra en un solo archivo de Python llamado `demo_mmap.py` y utiliza únicamente módulos de la biblioteca estándar: `mmap`, `os`, `random` y `time`. Su estructura está dividida en varias funciones para facilitar su comprensión y ejecución. La función principal, `main()`, se encarga de ejecutar dos partes: `demo_basico()` y `benchmark()`.

Al inicio del programa se definen algunas constantes que permiten establecer los parámetros de las pruebas:

1. `TAM_MB = 256`: establece el tamaño del archivo grande en megabytes.
2. `BLOQUE = 4096`: define el tamaño de los bloques que se leen en cada operación, equivalente a 4 KB.
3. `LECTURAS = 50000`: indica la cantidad de lecturas que se realizan durante las pruebas de acceso aleatorio.
4. `ARCHIVO = "archivo_grande.txt"`: especifica el nombre del archivo que se utiliza en las pruebas.

### Parte 1: uso de mmap como arreglo de bytes (`demo_basico`)

En esta primera parte se muestra cómo utilizar `mmap` para acceder al contenido de un archivo como si fuera un arreglo de bytes.

1. Primero, se crea un archivo pequeño que contiene una frase almacenada en formato binario (`"wb"`).
2. Después, se abre en modo `"r+b"`, que permite realizar operaciones de lectura y escritura.
3. Se crea el mapeo mediante `mmap.mmap(f.fileno(), 0)`, donde:
   - `f.fileno()` obtiene el descriptor del archivo abierto.
   - El valor `0` indica que se debe mapear el archivo completo.
4. Una vez creado el mapeo, se realizan algunas operaciones para observar cómo se puede manipular el contenido:
   - `len(mm)` permite conocer el tamaño del archivo.
   - `mm[0]` devuelve el primer byte como un número entero.
   - `mm[0:4]` permite obtener una parte del contenido.
   - `mm.find(b"mundo")` busca una palabra directamente dentro del archivo.
5. Posteriormente, se modifica una parte del contenido mediante `mm[0:4] = b"HOLA"`, mostrando que es posible escribir directamente sobre la región mapeada.
6. Se utiliza `mm.flush()` para solicitar que los cambios se reflejen en el archivo y `mm.close()` para liberar el mapeo.
7. Finalmente, se vuelve a abrir el archivo utilizando `read()` para comprobar que la modificación se guardó correctamente. Una vez terminada la prueba, el archivo se elimina.

### Creación del archivo grande (`crear_archivo`)

Para realizar las pruebas de rendimiento, se genera un archivo de texto de 256 MB con contenido ASCII.

1. El archivo se construye mediante líneas de exactamente 64 bytes.
2. Cada línea contiene un texto con un número consecutivo, seguido de una frase descriptiva. Se utiliza `ljust(63)` para completar el contenido con espacios y se agrega un salto de línea, obteniendo así los 64 bytes.
3. La cantidad de líneas se calcula dividiendo el tamaño total del archivo entre 64:
   `TAM_MB * 1024 * 1024 // 64`.
4. Al escribir el archivo se utiliza `newline="\n"` para mantener los saltos de línea con un solo byte, evitando que Windows los convierta y altere el tamaño esperado.
5. Se utiliza codificación ASCII para asegurar que cada carácter ocupe un byte. Esto permite calcular las posiciones dentro del archivo de manera sencilla y precisa.

### Acceso directo al archivo (`acceso_directo`)

Esta función permite mostrar cómo `mmap` facilita el acceso a una posición específica del archivo sin necesidad de recorrer previamente su contenido.

Como cada línea ocupa 64 bytes, la posición inicial de la línea `k` se obtiene multiplicando su número por 64 (`k * 64`).

Por ejemplo, para acceder a la línea 1,000,000, se utiliza una rebanada del mapeo:

`mm[k * 64:(k + 1) * 64]`

De esta manera, se obtiene directamente el contenido de esa línea, sin tener que leer todas las anteriores. Esto permite observar una de las principales ventajas de `mmap`: acceder a distintas partes de un archivo mediante sus posiciones en memoria.

### Parte 2: comparación entre mmap y read() (`benchmark`)

En esta segunda parte se realizan pruebas para comparar el rendimiento de `mmap` y `read()` al leer archivos de manera secuencial y aleatoria.

Se implementan cuatro funciones:

1. `secuencial_read`: lee el archivo desde el principio hasta el final, utilizando `f.read(BLOQUE)` dentro de un ciclo.
2. `secuencial_mmap`: recorre el archivo mapeado y obtiene bloques consecutivos mediante rebanadas (`mm[i:i + BLOQUE]`).
3. `aleatorio_read`: utiliza `f.seek(pos)` para desplazarse a una posición específica y después lee un bloque de 4 KB con `f.read(BLOQUE)`.
4. `aleatorio_mmap`: accede directamente a las posiciones indicadas mediante rebanadas del mapeo (`mm[pos:pos + BLOQUE]`).

Para las pruebas con `mmap` se utiliza `access=mmap.ACCESS_READ`, ya que en esta parte únicamente se necesita consultar el contenido del archivo.

**Condiciones para realizar una comparación justa**

Para que los resultados sean comparables, se consideran las siguientes condiciones:

1. Ambos métodos trabajan con bloques del mismo tamaño, es decir, 4 KB.
2. Las posiciones de las lecturas aleatorias se generan una sola vez utilizando `random.seed(42)`. Además, se seleccionan posiciones que sean múltiplos de 4096 mediante `random.randrange(n_bloques) * BLOQUE`.
3. De esta forma, tanto `read()` como `mmap` acceden exactamente a las mismas posiciones del archivo.
4. En cada operación, el bloque leído se asigna a una variable para que se realice el acceso a los datos.

**Medición de tiempos y efecto de la caché**

Para medir el rendimiento se utiliza la función `medir()`, que calcula el tiempo de ejecución de cada prueba mediante `time.perf_counter()`.

Cada prueba se ejecuta tres veces y los resultados se muestran en una tabla, donde cada fila representa una prueba y las columnas indican el tiempo obtenido en cada repetición.

Esta repetición también permite observar el efecto de la caché del sistema operativo. La primera ejecución puede tardar más porque algunos datos todavía no se encuentran en memoria, mientras que las siguientes pueden aprovechar los bloques que ya están almacenados en la caché.

Al finalizar todas las pruebas, se elimina el archivo grande para liberar el espacio utilizado.


## Analisis de resultados

## Paso a paso

## Conclusiones

## Referencias
- Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). Operating System Concepts (10th ed.). Wiley. (Capítulo sobre gestión de memoria virtual y mapeo de archivos).
- Linux Programmer's Manual. mmap(2) - Linux man page. Disponible en: https://man7.org/linux/man-pages/man2/mmap.2.html
- Python Software Foundation. mmap — Memory-mapped file support. Documentación oficial de Python. Disponible en: https://docs.python.org/3/library/mmap.html
