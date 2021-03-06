Para probar el sistema de obtencion de variables utilizaremos el siguiente
codigo:

.. include:: ../src/cppTestCode/testVariables.cpp 
   :code: cpp


Iniciamos el publicador

:: 
   >>> import os 
   >>> import time 
   >>> from subprocess import check_output 

   >>> def is_running(): 
   ...   out = check_output(["python","py/publish_subscribe/notifier.py", "status"]) 
   ...   return "running" in out

   >>> os.system("python py/publish_subscribe/notifier.py start") # doctest: +PASS

   >>> time.sleep(2) #esperamos que el servidor este andando. 
   >>> is_running() 
   True
   >>> import publish_subscribe.eventHandler 
   >>> eventHandler = publish_subscribe.eventHandler.EventHandler()
   

Iniciamos al gdbSpawmer  

:: 
   >>> import gdb.gdbSpawmer 
   >>> spawmer = gdb.gdbSpawmer.GdbSpawmer() 
   
Lanzamos un nuevo gdb: 

:: 
   >>> gdbPid = spawmer.startNewProcessWithGdb("cppTestCode/testVariables") 
   >>> time.sleep(2)
   >>> gdbPid > 0 
   True
   >>> len(spawmer.listaGdb) == 1 
   True

Colocamos un breakpoint:

::
   >>> eventHandler.publish(str(gdbPid) + ".break-funcion", "testVariables.cpp:37") 
   >>> time.sleep(2)

Ejecutamos hasta el breakpoint:

::
   >>> eventHandler.publish(str(gdbPid) + ".run", "")
   >>> time.sleep(2)
   
   
Pedimos las variables:

::
   >>> import threading, time
   >>> shared_list = [] 
   >>> shared_lock = threading.Lock() 
   >>>                               
   >>> def add_sync(data): 
   ...   global shared_lock 
   ...   global shared_list 
   ... 
   ...   shared_lock.acquire() 
   ...   shared_list.append(data) 
   ...   shared_lock.release()
   
   >>> eventHandler.subscribe("result-gdb." + str(gdbPid), add_sync)
   >>> eventHandler.publish(str(gdbPid) + ".get-variables", "")
   >>> time.sleep(2)
   
   >>> shared_list[0] #doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS 
   {u'debugger-id': ...
    u'klass': u'done',
   ...
   u'results': {u'variables': [{u'name': u'estructura',
                                u'value': u'{enteroStruct = ..., 
                                             floatStruct = ...}'},
                               {u'name': u'entero', 
                                u'value': u'0'},
                               {u'name': u'punteroEntero',
                                u'value': u'0x...'},
                               {u'name': u'cString', 
                                u'value': u'"Hola"'},
                               {u'name': u'clase',
                                u'value': u'{atributoEntero = ..., 
                                             atributoFloat = ...}'},
                               {u'arg': u'1',
                                u'name': u'argc',
                                u'value': u'1'},
                               {u'arg': u'1',
                                u'name': u'argv',
                                u'value': u'0x...'}]},
   u'token': None,
   u'type': u'Sync'}
   >>> shared_list = [] 
   
Para imprimir el valor de una expresion, en particular, de un puntero:

::
   >>> eventHandler.publish(str(gdbPid) + ".evaluate-expression", "*punteroEntero")
   >>> time.sleep(2)
   
   >>> shared_list[0] #doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
   {u'debugger-id': ...
    u'klass': u'done',
    ...
    u'results': {u'value': u'0'},
    u'token': None,
    u'type': u'Sync'}
   
   
Limpieza:

::

   >>> spawmer.exit("all") 
   >>> spawmer.eliminarCola() 
   >>> ##finalizo al server. 
   >>> os.system("python py/publish_subscribe/notifier.py stop")   # doctest: +PASS
   >>> is_running() 
   False
