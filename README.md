# Memory-mapped_files
## Integrantes
- 323270258 - Aguilar Sánchez Carla Alexandra 
- N.Cuenta - Nombre
- N.Cuenta - Nombre
- N.Cuenta - Nombre
  
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

## Analisis de resultados

## Paso a paso

## Conclusiones

## Referencias
- Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). Operating System Concepts (10th ed.). Wiley. (Capítulo sobre gestión de memoria virtual y mapeo de archivos).
- Linux Programmer's Manual. mmap(2) - Linux man page. Disponible en: https://man7.org/linux/man-pages/man2/mmap.2.html
- Python Software Foundation. mmap — Memory-mapped file support. Documentación oficial de Python. Disponible en: https://docs.python.org/3/library/mmap.html
