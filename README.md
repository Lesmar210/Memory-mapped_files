# Memory-mapped_files
## Integrantes
- 323270258 - Aguilar Sánchez Carla Alexandra 
- 323214478 - Ramriez Olvera Erick Yael
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

### Arranque

1. Python lee las constantes y define todas las funciones. Todavía no ejecuta nada.
2. Llega a la última línea, `if __name__ == "__main__": main()`, y llama a `main()`.
3. `main()` ejecuta primero `demo_basico()` y después `benchmark()`.

### Parte 1: `demo_basico()`

1. **Crear el archivo pequeño.** Se escribe `pequeno.txt` con la frase "Hola mundo desde un archivo mapeado a memoria".
2. **Abrirlo con mmap.** Se abre en modo lectura y escritura, y se mapea completo (`mmap.mmap(f.fileno(), 0)`). Desde aquí el archivo se usa como una lista de bytes.
3. **Consultarlo.** Se imprime:
   - el tamaño (45 bytes);
   - el primer byte (`mm[0]`, un número);
   - las primeras 4 posiciones (`mm[0:4]`, es decir `Hola`);
   - la posición de la palabra "mundo" (`mm.find`).
4. **Modificarlo.** Se escribe `mm[0:4] = b"HOLA"`, y la frase pasa de "Hola" a "HOLA" directo en memoria.
5. **Guardar y cerrar.** `mm.flush()` manda el cambio al disco y `mm.close()` cierra el mapeo.
6. **Comprobar.** Se abre el archivo de la forma normal con `read()` y se imprime. Debe verse "HOLA mundo...", lo que demuestra que el cambio sí quedó en el archivo.
7. **Limpiar.** Se borra `pequeno.txt`.

### Parte 2: `benchmark()`

**Preparación**

1. **Crear el archivo grande** (`crear_archivo()`):
   - Se calcula cuántas líneas hacen falta para llegar a 256 MB.
   - Se escribe cada línea ("Linea 000000000...", "Linea 000000001...") rellenada hasta medir 64 caracteres.
   - Es el paso que más tarda, porque escribe 256 MB.
2. **Saltar a una línea** (`acceso_directo()`):
   - Se abre el archivo grande con mmap.
   - Se calcula dónde empieza la línea 1,000,000 (1,000,000 × 64).
   - Se imprime esa línea sin haber leído las anteriores.
3. **Elegir lugares al azar.**
   - Se eligen 50,000 posiciones aleatorias, todas múltiplos de 4096.
   - La lista se arma una sola vez. Así los dos métodos leen exactamente los mismos lugares.

**Las pruebas**

Cada prueba se hace con `medir()`, que anota la hora antes y después, y se repite 3 veces. En cada repetición pasa lo siguiente:

1. **Lectura secuencial normal.** Se abre el archivo y se leen pedazos de 4 KB hasta llegar al final.
2. **Lectura secuencial con mmap.** Se mapea el archivo y se toman pedazos de 4 KB uno tras otro hasta el final.
3. **Lectura aleatoria normal.** Para cada una de las 50,000 posiciones se salta ahí y se lee un pedazo.
4. **Lectura aleatoria con mmap.** Para cada una de las 50,000 posiciones se toma directamente el pedazo del archivo mapeado.

**Resultados**

1. Se imprime una tabla con una fila por prueba y tres tiempos (1ª, 2ª y 3ª vez), en segundos.
2. La 1ª vez puede ser más lenta porque el sistema operativo aún no tiene el archivo en su memoria rápida (la caché). Las siguientes suelen ser más rápidas.
3. Se borra el archivo grande.


## Conclusiones

## Referencias
- Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). Operating System Concepts (10th ed.). Wiley. (Capítulo sobre gestión de memoria virtual y mapeo de archivos).
- Linux Programmer's Manual. mmap(2) - Linux man page. Disponible en: https://man7.org/linux/man-pages/man2/mmap.2.html
- Python Software Foundation. mmap — Memory-mapped file support. Documentación oficial de Python. Disponible en: https://docs.python.org/3/library/mmap.html
