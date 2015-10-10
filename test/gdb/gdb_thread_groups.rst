Objetivo
--------
Lo que se vera es que son los thread groups y como listarlos y su relacion con
los threads en una aplicacion multithreading.

Desarrollo
----------

Primero, inicializamos el sistema de comunicaciones

::

   >>> import sys
   >>> sys.path.append("../src/py/")

   >>> from shortcuts import start_notifier, stop_notifier, request, collect
   >>> start_notifier("../src/py/publish_subscribe/")

Ahora, antes de lanzar el GDB, vamos a registrarnos a sus eventos para ver cuales
son los que lanza justo al iniciarse.

::

   >>> from publish_subscribe.eventHandler import EventHandler
   >>> EH = EventHandler(name="TheTest")
   
   >>> @collect
   ... def collector(data):
   ...   if data['klass'] == u'library-loaded' or data['klass'].startswith('breakpoint-'):
   ...      return None # discard
   ...   return data
   
   >>> EH.subscribe('notification-gdb', collector)

Bien, ahora lanzamos GDB para ver que sucede


::

   >>> from gdb.gdb import Gdb
   >>> gdb = Gdb()

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-group-added',
    u'results': {u'id': u'i1'},
    u'token': None,
    u'type': u'Notify'}

Lo que vemos es que cuando GDB se lanza, él crea un container para una session de
debugging. En MI esto se llama 'thread group', pero en el contexto de una session 
por CLI (con un usuario humano) esto se llama 'inferior'.

Para probarlo, vamos a crear un inferior y ver que esto hace que GDB cree un nuevo
thread group.

::

   >>> request(gdb, "-add-inferior", [])              # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {u'inferior': u'i2'},
    u'token': ...,
    u'type': u'Sync'}

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-group-added',
    u'results': {u'id': u'i2'},
    u'token': None,
    u'type': u'Notify'}

Notese como la accion sincronica "add inferior" nos da un resultado sincronico pero
tambien nos da un evento asincronico que lo capturamos con nuestro collector.

Ahora, debe haber 2 inferior o thread groups

::

   >>> request(gdb, '-list-thread-groups', [])        # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {u'groups': [{u'id': u'i2', u'type': u'process'},
                             {u'id': u'i1', u'type': u'process'}]},
    u'token': ...,
    u'type': u'Sync'}

Cada thread group (TG) tiene un identificador y un tipo que por ahora es siempre 'process'.

Asi como se pueden agregar TGs, se los pueden borrar:

::

   >>> request(gdb, "-remove-inferior", ["i2"])              # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {},
    u'token': ...,
    u'type': u'Sync'}

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-group-removed',
    u'results': {u'id': u'i2'},
    u'token': None,
    u'type': u'Notify'}

A diferencia de lo que paso cuando se creaba un inferior, removerlo siempre nos da
un resultado asincronico, capturado por el handler collector (la respuesta sincronica
retornada por el request no aporta la misma informacion que la asincronica)

Aparentemente siempre debe haber al menos un inferior por GDB:

::

   >>> request(gdb, "-remove-inferior", ["i1"])              # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'error',
    u'results': {u'msg': u'Cannot remove last inferior'},
    u'token': ...,
    u'type': u'Sync'}

Cada TG es creado sin ningun ejecutable asociado. Para asociarlo podemos cargarlo
(con o sin sus simbolos)

::

   >>> BIN="../src/cppTestCode/threads/two_pthreads"
   >>> request(gdb, "-file-exec-and-symbols", [BIN])        # doctest: +PASS

   >>> request(gdb, '-list-thread-groups', [])              # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {u'groups': [{u'executable': u'.../two_pthreads',
                              u'id': u'i1',
                              u'type': u'process'}]},
    u'token': ...,
    u'type': u'Sync'}


Ready and loaded. Veamos que pasa cuando iniciamos el proceso.

::

   >>> request(gdb, "-exec-run", ["--start"])        # doctest: +PASS
   >>> request(gdb, '-list-thread-groups', [])       # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {u'groups': [{u'cores': [u'...'],
                              u'executable': u'.../two_pthreads',
                              u'id': u'i1',
                              u'pid': u'...',
                              u'type': u'process'}]},
    u'token': ...,
    u'type': u'Sync'}

Vemos como aparece el ejecutable asi como tambien el process id. Este ultimo identificador
depende del target donde se esta corriendo el proceso.

Para ver mas en detalle que threads se estan usando hacemos:

::

   >>> request(gdb, "-thread-info", [])       # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {u'current-thread-id': u'1',
                 u'threads': [{u'core': u'...',
                               u'frame': {u'addr': u'0x...',
                                          u'args': [{u'name': u'argc',
                                                     u'value': u'1'},
                                                    {u'name': u'argv',
                                                     u'value': u'0x...'}],
                                          u'file': u'two_pthreads.c',
                                          u'fullname': u'.../two_pthreads.c',
                                          u'func': u'main',
                                          u'level': u'0',
                                          u'line': u'...'},
                               u'id': u'1',
                               u'name': u'...',
                               u'state': u'stopped',
                               u'target-id': u'...'}]},
    u'token': ...,
    u'type': u'Sync'}

Tanto 'name' como 'target-id' son nombres simbolicos que dependen en general de la
plataforma. En algunos casos, 'name' puede se definido por el programa asi que puede
que tenga valor mostrarlo.

El estado ('state') puede tener dos valores posibles: 'stopped' o 'running'.

Como se puede ver, la informacion de los thread no tienen ningun identificador que indique
a que TG pertenece. De hecho, los ids de los threads es global independientemente de a
que TG pertenezcan.
Para poder asocias threads groups con threads es necesario hacer un request para
listar los TGs con el flag 'recurse' para que incluya los hilos que tiene asociado (de
hecho incluye la misma data que se obtiene al listar los threads directamente):

:: 
   
   >>> request(gdb, '-list-thread-groups', ['--recurse', '1'])    # doctest: +ELLIPSIS
   {u'debugger-id': ...,
    u'klass': u'done',
    u'results': {u'groups': [{u'cores': ...,
                              u'executable': u'.../two_pthreads',
                              u'id': u'i1',
                              u'pid': ...,
                              u'threads': [{u'core': ...,
                                            u'frame': ...
                                            u'id': u'1',
                                            u'name': u'two_pthreads',
                                            u'state': u'stopped',
                                            u'target-id': u'...'}],
                              u'type': u'process'}]},
    u'token': ...,
    u'type': u'Sync'}

Veamos que eventos aparecieron tras darle play a un proceso para debuguearlo:

::

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-group-started',
    u'results': {u'id': u'i1', u'pid': u'...'},
    u'token': None,
    u'type': u'Notify'}
   
   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-created',
    u'results': {u'group-id': u'i1', u'id': u'1'},
    u'token': None,
    u'type': u'Notify'}
 

Los eventos mas interesantes son "el TG se ejecuta" y "un hilo es creado".
Notese como el evento del thread indica a que TG pertenece.
(Nota: los eventos sobre breakpoints y sobre la carga de librerias fueron
removidos para evitar ofuscar el test.)

Los siguientes eventos son debido a que el hilo se ejecuta y llega al main, donde
estaba el breakpoint puesto por el flag '--start' y por ello se detiene:

::
  
   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'running',
    u'results': {u'thread-id': u'all'},
    u'token': None,
    u'type': u'Exec'}

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'stopped',
    u'results': {...
                 u'frame': {...
                            u'file': u'two_pthreads.c',
                            u'fullname': u'.../two_pthreads.c',
                            u'func': u'main',
                            u'line': u'13'},
                 u'reason': u'breakpoint-hit',
                 u'stopped-threads': u'all',
                 u'thread-id': u'1'},
    u'token': None,
    u'type': u'Exec'}


Ahora pondremos un breakpoint en el codigo del hilo secundario (funcion llamada "roll") 
para ver como se muestra un proceso con dos hilos.

::

   >>> request(gdb, "-break-insert", ["roll"])        # doctest: +PASS
   >>> request(gdb, "-exec-continue")                 # doctest: +PASS

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'running',
    ...

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-created',
    u'results': {u'group-id': u'i1', u'id': u'2'},
    u'token': None,
    u'type': u'Notify'}

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'running',
    u'results': {u'thread-id': u'all'},
    u'token': None,
    u'type': u'Exec'}

NOTE: algunas veces el evento de que se detuvo por un breakpoint nunca llega.
Tras  algo de debuggeo, es GDB quien nunca emite el evento. Parece que esto
esta relacionado con la aplicacion multithreading:
https://sourceware.org/bugzilla/show_bug.cgi?id=17247

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'stopped',
    u'results': {u'bkptno': u'2',
                 u'core': ...,
                 u'disp': u'keep',
                 u'frame': {u'addr': u'0x...',
                            u'args': [{u'name': u'cookie',
                                       u'value': u'0x...'}],
                            u'file': u'two_pthreads.c',
                            u'fullname': ...
                            u'func': u'roll',
                            u'line': u'5'},
                 u'reason': u'breakpoint-hit',
                 u'stopped-threads': u'all',
                 u'thread-id': u'2'},
    u'token': None,
    u'type': u'Exec'}

Al darle 'continue', el hilo principal empieza a correr y lanza su hilo secundario.
Esto se refleja en los dos eventos 'thread-created' y el segundo 'running'.
Debido a que le decimos a GDB que arranque todos los hilos, el evento 'running' indica
que los hilos que se estan corriendo son todos ('all'). (Tal vez, pero no se muestra
aca, se puede decirle a GDB que haga un 'continue' de solo algunos hilos)

Luego el hilo secundario llega al breakpoint y se detiene como lo muestra el evento 'stopped'.

Ahora tenemos 2 hilos, el principal bloqueado en el join (pero no esta bloqueado
por algo de GDB como un breakpoint) y el segundo hilo, bloqueado en un breakpoint.

Pero se puede ver que el evento 'stopped' indica que hilos fueron detenidos ('stopped-threads')
y como se muestra, todos los hilos fueron detenidos.

Veamos como queda la info de los hilos:

::

   >>> request(gdb, "-thread-info", [])       # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {u'current-thread-id': u'2',
                 u'threads': [{u'core': ...,
                               u'frame': {u'addr': u'0x...',
                                          u'args': [{u'name': u'cookie',
                                                     u'value': u'0x...'}],
                                          u'file': u'two_pthreads.c',
                                          u'fullname': ...
                                          u'func': u'roll',
                                          u'level': u'0',
                                          u'line': u'5'},
                               u'id': u'2',
                               u'name': ...
                               u'state': u'stopped',
                               u'target-id': ...},
                              {u'core': ...,
                               u'frame': {u'addr': u'0x...',
                                          u'args': [],
                                          u'func': u'__kernel_vsyscall',
                                          u'level': u'0'},
                               u'id': u'1',
                               u'name': ...
                               u'state': u'stopped',
                               u'target-id': ...}]},
    u'token': ...,
    u'type': u'Sync'}

Como era de esperarse, ahora tenemos 2 hilos. Sin embargo, algunas observaciones:
 - el hilo principal esta en el estado 'stopped' lo que es raro porque si bien esta
   bloqueado en un join, no esta bloqueado por culpa de GDB. Lo mas probable es que
   el breakpoint alcanzado por el segundo hilo haya hecho frenar a ambos.
 - el 'current-thread-id' paso de ser 1 (el hilo principal) a ser 2 (el nuevo hilo) 
   sin ninguna intervencion nuestra. A no suponer que se mantiene constante!!!.

Veamos que sucede cuando un hilo termina. Para ello, pondremos otro breakpoint en el
main y haremos continue para que el hilo secundario termine y el main se bloque nuevamente.

::

   >>> request(gdb, "-break-insert", ["16"])          # doctest: +PASS
   >>> request(gdb, "-exec-continue")                 # doctest: +PASS
   
   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'running',
    ...

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-exited',
    u'results': {u'group-id': u'i1', u'id': u'2'},
    u'token': None,
    u'type': u'Notify'}

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'stopped',
    ...


Y ahora veremos como  un programa termina, con un 'continue' final.

:: 

   >>> request(gdb, "-exec-continue")                 # doctest: +PASS

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'running',
    ...

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-exited',
    u'results': {u'group-id': u'i1', u'id': u'1'},
    u'token': None,
    u'type': u'Notify'}

   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'thread-group-exited',
    u'results': {u'exit-code': u'01', u'id': u'i1'},
    u'token': None,
    u'type': u'Notify'}


   >>> collector.get_next()                           # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'stopped',
    u'results': {u'exit-code': u'01', u'reason': u'exited'},
    u'token': None,
    u'type': u'Exec'}

 
Como era de esperarse, el hilo principal termina (thread-exited) y el inferior o TG 
tambien (thread-group-exited).
Lo increible es que hay un evento extra, un 'stopped' de un hilo que termino, pero
cuando el hilo secundario termino no hubo ningun 'stopped' de ese hilo! 

::

   >>> request(gdb, '-list-thread-groups', [])       # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {u'groups': [{u'executable': u'.../two_pthreads',
                              u'id': u'i1',
                              u'type': u'process'}]},
    u'token': ...,
    u'type': u'Sync'}

   >>> request(gdb, "-thread-info", [])               # doctest: +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    u'results': {u'threads': []},
    u'token': ...,
    u'type': u'Sync'}


Lo interesante es que la documentacion de GDB dice que debe haber un 'exit-code' cuando
se lista los TGs. Pero esta informacion no aparece; solo se la vio en el thread-group-exited.

Limpiamos todo:

::

   >>> gdb.shutdown()
   0

   >>> stop_notifier("../src/py/publish_subscribe/")

Conclusiones
------------

GDB tiene siempre al menos un inferior o thread group (TG). Se pueden agregar o quitar
pero siempre debe haber al menos 1. Eventos thread-group-added y thread-group-removed
Se listan con -list-thread-groups

Cada TG es como un place holder. Se le puede asociar con un ejecutable y luego darle play
para comenzar el debuggeo. Evento thread-group-started

Cada programa tiene al menos un hilo (el main), hilos que se crean y destruyen.
Se listan con -thread-info.  Eventos thread-created y thread-exited

Al finalizar un programa, el TG queda cargado con su ejecutable pero apagado. 
Eventos thread-group-exited (que tiene el exit code del proceso)

eventos recibido      |   datos trackeados en funcion del tiempo (a medida que pasa los eventos)
- - - - - - - - - - - - - - - - - - - - - - - - - -
   <inicial>          |   < vacio > 
thread-group-added    |   TG id (como 'i1')
   ???? (1)           |   TG id; executable (como 'two_pthreads')
   ???? (2)           |   TG id; executable; PID (process id)
thread-created        |   TG id; executable; PID; thread id (como '1')
running               |   TG id; executable; PID; thread id; thread state (running)
stopped               |   TG id; executable; PID; thread id; thread state (stopped)
thread-exited         |   TG id; executable; PID; thread id (thread lost or removed)
thread-group-exited   |   TG id; executable; PID (lost); exit code (como 0)
   ???? (3)           |   TG id; executable; exit code (removed)
   ???? (4)           |   TG id; executable (removed)
thread-group-removed  |   TG id (removed)
   <final>            |   < vacio > 

Los signos ???? representa que no hay ningun evento asincronico que contenga esa informacion.
Solo los eventos sincronicos (resultados de un request) como las respuestas de los 
comandos -thread-info y -list-thread-groups contienen esa data.
Lo interesante es que incluso solo se necesita ejecutar -list-thread-groups, el resto de
la informacion (en particular el estado de cada thread) se puede trackear con los eventos
'running' y 'stopped'. Aun asi, -thread-info es util para hacer refresh, sincronizaciones
y updateos en caso de perderse de algun running/stopped.
