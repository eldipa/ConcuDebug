import re
DIGITS = re.compile('\d+(\.\d+)?')


class Result:
   def parse(self, string, offset):
      self.variable = Variable()
      offset = self.variable.parse(string, offset)

      assert string[offset] == '='
      offset += 1

      self.value = Value()
      offset = self.value.parse(string, offset)

      return offset


class Variable:
   def parse(self, string, offset):
      i = string[offset:].find('=')
      if i < 0:
         raise Exception("Token '=' not found")
      self.name = string[offset:offset+i]

      return offset+i


class Value:
   def parse(self, string, offset):
      c = string[offset]

      self.value = {
            '"': CString(),
            '{': Tuple(),
            '[': List(),
            }[c]

      offset = self.value.parse(string, offset)
      return offset

class CString:
   def parse(self, string, offset):
      assert string[offset] == '"'
      
      escaped = False
      for i, c in enumerate(string[offset+1:]):
         if c == '"' and not escaped:
            self.value = string[offset+1:offset+1+i]
            break

         if c == '\\':
            escaped = not escaped
         else:
            escaped = False


      return offset + len(self.value) + 2


class Tuple:
   def parse(self, string, offset):
      assert string[offset] == '{'

      self.value = []
      
      offset += 1
      while string[offset] != '}':
         self.value.append(Result())
         offset = self.value[-1].parse(string, offset)
         assert string[offset] in (",", "}")


      return offset + 1

class List:
   def parse(self, string, offset):
      assert string[offset] == '['

      self.value = []
      
      offset += 1

      if string[offset] != ']':
         Elem = Value if string[offset] in ('"', '{', '[') else Result

      while string[offset] != ']':
         self.value.append(Result())
         offset = self.value[-1].parse(string, offset)
         assert string[offset] in (",", "]")


      return offset + 1

class Word:
   def __init__(self, delimiters):
      self.delimiters = delimiters

   def parse(self, string, offset):
      i = 0
      while string[offset+i] not in self.delimiters:
         i += 1

      self.value = string[offset:offset+i]
      return offset + i



class AsyncOutput:
   def parse(self, string, offset):
      self.async_class = Word((',', '\r', '\n'))
      offset = self.async_class.parse(string, offset)

      self.results = []

      while string[offset] == ',':
         offset += 1
         self.results.append(Result())
         offset = self.results[-1].parse(string, offset)

      return offset


class AsyncRecord:
   def parse(self, string, offset):
      self.type = {
            "*": "Exec",
            "+": "Status",
            "=": "Notify",
            }[string[offset]]

      offset += 1
      self.output = AsyncOutput()
      offset = self.output.parse(string, offset)

      return offset

class StreamRecord:
   def parse(self, string, offset):
      assert string[offset] in ("~", "@", "&")
      self.type = {
            "~": "Console",
            "@": "Target",
            "&": "Log",
            }[string[offset]]

      offset += 1
      self.value = CString()
      offset = self.value.parse(string, offset)

      return offset



class ResultRecord:
   def parse(self, string, offset):
      assert string[offset] == "^"
      offset += 1

      self.result_class = Word((',', '\r', '\n'))
      offset = self.result_class.parse(string, offset)

      self.results = []

      while string[offset] == ',':
         offset += 1
         self.results.append(Result())
         offset = self.results[-1].parse(string, offset)

      return offset


class Output:
   def parse_line(self, line):
      assert line[-1] == '\n'

      #import pdb; pdb.set_trace()        #     :)  
      if line == "(gdb)":
         return line

      if line[0] in ("~", "@", "&"):
         out = StreamRecord()
         out.parse(line, 0)
         return out

      token = DIGITS.match(line)
      offset = 0
      if token:
         token = token.group()
         offset += len(token)
         token = int(token)

      else:
         token = None

      if line[offset] == "^":
         out = ResultRecord()
      else:
         out = AsyncRecord()

      offset = out.parse(line, offset)

      assert len(line) == offset + 1

      out.token = token
      return out




