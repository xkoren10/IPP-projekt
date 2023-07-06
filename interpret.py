"""IPP projekt 2022
@file interpret.py
@author Matej Koren
"""
import sys
import re
from argparse import ArgumentParser
import xml.etree.ElementTree as El_tree
from sys import stderr
import os.path

""" Chybové kódy """
exit_ok = 0
missing_or_wrong_parameter = 10  # chybějící parametr skriptu (je-li třeba) nebo použití zakázané kombinace parametrů;
error_opening_input = 11  # chyba při otevírání vstupních souborů (např. neexistence, nedostatečné oprávnění);
error_opening_output = 12  # chyba při otevření výstupních souborů pro zápis
not_well_formatted_XML = 31  # chybný XML formát ve vstupním souboru;
unexpected_XML_structure = 32  # neočekávaná struktura XML;
semantic_error = 52  # chyba při sémantických kontrolách vstupního kódu v IPPcode22;
wrong_operand = 53  # běhová chyba interpretace – špatné typy operandů;
undefined_variable = 54  # běhová chyba interpretace – přístup k neexistující proměnné (rámec existuje);
undefined_frame = 55  # běhová chyba interpretace – rámec neexistuje (např. čtení z prázdného zásobníku rámců);
missing_value = 56  # běhová chyba interpretace – chybějící hodnota
bad_operand_value = 57  # běhová chyba interpretace – špatná hodnota operandu
string_error = 58  # běhová chyba interpretace – chybná práce s řetězcem.

""" Trieda pre argumenty """
class Argument:
    def __init__(self, arg_type, value):
        self.type = arg_type
        self.val = value


""" Trieda pre náveste """
class Label:
    def __init__(self, name, position):
        self.name = name
        self.position = position


""" Trieda pre inštrukcie """
class Instruction:
    def __init__(self, name, number):
        self.name = name
        self.number = number
        self.arguments = []

    def add_arguments(self, argument):
        self.arguments.append(argument)


""" Trieda pre premenné """
class Variable:
    def __init__(self, name, variable_type, value):
        self.name = name
        self.varType = variable_type
        self.value = value


""" Funkcia kontrolujúca výskyt premennej v zozname"""
def find_variable(array, name):
    if name in array.keys():
        return True
    return False


""" Funkcia kontrolúca zhodu typu a hodnoty"""
def check_type(type_to_check, value_to_check):

    try:
        if type_to_check == "int":
            if re.match('^([+-]?[0-9]+$)', value_to_check):
                return True
        elif type_to_check == "string":
            if re.match('^(((?!\\\\)\\S)|(\\\\\\d{3}))*$', value_to_check):
                return True
        elif type_to_check == "bool":
            if re.match('^(true|false)$', value_to_check):
                return True
        elif type_to_check == "nil":
            if re.match('^(nil)$', value_to_check):
                return True
        elif type_to_check == "label":
            if re.match('^([a-zA-Z_\\-$&%*!?][\\w\\-$&%*!?]*)$', value_to_check):
                return True
        elif type_to_check == "type":
            if re.match('^(int|bool|string|nil|float)$', value_to_check):
                return True
        elif type_to_check == "var":
            if re.match('^((?:LF|GF|TF)@[a-zA-Z_\\-$&%*!?]*)$', value_to_check):
                return True
        else:
            return False
    except:
        exit(missing_value)


""" Spracovanie argumentov """
if len(sys.argv) > 2 and ('--help' in sys.argv):
    exit(missing_or_wrong_parameter)

parser = ArgumentParser(description='Skript načíta XML reprezentáciu programu a tento program s využitím'
                                    'vstupu podľe parametrov interpretuje a generuje výstup.'
                                    'Aspoň jeden z parametrov (--source alebo --input) musí byť vždy zadaný.'
                                    'Ak jeden z nich chýba, dáta sú načítáné zo štandardného vstupu.',
                        usage=' interpret.py [--help] [--source=SOURCE] [--input=INPUT]')
parser.add_argument('--source', help='Vstupný súbor s XML reprezentáciou zdrojového kódu.', type=str)
parser.add_argument('--input', help='Súbor so vstupmi pre interpretáciu zadaného zdrojového kódu', type=str)

cmd_args = parser.parse_args()

""" Chýbajúce argumenty """
if cmd_args.source is None and cmd_args.input is None:
    exit(missing_or_wrong_parameter)

""" Nastavenie vstupu --source """
if cmd_args.source is not None:

    source = cmd_args.source

else:
    source = sys.stdin

""" Nastavenie vstupu --input """
if cmd_args.input is not None:

    inputs = cmd_args.input

else:
    inputs = sys.stdin

""" Načítanie XML súboru"""
try:
    tree = El_tree.parse(source)
    root = tree.getroot()
except:
    exit(not_well_formatted_XML)
    # exit(error_opening_input)

""" Kontrola výskytu potrebných častí """
if root.tag != 'program':
    exit(unexpected_XML_structure)

if "language" in root.attrib:
    language = root.attrib["language"]
    if language.upper() != "IPPCODE22":
        exit(unexpected_XML_structure)
    del root.attrib["language"]
else:
    exit(unexpected_XML_structure)


""" Slovníky pre inštrukcie, premenné a návestia """
instruction_array = {}
label_array = {}
var_array = {}
call_stack = []
value_stack = []


""" Načítanie inštrukcie"""
for child in root:
    if child.tag != 'instruction':
        exit(unexpected_XML_structure)
    child_att = list(child.attrib.keys())
    if not ('opcode' in child_att) or not ('order' in child_att):
        exit(unexpected_XML_structure)

    if not check_type("int", child.attrib["order"]):
        exit(unexpected_XML_structure)
    if int(child.attrib["order"]) < 1:
        exit(unexpected_XML_structure)

    """ Vytvorenie novej inštrukcie """
    new_instruction = Instruction(child.attrib["opcode"], int(child.attrib["order"]))

    """ Kontrola výskytu argumentov """
    for sub_element in child:
        if not (re.match(r"arg[123]", sub_element.tag)):
            exit(unexpected_XML_structure)
        arg_val = sub_element.text

        if not (sub_element.text is None):
            if not check_type(sub_element.attrib["type"], sub_element.text):
                exit(semantic_error)

        """ Vytvorenie nového argumentu """
        new_argument = Argument(sub_element.attrib["type"], arg_val)

        """ Priradenie nového argumentu pre inštrukciu """
        for args in new_instruction.arguments:
            if args == new_argument:
                exit(semantic_error)
        new_instruction.add_arguments(new_argument)

    """ Pridanie inštrukcie do slovníku ( ak ešte neexistuje rovnaká ) """
    for inst in instruction_array:
        if new_instruction.number == inst:
            exit(unexpected_XML_structure)
    instruction_array[new_instruction.number] = new_instruction

""" Zoradenie inštrukcíi podľa ["order"] """
instruction_array = dict(sorted(instruction_array.items()))

index = 0
translate = {}

""" Prepísanie poradia počnúc '1' """
for k, v in instruction_array.items():
    index += 1
    new_key = index
    translate[k] = new_key

for old, new in translate.items():
    instruction_array[new] = instruction_array.pop(old)


""" Prehľadanie poľa inštrukcií pre výskyt návestí (správnosť skokov vpred) """
for instruction in instruction_array.keys():
    if instruction_array[instruction].name == "LABEL":
        if check_type("label", instruction_array[instruction].arguments[0].val):

            """ Vytvorenie nového návestia """
            new_label = Label(instruction_array[instruction].arguments[0].val, instruction)
            if new_label.name in label_array:
                exit(semantic_error)

            """ Pridanie návestia do zoznamu (ak ešte neexistuje) """
            label_array[new_label.name] = new_label
        else:

            exit(wrong_operand)

i = 1

""" Hlavný cyklus na prechod inštrukciami """
while i <= len(instruction_array) + 1:

    """ Inštrukcie LABEL boli už spracované"""
    if i not in instruction_array.keys() or instruction_array[i].name == "LABEL":
        i += 1
        continue

    """ Definícia premennej """
    if instruction_array[i].name == "DEFVAR":

        """ Kontrola parametrov"""
        if check_type("var", instruction_array[i].arguments[0].val):
            var = instruction_array[i].arguments[0].val.split('@')
            new_variable = Variable(var[1], None, None)
            if new_variable.name in var_array.keys():
                exit(semantic_error)

            """ Pridanie premennej do zoznamu """
            var_array[new_variable.name] = new_variable
        else:
            exit(wrong_operand)

        """ Návrat z funkcie"""
    elif instruction_array[i].name == "RETURN":
        if len(call_stack) == 0:
            exit(missing_value)
        i = call_stack.pop()

        """ Návrat hodnoty zo zásobníka"""
    elif instruction_array[i].name == "POPS":

        """ Argument musí byť premenná"""
        if check_type("var", instruction_array[i].arguments[0].val):
            pop_var = instruction_array[i].arguments[0].val.split('@')
            if not find_variable(var_array, pop_var[1]):
                exit(undefined_variable)

        if len(value_stack) == 0:
            exit(missing_value)

        var_array[pop_var[1]].value = value_stack.pop()

        """ Výpis na štandardný chýbový výstup"""
    elif instruction_array[i].name == "BREAK":
        print("Pozícia v kóde: ", i, ". inštrukcia\n",
              "Kód inštrukcie: ", instruction_array[i].name,"\n",
              "Obsah globálneho rámcu: ", var_array, "\n",
              file=stderr, end='')

        """ Pridanie hodnoty na zásobník """
    elif instruction_array[i].name == "PUSHS":

        """ Argument musí byť premenná/symbol -> val1 """
        if check_type("var", instruction_array[i].arguments[0].val):
            push_var = instruction_array[i].arguments[0].val.split('@')
            if check_type("type", instruction_array[i].arguments[1].type):
                if not find_variable(var_array, push_var[1]):
                    exit(semantic_error)
            val1 = var_array[push_var[1]].value
            value_stack.append(val1)

        elif check_type("type", instruction_array[i].arguments[0].type):
            val1 = instruction_array[i].arguments[0].val
            value_stack.append(val1)
        else:
            exit(semantic_error)

        """ Volanie funkcie """
    elif instruction_array[i].name == "CALL":
        if check_type("label", instruction_array[i].arguments[0].val):
            jump_label = instruction_array[i].arguments[0].val
            if jump_label in label_array.keys():
                call_stack.append(i+1)
                """ Poradie práve vykonávanej inštrukcie sa nastaví na pozíciu, na ktorej sa nachádza návestie"""
                i = label_array[jump_label].position

            else:
                exit(semantic_error)
        else:

            exit(wrong_operand)

        """ Nepodmienený skok """
    elif instruction_array[i].name == "JUMP":
        if check_type("label", instruction_array[i].arguments[0].val):
            jump_label = instruction_array[i].arguments[0].val
            if jump_label in label_array.keys():

                """ Poradie práve vykonávanej inštrukcie sa nastaví na pozíciu, na ktorej sa nachádza návestie"""
                i = label_array[jump_label].position

            else:
                exit(semantic_error)
        else:

            exit(wrong_operand)

        """ Presun hodnôt """
    elif instruction_array[i].name == "MOVE":

        """ Kontrola prvého argumentu """
        if check_type("var", instruction_array[i].arguments[0].val):
            move_var = instruction_array[i].arguments[0].val.split('@')
            if check_type("type", instruction_array[i].arguments[1].type):
                if not find_variable(var_array, move_var[1]):
                    exit(undefined_variable)

                    """ Presun zo symbolu do premennej """
                var_array[move_var[1]].value = instruction_array[i].arguments[1].val
                var_array[move_var[1]].varType = instruction_array[i].arguments[1].type

        elif instruction_array[i].arguments[1].type == "var":
            if check_type("var", instruction_array[i].arguments[1].val):
                source_var = instruction_array[i].arguments[1].val.split('@')
                if not find_variable(var_array, source_var[1]):
                    exit(undefined_variable)
            else:
                exit(wrong_operand)

                """ Presun z premennej do premennej """
            var_array[move_var[1]].value = var_array[source_var[1]].value
            var_array[move_var[1]].varType = var_array[source_var[1]].varType
        else:
            exit(wrong_operand)

    elif instruction_array[i].name == "STRLEN":

        """ Kontrola prvého argumentu """
        if check_type("var", instruction_array[i].arguments[0].val):
            strlen_var = instruction_array[i].arguments[0].val.split('@')
            if check_type("type", instruction_array[i].arguments[1].type):
                if not find_variable(var_array, strlen_var[1]):
                    exit(undefined_variable)

                    """ Presun zo symbolu do premennej """
                var_array[move_var[1]].value = len(instruction_array[i].arguments[1].val)
                var_array[move_var[1]].varType = "int"

        elif instruction_array[i].arguments[1].type == "var":
            if check_type("var", instruction_array[i].arguments[1].val):
                strlen_src_var = instruction_array[i].arguments[1].val.split('@')
                if not find_variable(var_array, strlen_src_var[1]):
                    exit(undefined_variable)
            else:
                exit(wrong_operand)

                """ Presun z premennej do premennej """
            var_array[move_var[1]].value = len(var_array[source_var[1]].value)
            var_array[move_var[1]].varType = "string"
        else:
            exit(wrong_operand)

        """ Výpis na štandardný výstup """
    elif instruction_array[i].name == "WRITE":

        """ Výpis symbolu """
        if check_type("type", instruction_array[i].arguments[0].type):

            """ Odstránenie escape sekvencii """
            if instruction_array[i].arguments[0].type == "string":
                escapedList = re.findall(r'(\\[0-9]{3})+', instruction_array[i].arguments[0].val)
                if len(escapedList) > 0:
                    for escapedUnicode in escapedList:
                        unicodeAsChar = chr(int(escapedUnicode[1:]))
                        value = instruction_array[i].arguments[0].val.replace(escapedUnicode, unicodeAsChar)
                        print(value, end='')
                else:
                    print(instruction_array[i].arguments[0].val, end='')
            else:
                print(instruction_array[i].arguments[0].val, end='')

            """ Výpis z premennej """
        elif instruction_array[i].arguments[0].type == "var":

            if check_type("var", instruction_array[i].arguments[0].val):
                write_var = instruction_array[i].arguments[0].val.split('@')
                if not find_variable(var_array, write_var[1]):
                    exit(undefined_variable)

                    """ Odstránenie escape sekvencii """
                if var_array[write_var[1]].varType == "string":
                    escapedList = re.findall(r'(\\[0-9]{3})+', var_array[write_var[1]].value)
                    if len(escapedList) > 0:
                        for escapedUnicode in escapedList:
                            unicodeAsChar = chr(int(escapedUnicode[1:]))
                            value = var_array[write_var[1]].value.replace(escapedUnicode, unicodeAsChar)
                            print(value, end='')
                    else:
                        print(var_array[write_var[1]].value, end='')
                else:
                    print(var_array[write_var[1]].value, end='')
            else:
                exit(wrong_operand)
        else:
            exit(wrong_operand)

        """ Ukončenie programu """
    elif instruction_array[i].name == "EXIT":

        """ Ukončenie s hodnotou zo symbolu (integer) """
        if re.match('^(int)$', instruction_array[i].arguments[0].type):
            if check_type("int", instruction_array[i].arguments[0].val):
                exit(int(instruction_array[i].arguments[0].val))
            else:
                exit(wrong_operand)
            """ Ukončenie s hodnotou z premennej (integer) """
        elif instruction_array[i].arguments[0].type == "var":
            if check_type("var", instruction_array[i].arguments[0].val):
                exit_var = instruction_array[i].arguments[0].val.split('@')
                if not find_variable(var_array, exit_var[1]):
                    exit(semantic_error)
                if var_array[exit_var[1]].varType == "int":
                    exit(int(var_array[exit_var[1]].value))
            exit(wrong_operand)
        else:
            exit(wrong_operand)


        """ Aritmetické inštrukcie """
    elif instruction_array[i].name in ['MUL', 'ADD', 'SUB', 'IDIV']:

        """ Prvý argument musí byť premenná -> arithmetic_var """
        if check_type("var", instruction_array[i].arguments[0].val):
            arithmetic_var = instruction_array[i].arguments[0].val.split('@')
            if not find_variable(var_array, arithmetic_var[1]):
                exit(undefined_variable)
        else:
            exit(wrong_operand)

        """ Druhý argument: symbol/ premenná -> val1 """
        if (check_type("int", instruction_array[i].arguments[1].val)) and \
                (instruction_array[i].arguments[1].type == "int"):
            val1 = int(instruction_array[i].arguments[1].val)
        elif check_type("var", instruction_array[i].arguments[1].val) and \
                (instruction_array[i].arguments[1].type == "var"):
            add_var1 = instruction_array[i].arguments[1].val.split('@')
            if not find_variable(var_array, add_var1[1]):
                exit(undefined_variable)
            if check_type("int", var_array[add_var1[1]].varType):
                val1 = var_array[add_var1[1]]
        else:
            exit(wrong_operand)

        """ Tretí argument: symbol/ premenná -> val2 """
        if (check_type("int", instruction_array[i].arguments[2].val)) and \
                (instruction_array[i].arguments[2].type == "int"):
            val2 = int(instruction_array[i].arguments[2].val)
        elif (check_type("var", instruction_array[i].arguments[2].val)) and \
                (instruction_array[i].arguments[2].type == "var"):
            add_var2 = instruction_array[i].arguments[2].val.split('@')
            if not find_variable(var_array, add_var2[1]):
                exit(undefined_variable)
            if check_type("int", var_array[add_var2[1]]):
                val2 = var_array[add_var2[1]]
        else:
            exit(wrong_operand)

        """ Druh aritmetickej operácie """
        if instruction_array[i].name == "SUB":
            var_array[arithmetic_var[1]].value = int(val1 - val2)
            var_array[arithmetic_var[1]].varType = "int"
        if instruction_array[i].name == "ADD":
            var_array[arithmetic_var[1]].value = int(val1 + val2)
            var_array[arithmetic_var[1]].varType = "int"
        if instruction_array[i].name == "MUL":
            var_array[arithmetic_var[1]].value = int(val1 * val2)
            var_array[arithmetic_var[1]].varType = "int"
        if instruction_array[i].name == "IDIV":
            if val2 == 0:
                exit(wrong_operand)
            var_array[arithmetic_var[1]].value = int(val1 / val2)
            var_array[arithmetic_var[1]].varType = "int"

        """ Vrátenie typu """
    elif instruction_array[i].name == "TYPE":

        """ Prvý argument musí byť premenná -> dest_var """
        if check_type("var", instruction_array[i].arguments[0].val):
            dest_var = instruction_array[i].arguments[0].val.split('@')
            if not find_variable(var_array, dest_var[1]):
                exit(undefined_variable)
        else:
            exit(wrong_operand)

        """ Druhý argument: premenná/symbol -> val1"""
        if check_type("type", instruction_array[i].arguments[1].type):
            val1 = instruction_array[i].arguments[1].type
        elif check_type("var", instruction_array[i].arguments[1].val):

            type_var = instruction_array[i].arguments[1].val.split('@')
            if not find_variable(var_array, type_var[1]):
                exit(undefined_variable)
            val1 = var_array[type_var[1]].varType
            if val1 is None:
                val1 = ""

        else:
            exit(wrong_operand)

        """ Uloženie typu do premennej dest_var """
        var_array[dest_var[1]].value = val1

        """ Štandardný chybový výstup"""
    elif instruction_array[i].name == "DPRINT":

        """ Argument je type premenná alebo symbol """
        if check_type("type", instruction_array[i].arguments[0].type):

            """ Výpis hodnoty na chybový výstup"""
            print(instruction_array[i].arguments[0].val, file=stderr, end='')

        elif instruction_array[i].arguments[0].type == "var":
            if check_type("var", instruction_array[i].arguments[0].val):
                exit_var = instruction_array[i].arguments[0].val.split('@')
                if not find_variable(var_array, exit_var[1]):
                    exit(undefined_variable)

                    """ Výpis hodnoty na chybový výstup"""
                print(var_array[exit_var[1]].value, file=stderr, end='')
            exit(wrong_operand)
        else:
            exit(wrong_operand)

        """ Práca s reťazcami """
    elif instruction_array[i].name in ["CONCAT", "STRI2INT", "SETCHAR", "GETCHAR"]:
        """" Prvý argument musí byť premenná -> logic_var """
        if check_type("var", instruction_array[i].arguments[0].val):
            concat_var = instruction_array[i].arguments[0].val.split('@')
            if not find_variable(var_array, concat_var[1]):
                exit(undefined_variable)
        else:
            exit(wrong_operand)

            """ Druhý argument: premenná/symbol -> val1 """
        if check_type("type", instruction_array[i].arguments[1].type):
            if instruction_array[i].arguments[1].type == "string":
                val1 = instruction_array[i].arguments[1].val
            else:
                exit(wrong_operand)
        elif check_type("var", instruction_array[i].arguments[1].val) and \
                (instruction_array[i].arguments[1].type == "var"):
            concat_var1 = instruction_array[i].arguments[1].val.split('@')
            if not find_variable(var_array, concat_var1[1]):
                exit(undefined_variable)
            if var_array[concat_var1[1]].type == "string":
                val1 = var_array[concat_var1[1]].value
            else:
                exit(wrong_operand)

            """ Tretí argument: premenná/symbol -> val2 """
            if check_type("type", instruction_array[i].arguments[2].type):
                if instruction_array[i].arguments[2].type == "string":
                    val2 = instruction_array[i].arguments[2].val
                else:
                    exit(wrong_operand)
            elif check_type("var", instruction_array[i].arguments[2].val) and \
                    (instruction_array[i].arguments[2].type == "var"):
                concat_var2 = instruction_array[i].arguments[2].val.split('@')
                if not find_variable(var_array, concat_var2[1]):
                    exit(undefined_variable)
                if var_array[concat_var2[1]].type == "string":
                    val1 = var_array[concat_var2[1]].value
                else:
                    exit(wrong_operand)
                val2 = var_array[concat_var2[1]].value

            """ Delenie podľa operačných kódov """
            if instruction_array[i].name == "CONCAT":
                var_array[concat_var[1]].value = val1 + val2
            elif instruction_array[i].name == "STRRI2INT":
                try:
                    var_array[concat_var[1]].value = ord(val1[val2])
                except ValueError:
                    exit(string_error)
            elif instruction_array[i].name == "SETCHAR":
                val2set = var_array[concat_var[1]].value
                val2set[val1] = val2[:0]
                var_array[concat_var[1]].value = val2set
            elif instruction_array[i].name == "GETCHAR":
                var_array[concat_var[1]].value=val1[val2]

        """ ASCII reprezentácia čísla """
    elif instruction_array[i].name == "INT2CHAR":

        """" Prvý argument musí byť premenná -> int2char_var """
        if check_type("var", instruction_array[i].arguments[0].val):
            int2char_var = instruction_array[i].arguments[0].val.split('@')
            if not find_variable(var_array, int2char_var[1]):
                exit(undefined_variable)

                """ Druhý argument: symbol/premenná """
            if not re.match('^(int)$', instruction_array[i].arguments[1].type):
                exit(semantic_error)
            if check_type("int", instruction_array[i].arguments[1].val):

                """ Prepis na stringovú reprezentáciu celočíselnej hodnoty"""
                try:
                    var_array[int2char_var[1]].value = chr(int(instruction_array[i].arguments[1].val))
                except ValueError:
                    exit(string_error)
                var_array[int2char_var[1]].varType = "string"

        elif instruction_array[i].arguments[1].type == "var":
            if check_type("var", instruction_array[i].arguments[1].val):
                int2char_source_var = instruction_array[i].arguments[1].val.split('@')
                if not find_variable(var_array, int2char_source_var[1]):
                    exit(undefined_variable)
            else:
                exit(wrong_operand)

                """ Prepis na stringovú reprezentáciu celočíselnej hodnoty"""
            try:
                var_array[move_var[1]].value = chr(int(var_array[int2char_source_var[1]].value))
            except ValueError:
                exit(string_error)
            var_array[move_var[1]].varType = "string"

        """ Porovnávacie inštrukcie """
    elif instruction_array[i].name in ['LT', 'GT', 'EQ', 'AND', 'OR', 'NOT']:

        """" Prvý argument musí byť premenná -> logic_var """
        if check_type("var", instruction_array[i].arguments[0].val):
            logic_var = instruction_array[i].arguments[0].val.split('@')
            if not find_variable(var_array, logic_var[1]):
                exit(undefined_variable)
        else:
            exit(wrong_operand)

            """ Druhý argument: premenná/symbol -> val1 """
        if check_type("type", instruction_array[i].arguments[1].type):
            if instruction_array[i].arguments[1].type == "int":
                val1 = int(instruction_array[i].arguments[1].val)
            else:
                val1 = instruction_array[i].arguments[1].val
        elif check_type("var", instruction_array[i].arguments[1].val) and \
                (instruction_array[i].arguments[1].type == "var"):
            logic_var1 = instruction_array[i].arguments[1].val.split('@')
            if not find_variable(var_array, logic_var1[1]):
                exit(undefined_variable)
            val1 = var_array[logic_var1[1]].value

            """ Tretí argument: premenná/symbol -> val2 """
        if instruction_array[i].name != "NOT":
            if check_type("type", instruction_array[i].arguments[2].type):
                if instruction_array[i].arguments[2].type == "int":
                   val2 = int(instruction_array[i].arguments[2].val)
                else:
                    val2 = instruction_array[i].arguments[2].val
            elif check_type("var", instruction_array[i].arguments[2].val) and \
                    (instruction_array[i].arguments[2].type == "var"):
                logic_var2 = instruction_array[i].arguments[2].val.split('@')
                if not find_variable(var_array, logic_var2[1]):
                    exit(undefined_variable)
                val2 = var_array[logic_var2[1]].value

        """ Ak sa zhodujú typy, vykoná sa zadaná logická operácia """
        if instruction_array[i].arguments[2].type == instruction_array[i].arguments[1].type:

            if (instruction_array[i].name == "LT") and (instruction_array[i].arguments[2].type != "nil" or
                                                        instruction_array[i].arguments[1].type != "nil"):

                if val1 < val2:
                    var_array[logic_var[1]].value = "true"
                else:
                    var_array[arithmetic_var[1]].value = "false"

            if (instruction_array[i].name == "GT") and (instruction_array[i].arguments[2].type != "nil" or
                                                        instruction_array[i].arguments[1].type != "nil"):
                if val1 > val2:
                    var_array[logic_var[1]].value = "true"
                else:
                    var_array[logic_var[1]].value = "false"

            if instruction_array[i].name == "EQ":
                if val1 == val2:
                    var_array[logic_var[1]].value = "true"
                else:
                    var_array[logic_var[1]].value = "false"

            if instruction_array[i].name == "AND":

                if val1 == val2 == "true":
                    var_array[logic_var[1]].value = "true"
                else:
                    var_array[logic_var[1]].value = "false"

            if instruction_array[i].name == "OR":
                if (val1 == val2 == "true") or\
                        (val1 == val2 == "false"):
                    var_array[logic_var[1]].value = "false"
                else:
                    var_array[logic_var[1]].value = "true"

        elif instruction_array[i].name == "NOT":
            if val1 == "true":
                var_array[logic_var[1]].value = "false"
            if val1 == "false":
                var_array[logic_var[1]].value = "true"
            else:
                exit(wrong_operand)

        else:
            exit(wrong_operand)
        var_array[logic_var[1]].varType = "bool"

    elif instruction_array[i].name in ['JUMPIFEQ', 'JUMPIFNEQ']:

        """" Prvý argument musí byť label -> jump_label """
        if check_type("label", instruction_array[i].arguments[0].val):
            jump_label = instruction_array[i].arguments[0].val
            if jump_label not in label_array.keys():
                exit(semantic_error)

            """ Druhý argument: premenná/symbol -> val1 """
        if check_type("type", instruction_array[i].arguments[1].type):
            if instruction_array[i].arguments[1].type == "int":
                val1 = int(instruction_array[i].arguments[1].val)
            else:
                val1 = instruction_array[i].arguments[1].val
        elif check_type("var", instruction_array[i].arguments[1].val) and \
                (instruction_array[i].arguments[1].type == "var"):
            jump_var1 = instruction_array[i].arguments[1].val.split('@')
            if not find_variable(var_array, jump_var1[1]):
                exit(undefined_variable)
            val1 = var_array[jump_var1[1]].value

            """ Tretí argument: premenná/symbol -> val2 """
        if check_type("type", instruction_array[i].arguments[2].type):
            if instruction_array[i].arguments[2].type == "int":
                val2 = int(instruction_array[i].arguments[2].val)
            else:
                val2 = instruction_array[i].arguments[2].val
        elif check_type("var", instruction_array[i].arguments[2].val) and \
                (instruction_array[i].arguments[2].type == "var"):
            jump_var2 = instruction_array[i].arguments[2].val.split('@')
            if not find_variable(var_array, jump_var2[1]):
                exit(undefined_variable)
            val2 = var_array[jump_var2[1]].value

        if instruction_array[i].arguments[2].type == instruction_array[i].arguments[1].type:
            if instruction_array[i].name == "JUMPIFEQ":
                if val1 == val2:
                    i = label_array[jump_label].position

            if instruction_array[i].name == "JUMPIFNEQ":
                if val1 != val2:
                    i = label_array[jump_label].position
        else:
            exit(wrong_operand)

        """ Neimplementované funkcie"""
    elif instruction_array[i].name in ['CREATEFRAME', 'POPFRAME', 'PUSHFRAME', 'READ']:
        pass

        """ Neznáma inštrukcia """
    else:
        exit(unexpected_XML_structure)

    """ Inkrementácia počítadla """
    i += 1
