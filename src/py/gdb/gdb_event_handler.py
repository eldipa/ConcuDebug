import gdb

import Queue
import functools
import os
import syslog

import contextlib
import traceback

from publish_subscribe.eventHandler import EventHandler as EH

def noexception(error_message, return_value=None):
  '''Helper decorator for logging exceptions using the global GDBEventHandler instance.

     This wrapper will invoke the wrapped method and if an exception is thrown,
     this will be logged to the system's log (GDBEventHandler's _log method) and
     a copy of the message will be published to outside (GDBEventHandler's publish method).
    
     The message will be the concatenation of error_message and the traceback.
     See the GDBEventHandler's publish_error method)
     
     This wrapper will capture any exception and will discard them after logging the
     error. In these cases, the wrapper will return return_value as the result of the
     original method invokation.

     Precondition: the global event handler (GDBEventHandler) must be initialized first
     calling the 'initialize' function, otherwise, when this decorator call to
     '_get_global_event_handler' this will crash.
  '''
  def decorator(func):
    def wrapper(self, *args, **kargs):
      try:
        with publish_expection_context(error_message):
          return self.func(*args, **kargs)
      except:
        pass
      return return_value
    return wrapper
  return decorator

@contextlib.contextmanager
def publish_expection_context(error_message):
  try:
    yield 
  except:
    publisher = _get_global_event_handler()
    publisher.publish_exception(error_message)

class _GDBEventHandler(EH):
  def __init__(self, gdb_id):
    EH.__init__(self, name="(gdb %s)" % gdb_id, as_daemon=True) # as_daemon=True otherwise GDB hangs
    self.gdb_id = gdb_id
    self.queue = Queue.Queue(maxsize=1000000)

  def get_gdb_id(self):
    return self.gdb_id

  def _execute_callback(self, callback, data, t):
    '''Dont execute the callback right now, instead defer the execution of the event 
       and move it to the gdb event loop to be executed in some point in the future.

       This method can be running in a separate thread (async)'''
    event = functools.partial(self._execute_callback_in_gdb_loop, callback, data, t)
    gdb.post_event(lambda: self._handle_event_in_gdb_event_loop(event))
  
  @noexception(error_message="Internal error in the processing of the current or the previous queued events.")
  def _handle_event_in_gdb_event_loop(self, event):
    '''Handle this event. 
       If the target is running, defer the execution pushing this event into a 
       queue to be executed later.
       If the target is stopped, then it should be safe to execute the event
       now, but before, execute all the queued events and then this current event.
       
       This method should run in the main thread (gdb thread or gdb event loop)'''
    if self._is_target_stopped():
      last_event = event
      while True:
        try:
          event = self.queue.get_nowait()
        except Queue.Empty:
          break

        event()
        self.queue.task_done()

      last_event()
    else:
      self._put_event_into_queue(event)

  @noexception(error_message="Internal GDB's queue of events is full")
  def _put_event_into_queue(self, event):
    self.queue.put(event)
 
  @noexception(error_message="Error when trying to see if the target stopped", return_value=False)
  def _is_target_stopped(self):
    selected_thread = gdb.selected_thread()
    if selected_thread is not None and selected_thread.is_running():
      return False
    else:
      return True

  @noexception(error_message="Exception when executing a callback (processing a incoming event)")
  def _execute_callback_in_gdb_loop(self, callback, data, t):
    '''Execute the callback associated to the particular event with those data.

       This method should be executed in the gdb loop and with the target process
       stopped.

       This method also must warranty that no exception can be raised from here.'''
    callback(data)

  def publish_log(self, severity, log_message, *args, **kargs):
    '''Log to syslog and publish an event of type 'gdb-log', with the defined severity.
       The message will be 'log_message', fulfilled with the arguments 'args'.
    '''
    message = self._log(severity, log_message, *args)

    data = {'msg': message, 'gdb-id': self.gdb_id, 'severity': severity}
    data.update(kargs.get('extra_data', {}))

    self.publish("gdb-log", data)

  def publish_exception(self, error_message, **kargs):
    '''Shortcut for logging errors. This method will log to syslog and publish an
       event using the publish_log method, with LOG_ERR severity.
       The final message will be the concatenation of the error_message and the
       current traceback.
    '''
    self.publish_log(syslog.LOG_ERR, error_message + "%s", traceback.format_exc(), extra_data=kargs.get('extra_data', {}))


__EV = None

def initialize():
  global __EV
  if __EV is not None:
    raise ValueError("The GDB Event Handler is already loaded.")

  gdb_id = os.getpid()
  __EV = _GDBEventHandler(gdb_id)
  
def _get_global_event_handler():
  global __EV
  if __EV is None:
    raise ValueError("The GDB Event Handler was not initialized.")

  return __EV
