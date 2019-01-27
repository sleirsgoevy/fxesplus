#!/usr/bin/python3
import re
import sys
import argparse

from lib_570esp import *

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--target', default='overflow',
		choices=('none', 'overflow', 'loader', 'loader2'),
		help='how will the output be used')
parser.add_argument('-f', '--format', default='key',
		choices=('hex', 'key'),
		help='output format')
args = parser.parse_args()

def note(st):
	''' Print st to stderr. Used for additional information (note, warning) '''
	sys.stderr.write(st)

def canonicalize(st):
	''' Make (st) canonical. '''
	if '$' in st:
		st1, st2 = st.split('$', 1)
		return canonicalize(st1) + '$' + st2
	st = st.lower()
	st = st.strip()
	# remove spaces around non alphanumeric
	st = re.sub(r' *([^a-z0-9]) *', r'\1', st)
	return st

def del_inline_comment(line):
	return (line+'#')[:line.find('#')].rstrip()

def add_command(command_dict, address, command, tags, debug_info=''):
	''' Add a command to command_dict. '''
	assert command, f'Empty command {debug_info}'
	assert type(command_dict) is dict

	for disallowed_prefix in '0x', 'call', 'goto', 'adr_of':
		assert not command.startswith(disallowed_prefix), \
		f'Command ends with "{disallowed_prefix}" {debug_info}'
	assert not command.endswith(':'), \
		f'Command ends with ":" {debug_info}'
	assert ';' not in command, \
		f'Command contains ";" {debug_info}'

	# this is inefficient
	prev_command = command_dict.get(command, None)
	for adr, tags in command_dict.values():
		if adr == address:
			prev_command = (adr, tags)
			break
	assert prev_command is None, f'Command {command} appears twice - ' \
		f'first: {prev_command[0]:05X} {prev_command[1]}, ' \
		f'second: {address:05X} {tags},' \

	command_dict[command] = (address, tuple(tags))


def get_commands(filename, commands=None):
	''' Read a list of gadget names.

	Args:
		commands: A dict to append result to. Not passing any creates a new dict.

	Return:
		A dict of {name: (address, tags)}
	'''
	with open(filename, 'r') as f:
		data = f.read().splitlines()

	if commands is None: commands = {}
	in_comment = False
	line_regex = re.compile('([0-9a-fA-F]+)\s+(.+)')
	for line_index, line in enumerate(data):
		line = line.strip()

		# multi-line comments
		if line == '/*':
			in_comment = True
			continue
		if line == '*/':
			in_comment = False
			continue
		if in_comment:
			continue

		line = del_inline_comment(line)
		if not line: continue

		match = line_regex.fullmatch(line)
		address, command = match[1], match[2]

		command = canonicalize(command)

		tags = [] # process tags (leading `{...}`)
		while command and command[0] == '{':
			i = command.find('}')
			if i < 0:
				raise Exception(f'Line {line_index} '
					'has unmatched "{"');
			tags.append(command[1:i])
			command = command[i+1:]

		try:
			address = int(address, 16)
		except ValueError:
			raise Exception(f'Line {line_index} has invalid address: {address!r}')

		add_command(commands, address, command, tags, f'at {filename}:{line_index}')

	return commands

def get_disassembly(filename):
	'''Try to parse a disassembly file with annotated address.

	Each line should look like this:

		mov r2, 1                      ; 0A0A2 | 0201

	Return:
		A list of strings.
	'''
	with open(filename, 'r') as f:
		data = f.read().splitlines()

	line_regex = re.compile(r'\t(.*?)\s*; ([0-9a-fA-F]*) \|')
	disasm = []
	for line in data:
		match = line_regex.match(line)  # match prefix
		if match:
			addr = int(match[2], 16)
			while addr >= len(disasm): disasm.append('')
			disasm[addr] = match[1]
	return disasm
disasm = get_disassembly('fx_570es+_disas.txt')

def read_rename_list(filename, commands=None, datalabels=None):
	'''Try to parse a rename list.

	If the rename list is ambiguous without disassembly, it raises an error.

	Args:
		commands: A dict to add result to. Not passing any creates a new dict.
		datalabels: A dict to add result to. Not passing any creates a new dict.

	Return:
		A tuple (commands, datalabels), where
		`commands` has the form {name: (address, tags)}
		`datalabels` has the form {name: address}
	'''
	with open(filename, 'r') as f:
		data = f.read().splitlines()

	if commands is None: commands = {}
	if datalabels is None: datalabels = {}
	line_regex   = re.compile(r'^\s*([\w_.]+)\s+([\w_.]+)')
	global_regex = re.compile(r'f_([0-9a-fA-F]+)')
	local_regex  = re.compile(r'.l_([0-9a-fA-F]+)')
	data_regex   = re.compile(r'd_([0-9a-fA-F]+)')
	hexadecimal  = re.compile(r'[0-9a-fA-F]+')

	last_global_label = None
	for line_index, line in enumerate(data):
		match = line_regex.match(line)
		if not match: continue
		raw, real = match[1], match[2]
		if real.startswith('.'):
			# we don't get local labels.
			continue

		match = data_regex.fullmatch(raw)
		if match:
			addr = int(match[1], 16)
			datalabels[real] = addr
			continue

		addr = None
		if hexadecimal.fullmatch(raw):
			addr = int(raw, 16)
			last_global_label = None
			# because we don't know whether this label is global or local
		else:
			match = global_regex.match(raw)
			if match:
				addr = int(match[1], 16)
				if len(match[0]) == len(raw):  # global_regex.fullmatch
					last_global_label = addr
				else:
					match = local_regex.fullmatch(raw[len(match[0]):])
					if match:  # full address f_12345.l_67
						addr += int(match[1], 16)
			else:
				match = local_regex.fullmatch(raw)
				if match:
					addr = last_global_label + int(match[1], 16)

		if addr is not None:
			assert addr < len(disasm), f'{addr:05X}'
			if disasm[addr].startswith('push lr'):
				tags = 'del lr',
				addr += 2
			else:
				tags = 'rt',
				a1 = addr + 2
				while not any(disasm[a1].startswith(x) for x in ('push lr', 'pop pc', 'rt')): a1 += 2
				if not disasm[a1].startswith('rt'):
					tags = tags + ('del lr',)

			if real in commands:
				if 'override rename list' in commands[real][1]:
					continue
				if commands[real] == (addr, tags):
					note(f'Warning: Duplicated command {real}\n')
					continue

			add_command(commands, addr, real, tags=tags, debug_info=f'at {filename}:{line_index}')
		else:
			raise ValueError('Invalid line: ' + repr(line))

	return commands, datalabels

commands = {}
get_commands('builtins', commands)
commands, datalabels = read_rename_list('570es+_names.txt', commands)

def sizeof_register(reg_name):
	# assume reg_name is a valid register name
	return {'r':1,'e':2,'x':4,'q':8}[reg_name[0]]

program = sys.stdin.read().split('\n')

result = [] # list of ints in range 0..255
labels = {}
adr_of_cmds = [] # list of (source adr, offset, target label)

# Right after the buffer overflow, the memory region [home..home+len(result)[
# should have value = result (after replacing labels)
home = None

def process(line):
	# the processing result will affect those variables
	global result, labels, adr_of_cmds, home

	if not line: # empty line
		pass

	elif ';' in line:
		''' Compound statement. Syntax:
		`<statement1> ; <statement2> ; ...`
		'''
		for command in line.split(';'): process(command)

	elif line[-1] == ':':
		''' Syntax: `<label>:`
		Special: If the label is 'home', it specifies the point to
		start program execution. By default it's at the begin.
		'''
		label = line[:-1]
		assert label not in labels, f'Duplicated label: {label}'
		labels[label] = len(result)

	elif line.startswith('0x'):
		''' Syntax: `0x<hexadecimal digits>` '''
		assert len(line)%2==0, f'Invalid data length: {line}'
		n_byte = len(line)//2-1
		data = int(line, 16)
		for _ in range(n_byte):
			result.append(data&0xFF)
			data>>=8

	elif line.startswith('call'):
		''' Syntax: `call <address>` or `call <built-in>`. '''
		try:
			adr = int(line[4:], 16)
		except ValueError:
			adr, tags = commands[line[4:].strip()]
			for tag in tags:
				if tag.startswith('warning'):
					note(tag+'\n')

		assert 0 <= adr < 0x20000, f'Invalid address: {adr}'
		adr = optimize_adr_for_npress(adr)
		process(f'0x{adr+0x30300000:0{8}x}')

	elif line.startswith('goto'):
		''' Syntax: `goto <label>` '''
		label = line[4:]
		process(f'er14 = adr_of [-2] {label}')
		process('call sp=er14,pop er14')

	elif line.startswith('adr_of'):
		''' Syntax: `adr_of [offset] <label>` | `adr_of <label>` '''
		line = line[6:].strip()
		if line[0] == '[':
			i = line.index(']')
			offset = int(line[1:i])
			label = line[i+1:].strip()
		else:
			offset = 0
			label = line.strip()

		adr_of_cmds.append((len(result), offset, label))
		result.extend((0,0))

	elif line in datalabels:
		''' `<label>`. '''
		process(f'{line}+0')

	elif '+' in line and line[:line.find('+')] in datalabels:
		''' `<label> + <offset>`. '''
		label, offset = line.split('+')
		process(f'0x{datalabels[label]+int(offset,0):04x}')

	elif line in commands:
		''' `<built-in>`. Equivalent to `call <built-in>`. '''
		process('call '+line)

	elif '=' in line:
		''' Syntax:
		`register = <value> [, adr_of <label> [, ...]]`
		'''
		i = line.index('=')
		register, value = line[:i], line[i+1:].lstrip()

		assert '=' not in value, f'Nested assignment in {line}'
		value = value.replace(',', ';')

		process(f'call pop {register}')

		l1 = len(result)
		process(value)
		assert len(result)-l1==sizeof_register(register), \
				f'Line {line!r} source/destination target mismatches'

	elif line[0] == '$':
		''' Python eval. The result will be processed as commands. '''
		x = eval(line[1:])
		if isinstance(x, str):
			process(x)
		elif isinstance(x, list) or isinstance(x, tuple):
			for command in x:
				process(x)

	elif line.startswith('org'):
		''' Syntax: `org <expr>`

		Specify the address of this location after mapping.
		Only use this for loader mode.
		'''
		hx = eval(line[3:])
		home1 = hx - len(result)
		assert home is None or home == home1, 'Inconsistent value of `home`'
		home = home1

	else:
		assert False, f'Unrecognized command'


# Process program
for input_line in program:
	line = canonicalize(del_inline_comment(input_line))

	# temporarily redirect notes to note_log
	note_log = ''
	note_ = note
	def note(st):
		global note_log
		note_log += st

	old_len_result = len(result)
	process(line)

	# labels have undetermined value and they are temporarily represented
	# by zeroes in result list
	if args.target == 'overflow' and args.format == 'key' and \
			any(x != 0 and get_npress(x) > 10 for x in result[old_len_result:]):
		note('Line generates many keypresses\n')

	# restore warnings
	note = note_
	if note_log:
		note(f'While processing line\n{input_line}\n')
		note(note_log)

# A list of (source adr, offset relative to `home`).
adr_of_cmds = [(source_adr, labels[target_label]+offset)
	for source_adr, offset, target_label in adr_of_cmds]

if args.target in ('none', 'overflow'):
	if args.target == 'overflow':
		assert len(result) <= 100, 'Program too long'

	if home == None: # `org` is not used
		# compute value of `home`
		home = 0x8DA4  # initial value of SP before POP PC
		if 'home' in labels:
			home -= labels['home']  # so that the SP starts at the `home:` label
		if home + len(result) > 0x8E00:
			note(f'Warning: Program length = {len(result)} bytes > 92 bytes\n')

		min_home = home
		while min_home >= 0x8154+200: min_home -= 100
		while home + len(result) <= 0x8E00: home += 100 # 0x8E00: end of RAM
		home = min(range(min_home, home, 100), key=lambda home:
			(
				sum( # count number of ... satisfy condition
					get_npress_adr(home+home_offset) >= 100
					for source_adr, home_offset in adr_of_cmds),
				-home # if ties then take max `home`
			)
		)

elif args.target == 'loader':
	if home == None:
		home = 0x85b0 - len(result)
		entry = home + labels.get('home', 0) - 2
		result.extend((0x6a, 0x4f, 0, 0, entry & 255, entry >> 8, 0x68, 0x4f, 0, 0))
		while home + len(result) < 0x85d7:
			result.append(0)
		result.extend((0xff, 0xae, 0x85))
		home2 = 0
		assert (home - home2) >= 0x8501, 'Program too long'
		while get_npress_adr(home - home2) >= 100:
			home2 += 1

elif args.target == 'loader2':
        if home == None:
            home = 0x85ba
            if (home + labels.get('home', 0) - 2) % 256 == 0:
                home += 1
            assert home + len(result) <= 0x8e00, "Program too long"

else:
	assert False, 'Internal error'

# home is picked now, now substitute in the result
assert home is not None
for source_adr, home_offset in adr_of_cmds:
	target_adr = home + home_offset
	assert result[source_adr] == 0
	result[source_adr] = target_adr & 0xFF
	assert result[source_adr+1] == 0
	result[source_adr+1] = target_adr >> 8

# debug print label location
#for label, home_offset in labels.items():
#	note(f'Label {label} is at address {home+home_offset:04X}\n')

# scroll it around (use the most inefficient way)
hackstring = list(map(ord,'1234567890'*10)) # but still O(n)
for home_offset, byte in enumerate(result):
	assert isinstance(byte, int), (home_offset, byte)
	hackstring[(home+home_offset-0x8154)%100] = byte

# done
if args.target == 'overflow' and args.format == 'hex':
	print(''.join(f'{byte:0{2}x}' for byte in hackstring))
elif args.target in ('none', 'loader2') and args.format == 'hex':
	print('0x%04x:'%home, *map('%02x'.__mod__, result))
elif args.target == 'loader2' and args.format == 'key':
	import keypairs
	print('%s %s:'%(keypairs.get_pair((home + len(result) - 1) & 255), keypairs.get_pair((home + len(result) - 1) >> 8)))
	entry = home + labels.get('home', 0) - 2
	if home != 0x85ba: result.insert(0, 0)
	result[:0] = (0x30, 0x6a, 0x4f, 0x30, 0x30, entry & 255, entry >> 8, 0x68, 0x4f, 0x30, 0)
	result.reverse()
	print(keypairs.format(result))
	
elif args.target == 'loader' and args.format == 'key':
	print('%s %s:'%(to_key((home - home2) & 255), to_key((home - home2) >> 8)))
	for i in range(home2):
	    result.insert(0, 0)
	import keypairs
	print(keypairs.format(result))
elif args.target == 'overflow' and args.format == 'key':
	print(' '.join(map(to_key, hackstring)))
else:
	raise ValueError('Unsupported target/format combination')
