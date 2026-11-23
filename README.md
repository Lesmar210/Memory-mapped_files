# Memory-mapped_files
## Integrantes
- 323270258 - Aguilar Sánchez Carla Alexandra 
- 323214478 - Ramriez Olvera Erick Yael
- 426059112 - Santiago Carreto Héctor
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

## Mecánica del SO: páginas, page faults y espacio de direcciones

### Espacio de direcciones virtual

Cada proceso ve su propio espacio de direcciones virtual, un rango de direcciones contiguas que no corresponde directamente a la RAM física. El sistema operativo, apoyado en el hardware (la MMU), traduce cada dirección virtual a una dirección física cuando el proceso accede a ella. Ese espacio se divide en regiones: código, datos, heap, pila, bibliotecas compartidas y **regiones mapeadas a archivos**.

Cuando llamamos a `mmap`, el kernel **no lee el archivo en ese momento**. Solo reserva un rango de direcciones virtuales nuevo en el proceso y anota que ese rango está respaldado por un archivo (en Linux, una estructura llamada VMA). El contenido llega a la RAM después, bajo demanda.

### Páginas y tabla de páginas

- La memoria virtual y la física se dividen en bloques de tamaño fijo llamados **páginas** (normalmente **4 KB = 4096 bytes**). En la memoria física a esos bloques se les llama *marcos* (frames).
- La **tabla de páginas** de cada proceso indica, para cada página virtual, en qué marco físico está y con qué permisos (lectura, escritura), o si todavía no está en memoria.
- El **TLB** es una caché pequeña dentro del procesador que guarda traducciones recientes para no consultar la tabla de páginas en cada acceso.
- La **caché de páginas** (page cache) es la memoria que el kernel usa para guardar bloques de archivos ya leídos. Tanto `read()` como `mmap` pasan por ella.

En nuestra demo, el archivo de 256 MB equivale a 256 × 1024 / 4 = **65,536 páginas**. Como `BLOQUE = 4096`, cada lectura de la prueba corresponde a exactamente una página, y las posiciones aleatorias son múltiplos de 4096, es decir, están alineadas a página.

### Page fault (fallo de página)

Un page fault ocurre cuando el proceso accede a una dirección virtual cuya página no tiene una traducción válida en la tabla de páginas. **No es un error**: es el mecanismo normal con el que funciona el mapeo bajo demanda. La CPU lanza una excepción y el kernel la atiende.

Flujo de un acceso con `mmap`:

1. El proceso hace `mm[pos:pos + BLOQUE]`, lo que accede a una dirección virtual dentro de la región mapeada.
2. La MMU consulta TLB y tabla de páginas. Si la página no está presente, se produce un **page fault** y el control pasa al kernel.
3. El kernel verifica que la dirección pertenezca a una región mapeada y que el acceso tenga permiso.
4. Busca la página del archivo en la caché de páginas:
   - **Fallo menor (minor fault):** la página ya está en la caché de páginas (por ejemplo, porque otra lectura la trajo antes). Solo hay que actualizar la tabla de páginas. Es rápido (del orden de microsegundos o menos).
   - **Fallo mayor (major fault):** la página no está en RAM. El kernel debe leerla del disco, esperar la E/S y luego enlazarla. Es mucho más lento (del orden de milisegundos en un disco, menos en SSD).
5. El kernel actualiza la tabla de páginas y reanuda la instrucción que falló. Para el proceso, el acceso simplemente funcionó.

Esto explica el comportamiento de las **tres repeticiones** de la prueba. En la 1ª vez, el archivo probablemente no está en la caché de páginas, así que hay fallos mayores. En la 2ª y 3ª vez, ya está en RAM y los accesos son mucho más baratos. Hay que tener en cuenta que `crear_archivo()` acaba de escribir el archivo, por lo que parte de él puede estar ya en caché incluso en la 1ª vez.

### Qué pasa con `read()`

1. El proceso llama `read()`, que es una **llamada al sistema**: cambia de modo usuario a modo kernel.
2. El kernel busca los bytes en la caché de páginas. Si no están, los lee del disco.
3. El kernel **copia** los datos de la caché de páginas al búfer del proceso (copia kernel → usuario).
4. Regresa a modo usuario.

Cada `read()` implica un cambio de modo y una copia. Con `mmap` no hay llamada al sistema por cada acceso, pero sí puede haber un page fault la primera vez que se toca cada página.

### Otros detalles relevantes

- **Lectura anticipada (readahead):** ante un patrón secuencial, el kernel lee páginas por adelantado. Esto favorece a ambos métodos en acceso secuencial y casi no ayuda en acceso aleatorio.
- **Escrituras y `flush()`:** al modificar una región mapeada, la página queda marcada como "sucia" y el kernel la escribe a disco más tarde. `mm.flush()` (que usa `msync`) fuerza esa sincronización. Por eso en `demo_basico()` se llama a `flush()` antes de cerrar.
- **Modo de acceso:** `ACCESS_READ` solo permite leer (intentar escribir produce un error). En `demo_basico()` se usa el modo por defecto, que permite lectura y escritura y refleja los cambios en el archivo.
- **Una limitación de Python:** una rebanada `mm[i:i + BLOQUE]` devuelve un objeto `bytes` nuevo, es decir, **hace una copia** hacia el heap del intérprete. Así, la ventaja de "cero copias" de `mmap` se reduce en esta demo. Con `memoryview(mm)[i:i + BLOQUE]` se evitaría esa copia. Esto conviene tenerlo presente al interpretar los tiempos.
- **Windows:** el concepto es el mismo, pero internamente se usan `CreateFileMapping` y `MapViewOfFile` en lugar de `mmap(2)`.

## Comparativa: `mmap` vs `read()`

| Criterio | `mmap` | `read()` |
|---|---|---|
| Mecanismo | Mapea el archivo al espacio de direcciones; la carga ocurre mediante page faults | Llamada al sistema que copia datos al búfer del usuario |
| Costo por acceso | Sin syscall por acceso; costo de page fault la primera vez que se toca una página | Una syscall (cambio de modo) por cada `read()` |
| Copias de datos | Accede a la caché de páginas sin copia intermedia (en Python, la rebanada sí copia) | Siempre copia de la caché del kernel al búfer del usuario |
| Acceso secuencial | Bueno, aprovecha readahead; muchos page faults menores | Muy bueno, readahead y pocas syscalls con bloques grandes |
| Acceso aleatorio | Muy bueno: basta con calcular la dirección, sin `seek` | Peor: requiere `seek()` + `read()` por cada acceso |
| Modelo de programación | El archivo se usa como arreglo de bytes (índices, rebanadas, `find`) | Flujo de bytes con posición actual |
| Archivos pequeños | Poco conveniente: el costo de crear y destruir el mapeo no se compensa | Más simple y eficiente |
| Archivos muy grandes | Útil: no hace falta cargar todo, solo se traen las páginas tocadas (limitado por el espacio de direcciones, sobre todo en 32 bits) | Útil si se lee por bloques |
| Latencia | Impredecible: cualquier acceso a memoria puede bloquearse por un fallo mayor | Más predecible: el bloqueo ocurre en la llamada a `read()` |
| Manejo de errores | Errores de E/S o archivo truncado se manifiestan como señales/excepciones al acceder a memoria (p. ej. `SIGBUS`) | Se reportan como valor de retorno o excepción en `read()` |
| Cambiar el tamaño del archivo | Complicado (hay que remapear) | Natural (`write`, `truncate`) |
| Compartir entre procesos | Varios procesos pueden mapear el mismo archivo y compartir las mismas páginas físicas | Cada proceso tiene su propia copia en su búfer |

### Criterios: cuándo conviene `mmap` y cuándo `read()`

**Conviene `mmap` cuando:**

1. Hay **muchos accesos aleatorios** a un archivo grande (bases de datos, índices, búsquedas).
2. El mismo archivo se **lee repetidamente** o por varios procesos, y se quiere aprovechar la caché y compartir páginas.
3. Se quiere un código más simple, tratando el archivo como un arreglo (`mm[a:b]`, `mm.find(...)`).
4. Se necesita compartir memoria entre procesos a través de un archivo.
5. El archivo cabe razonablemente en el espacio de direcciones del proceso.

**Conviene `read()` cuando:**

1. La lectura es **secuencial, de una sola pasada** (el readahead ya la hace eficiente y no hace falta el mapeo).
2. El archivo es **pequeño** o se lee una sola vez.
3. Se necesita **latencia predecible** o manejar errores de E/S de forma controlada.
4. El archivo **cambia de tamaño** durante el uso o se está escribiendo de forma incremental (logs, flujos).
5. El archivo no es regular, como una tubería (pipe), un socket o la entrada estándar: no se pueden mapear.

### Hipótesis a contrastar con el benchmark

Estas son las expectativas teóricas que el Integrante 4 puede verificar con la tabla de tiempos de `demo_mmap.py`:

- **Secuencial:** `read()` y `mmap` deberían dar tiempos similares. `read()` puede salir ligeramente mejor porque hace pocas syscalls y aprovecha bien el readahead.
- **Aleatorio:** `mmap` debería ser más rápido que `read()` en la 2ª y 3ª repetición, porque evita una syscall y un `seek` por cada una de las 50,000 lecturas.
- **Caché:** la 1ª repetición debería ser la más lenta en las pruebas que lean el archivo desde disco. Las siguientes deberían bajar y estabilizarse.
- Si los resultados no coinciden con estas hipótesis, hay que explicarlo (por ejemplo, por el efecto de la caché de Windows/Linux, por la copia que hace la rebanada de Python o por el búfer interno de `open()`).

## Demo

El programa se encuentra dividido en cuatro archivos de Python y utiliza únicamente módulos de la biblioteca estándar: `mmap`, `os`, `random`, `resource`, `tempfile`, `time`, `zlib` y `argparse`.

1. `main.py`: punto de entrada. Ejecuta en orden `mmap_como_arreglo()`, `crear_archivo()`, `page_faults()` y `benchmark()`.
2. `archivo.py`: constantes, creación del archivo grande, vaciado de caché, conteo de fallos de página e información del archivo (inodo y bloques).
3. `demo_basico.py`: contiene `mmap_como_arreglo()` y `page_faults()`.
4. `benchmark.py`: las cuatro funciones de lectura, la medición de tiempos y fallos, y las tablas de resultados.

Se definen algunas constantes que permiten establecer los parámetros de las pruebas:

1. `PAGE = mmap.PAGESIZE`: tamaño de página del sistema (normalmente 4096 bytes).
2. `BLOCK = 4096`: tamaño de cada lectura aleatoria, equivalente a 4 KB.
3. `SEQ_CHUNK = 64 * 1024`: tamaño de cada bloque en la lectura secuencial.
4. `N_RANDOM = 20_000`: cantidad de lecturas que se realizan en las pruebas de acceso aleatorio.
5. `SEED = 42`: semilla para generar siempre las mismas posiciones.

El tamaño del archivo grande es de 512 MB por defecto.

### Uso de mmap como arreglo de bytes (`mmap_como_arreglo`)

En esta primera parte se muestra cómo utilizar `mmap` para acceder al contenido de un archivo como si fuera un arreglo de bytes.

1. Primero, se crea un archivo temporal que contiene una frase almacenada en formato binario (`"wb"`), rellenada con ceros hasta completar una página.
2. Después, se abre en modo `"r+b"`, que permite realizar operaciones de lectura y escritura.
3. Se crea el mapeo mediante `mmap.mmap(f.fileno(), 0)`, donde:
   - `f.fileno()` obtiene el descriptor del archivo abierto.
   - El valor `0` indica que se debe mapear el archivo completo.
4. Una vez creado el mapeo, se realizan algunas operaciones para observar cómo se puede manipular el contenido:
   - `len(mm)` permite conocer el tamaño del mapeo.
   - `mm[:31]` devuelve los primeros bytes del contenido.
   - `mm[0]` devuelve el primer byte como un número entero.
   
5. Posteriormente, se modifica una parte del contenido mediante `mm[0:4] = b"HOLA"`, mostrando que es posible escribir directamente sobre la región mapeada.
6. Se utiliza `mm.flush()` para solicitar que los cambios se reflejen en el archivo, y el mapeo se cierra al salir del bloque `with`.
7. Finalmente, se vuelve a abrir el archivo utilizando `read()` para comprobar que la modificación se guardó correctamente. Una vez terminada la prueba, el archivo se elimina.

### Creación del archivo grande (`crear_archivo`)

Para realizar las pruebas de rendimiento, se genera un archivo grande con contenido aleatorio.

1. Se genera un bloque de 1 MB con datos aleatorios mediante `os.urandom`, para que el archivo no esté vacío ni pueda ser disperso (sparse).
2. Ese bloque se escribe repetidamente hasta alcanzar el tamaño del archivo (512 MB por defecto).
3. Al terminar se utilizan `flush()` y `os.fsync()` para asegurar que el contenido quedó en disco antes de medir.

### Información del archivo y page faults (`page_faults`)

Esta función permite observar qué hace el sistema operativo al mapear un archivo.

1. Imprime el inodo, el tamaño, el tamaño de bloque del sistema de archivos, los bloques asignados, el tamaño de página y la cantidad de páginas del archivo.
2. Vacía la caché del archivo y registra los fallos de página antes del mapeo.
3. Crea el mapeo con `ACCESS_READ` y vuelve a medir los fallos: esta cifra muestra el costo de reservar las direcciones, sin haber leído datos.
4. Toca 1000 páginas distintas (un byte por página) y mide los fallos que se generaron.
5. Vuelve a leer esas mismas 1000 páginas y mide los fallos: al estar ya mapeadas, no deberían aparecer fallos nuevos.

### Comparación entre mmap y read() (`benchmark`)

En esta segunda parte se realizan pruebas para comparar el rendimiento de `mmap` y `read()` al leer archivos de manera secuencial y aleatoria.

Se implementan cuatro funciones:

1. `seq_read`: lee el archivo desde el principio hasta el final, utilizando `f.read(SEQ_CHUNK)` dentro de un ciclo, sin búfer de Python.
2. `seq_mmap`: recorre el archivo mapeado y obtiene bloques consecutivos mediante rebanadas (`mm[i:i + SEQ_CHUNK]`), usando `MADV_SEQUENTIAL`.
3. `rand_read`: utiliza `os.pread(fd, BLOCK, pos)` para leer un bloque de 4 KB en una posición específica con una sola llamada al sistema.
4. `rand_mmap`: accede directamente a las posiciones indicadas mediante rebanadas del mapeo (`mm[pos:pos + BLOCK]`), usando `MADV_RANDOM`.

Para las pruebas con `mmap` se utiliza `access=mmap.ACCESS_READ`, ya que en esta parte únicamente se necesita consultar el contenido del archivo.

Cada función calcula un `zlib.crc32` de los datos leídos. Esto asegura que los bytes realmente se acceden y permite comprobar que `read()` y `mmap` leyeron exactamente lo mismo.

**Condiciones para realizar una comparación justa**

Para que los resultados sean comparables, se consideran las siguientes condiciones:

1. Ambos métodos trabajan con bloques del mismo tamaño: 64 KB en la lectura secuencial y 4 KB en la aleatoria.
2. Las posiciones de las lecturas aleatorias se generan una sola vez utilizando `random.Random(42)`. Además, se seleccionan posiciones que sean múltiplos de 4096.
3. De esta forma, tanto `read()` como `mmap` acceden exactamente a las mismas posiciones del archivo.
4. En cada operación se calcula el checksum del bloque leído, para que se realice el acceso a los datos.

**Medición de tiempos y efecto de la caché**

Para medir el rendimiento se utiliza la función `medir()`, que calcula el tiempo de ejecución de cada prueba mediante `time.perf_counter()` y registra los fallos de página menores y mayores ocurridos durante ella.

Para controlar el efecto de la caché del sistema operativo, cada prueba se ejecuta en dos condiciones:

1. **Caché fría:** antes de cada medición se saca el archivo de la caché de páginas con `os.posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)`. Así la lectura viene realmente del disco y aparecen fallos mayores.
2. **Caché caliente:** antes de medir se lee el archivo completo una vez, de modo que quede en RAM. Así se mide el costo del mecanismo sin la influencia del disco.

Los resultados se muestran en cuatro tablas (secuencial y aleatorio, cada uno con caché fría y caliente), donde cada fila representa un método y las columnas indican el tiempo, los fallos menores y los fallos mayores.

Al finalizar todas las pruebas, se elimina el archivo grande para liberar el espacio utilizado

## Analisis de resultados

Para ejecutar el proyecto se utilizó Python 3.14.4 a través de WSL con la distribución Ubuntu. Se consideró mejor opción para poder observar correctamente la interacción del programa con el sistema operativo.

Ejecutando main se obtiene: 

```
=== mmap como arreglo de bytes ===
Tamano del mapeo : 4096 bytes
Primeros bytes   : b'Hola, mundo mapeado en memoria!'
Byte 0           : 72
Releido con read(): b'HOLA, mundo mapeado en memoria!'
Creando /tmp/demo_mmap.bin (512 MiB)...

=== Mapeo y page faults ===
Inodo               : 27
Tamano              : 536870912 bytes
Tamano de bloque FS : 4096 bytes
Bloques asignados   : 1048576 (de 512 bytes)
Tamano de pagina SO : 4096 bytes
Paginas del archivo : 131072

Despues de mmap()        : minor=0, major=0
Al tocar 1000 paginas     : minor=64, major=0
Al releer esas 1000       : minor=0, major=0

=== Benchmark mmap vs read() ===
Pagina del SO: 4096 bytes | lecturas aleatorias: 20000 x 4096 bytes

--- SECUENCIAL - cache fria ---
metodo                      tiempo (s)   minor flt   major flt
read() chunks 64 KiB             0.561          32           0
mmap (MADV_SEQUENTIAL)           0.650         675           1

--- ALEATORIO  - cache fria ---
metodo                      tiempo (s)   minor flt   major flt
pread() 4 KiB                   11.686           1           0
mmap (MADV_RANDOM)              11.051           0       18549

--- SECUENCIAL - cache caliente ---
metodo                      tiempo (s)   minor flt   major flt
read() chunks 64 KiB             0.478           0           0
mmap (MADV_SEQUENTIAL)           0.490        8193           0

--- ALEATORIO  - cache caliente ---
metodo                      tiempo (s)   minor flt   major flt
pread() 4 KiB                    0.124           0           0
mmap (MADV_RANDOM)               0.147        7470           0

Archivo temporal borrado: /tmp/demo_mmap.bin
```

Importante mencionar que al correr el programa con WSL los accesos a memoria se ralentizan bastante.

### `mmap_como_arreglo()`

```
Tamano del mapeo : 4096 bytes
Primeros bytes   : b'Hola, mundo mapeado en memoria!'
Byte 0           : 72
Releido con read(): b'HOLA, mundo mapeado en memoria!'
```
Primero se muestra el tamaño del mapeo, posteriormente se muestran los primeros bytes del archivo, los cuales se imprimen correctamente, ya que los modificamos antes de esta prueba con:
```python
tmp.write(b"Hola, mundo mapeado en memoria!" + b"\x00" * (PAGE - 31))
```
Se continúa mostrando el primer byte como un número entero:
```
Carácter	Byte(Binario)	Decimal(ASCII)
   H	      01001000	         72
```
Finalmente, se muestran los primeros 31 bytes después del cambio para comprobar que se guardaron dichos cambios.

### `crear_archivo`
Esta función crea el archivo grande para las pruebas de eficiencia y solo muestra ```Creando /tmp/demo_mmap.bin (512 MiB)...```

### `page_faults`
```
Inodo               : 27
Tamano              : 536870912 bytes
Tamano de bloque FS : 4096 bytes
Bloques asignados   : 1048576 (de 512 bytes)
Tamano de pagina SO : 4096 bytes
Paginas del archivo : 131072

Despues de mmap()        : minor=0, major=0
Al tocar 1000 paginas     : minor=64, major=0
Al releer esas 1000       : minor=0, major=0
```
Primero de imprimen los datos de la prueba y después se muestran los errores de página que ocurren tras cada paso

### `benchmark`

```
Pagina del SO: 4096 bytes | lecturas aleatorias: 20000 x 4096 bytes

--- SECUENCIAL - cache fria ---
metodo                      tiempo (s)   minor flt   major flt
read() chunks 64 KiB             0.561          32           0
mmap (MADV_SEQUENTIAL)           0.650         675           1

--- ALEATORIO  - cache fria ---
metodo                      tiempo (s)   minor flt   major flt
pread() 4 KiB                   11.686           1           0
mmap (MADV_RANDOM)              11.051           0       18549

--- SECUENCIAL - cache caliente ---
metodo                      tiempo (s)   minor flt   major flt
read() chunks 64 KiB             0.478           0           0
mmap (MADV_SEQUENTIAL)           0.490        8193           0

--- ALEATORIO  - cache caliente ---
metodo                      tiempo (s)   minor flt   major flt
pread() 4 KiB                    0.124           0           0
mmap (MADV_RANDOM)               0.147        7470           0
```
Primero se muestran los datos de la prueba y luego se muestran los resultados:

1. Secuencial, fría:	mmap 15.9% más lento	read() tuvo ventaja
2. Secuencial, caliente:	mmap 2.5% más lento	Rendimiento prácticamente similar
3. Aleatorio, frío:	mmap 5.4% más rápido	Ventaja pequeña de mmap
4. Aleatorio, caliente:	mmap 18.5% más lento	pread() tuvo ventaja

- Secuencial: En este tipo de acceso observamos la ligera ventaja de read() frente a mmap que se esperaba, siendo aproximadamente 15% más rápido en caché fría.

Esto cambia en caché caliente, los tiempos de ejecución se estabilizan y no ocurre ningun error de página mayor, pero ocurren más errores menores.
Esto ocurre porque read() copia la información del archivo a RAM usando llamadas al kernel y solo trabaja con el buffer. mmap mapea los espacios de memoria y copia la información a RAM, pero accesos a paginas aún no mapeadas provocan un error menor.

- Aleatorio: En caché fría pread() lee segmentos aleatorios del archivo utilizando directamente llamadas al kernel, asi saltandose el mapeo en memoria virtual. Esto hace que el registro muestre 0 errores mayores (Accesos a almacenamiento), pero aún asi pausa el proceso.
mmap accede los puntos aleatorios de memoria e intenta mapearlos, los busca en RAM y luego en almacenamiento, por esto provoca tantos errores mayores.

En caché caliente la mayoría o todos los datos ya esyan copiados a RAM por lo que la ejecución es mucho más rápida: pread se ejecuta sin ningun problema pero mmap tiene muchos errores menores por la misma razón que antes, muchos de los accesos requeridos aún no han sido mapeados, lo que provoca errores menores. Este proceso causa que mmap sea ligeramente más lento que pread(), pero en posteriores ejecuciones donde los accesos sean en paginas ya mapeadas mmap sería más rápido (solo si se mantiene el mismo mapeo).

## Paso a paso

### Arranque

1. Python lee las constantes y define todas las funciones. Todavía no ejecuta nada.
2. Llega a la última línea de `main.py`, `if __name__ == "__main__": main()`, y llama a `main()`.
3. `main()` lee las opciones, define el tamaño y la ruta del archivo de prueba, y ejecuta las partes en orden.

### Parte 1: `mmap_como_arreglo()`

1. **Crear el archivo pequeño.** Se escribe un archivo temporal con la frase "Hola, mundo mapeado en memoria!" rellenada con ceros hasta una página.
2. **Abrirlo con mmap.** Se abre en modo lectura y escritura, y se mapea completo (`mmap.mmap(f.fileno(), 0)`). Desde aquí el archivo se usa como una lista de bytes.
3. **Consultarlo.** Se imprime:
   - el tamaño del mapeo (4096 bytes);
   - los primeros bytes (`mm[:31]`);
   - el primer byte (`mm[0]`, un número).
4. **Modificarlo.** Se escribe `mm[0:4] = b"HOLA"`, y la frase pasa de "Hola" a "HOLA" directo en memoria.
5. **Guardar y cerrar.** `mm.flush()` manda el cambio al disco y el mapeo se cierra al salir del `with`.
6. **Comprobar.** Se abre el archivo de la forma normal con `read()` y se imprime. Debe verse "HOLA, mundo...", lo que demuestra que el cambio sí quedó en el archivo.
7. **Limpiar.** Se borra el archivo temporal.

### Parte 2: creación del archivo y `page_faults()`

1. **Crear el archivo grande** (`crear_archivo()`):
   - Se genera un bloque de 1 MB con datos aleatorios.
   - Se escribe repetidamente hasta llegar a 512 MB y se sincroniza a disco.
   - Es el paso que más tarda, porque escribe todo el archivo.
2. **Mostrar el mapeo y los fallos** (`page_faults()`):
   - Se imprime el inodo, los bloques y las páginas del archivo.
   - Se vacía la caché y se mapea el archivo: aquí casi no hay fallos, porque solo se reservan direcciones.
   - Se tocan 1000 páginas y se cuentan los fallos.
   - Se vuelven a leer esas páginas y ya no aparecen fallos nuevos.

### Parte 3: `benchmark()`

**Preparación**

1. **Elegir lugares al azar.**
   - Se eligen 20,000 posiciones aleatorias, todas múltiplos de 4096.
   - La lista se arma una sola vez. Así los dos métodos leen exactamente los mismos lugares.

**Las pruebas**

Cada prueba se hace con `medir()`, que anota la hora antes y después, y los fallos de página. Primero se ejecutan con caché fría y después con caché caliente:

1. **Lectura secuencial normal.** Se abre el archivo y se leen pedazos de 64 KB hasta llegar al final.
2. **Lectura secuencial con mmap.** Se mapea el archivo y se toman pedazos de 64 KB uno tras otro hasta el final.
3. **Lectura aleatoria normal.** Para cada una de las 20,000 posiciones se lee un pedazo de 4 KB con `pread()`.
4. **Lectura aleatoria con mmap.** Para cada una de las 20,000 posiciones se toma directamente el pedazo del archivo mapeado.

En la caché fría, el archivo se saca de la caché antes de cada medición. En la caché caliente, el archivo se lee completo una vez antes de medir.

**Resultados**

1. Se imprime una tabla por escenario, con una fila por método y las columnas de tiempo, fallos menores y fallos mayores.
2. Con caché fría aparecen fallos mayores, porque los datos se leen del disco. Con caché caliente solo aparecen fallos menores.
3. Se borra el archivo grande.


## Conclusiones

A través de este proyecto se comprobó el funcionamiento de los archivos mapeados en memoria (mmap), observando cómo el sistema operativo relaciona un archivo con el espacio de direcciones virtuales de un proceso. Se verificó que crear un mapeo no implica cargar inmediatamente todo el archivo a RAM, sino que las páginas se van haciendo accesibles conforme el programa las utiliza. Esto permite trabajar con archivos grandes sin necesidad de cargarlos completamente de manera explícita.

Finalmente, se concluye que mmap no es necesariamente más rápido que read() en todos los escenarios. Su principal ventaja se encuentra en la flexibilidad de acceder al archivo como una región de memoria y su utilidad en accesos repetidos.

En cambio, read() y pread() pueden ser muy eficientes para lecturas secuenciales o aleatorias cuando se utilizan adecuadamente y los datos están disponibles en la caché. La elección del método debe considerar el patrón de acceso, el tamaño del archivo y el estado de la caché.

## Referencias
- Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). Operating System Concepts (10th ed.). Wiley. (Capítulo sobre gestión de memoria virtual y mapeo de archivos).
- Linux Programmer's Manual. mmap(2) - Linux man page. Disponible en: https://man7.org/linux/man-pages/man2/mmap.2.html
- Python Software Foundation. mmap — Memory-mapped file support. Documentación oficial de Python. Disponible en: https://docs.python.org/3/library/mmap.html
