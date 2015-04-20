import threading
from gdb_mi import Output, Record, Stream
import publish_subscribe.eventHandler


class OutputReader(threading.Thread):
    
    def __init__(self, gdbOutput, queue, gdbPid): 
        threading.Thread.__init__(self)
        self.eventHandler = publish_subscribe.eventHandler.EventHandler()
        self.queue = queue
        self.parser = Output()
        self.gdbOutput = gdbOutput
        self.daemon = True
        self.gdbPid = gdbPid
        self.pid = 0
    
    def run(self):
        salir = False

        while (not salir):
            line = ""
            try:
                line = self.gdbOutput.readline()
            except:
                salir = True
                continue
            
#             print "line=" + line
            
            if line == "":
                salir = True
                continue

            record = self.parser.parse_line(line)

            if isinstance(record, Record):
                if (record.klass == "thread-group-started"):
                    self.pid = record.results["pid"]
                    self.eventHandler.publish("debugger.new-target.%i" % self.gdbPid , {'gdbPid': self.gdbPid, 'targetPid': self.pid})
                
            if record != "(gdb)":
                
                data = vars(record)
                topic = "gdb." + str(self.gdbPid) + ".type." + record.type
            
                if isinstance(record, Record):
                    topic += (".klass." + record.klass)
                if isinstance(record, Stream):
                    pass  # de momento nada
                   
                self.eventHandler.publish(topic, data)
#         print "saliendo reader"
