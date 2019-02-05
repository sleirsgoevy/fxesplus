function help()
	print([[
The supported functions are:

printf()        Print with format.
ins             Log all register values to the screen.
break_at        Set breakpoint. If input not specified, break at current address.
unbreak_at      Delete breakpoint.
			If input not specified, delete breakpoint at current address.
			Have no effect if there is no breakpoint at specified position.
cont()          Continue program execution.
inject          Inject 100 bytes to the input field.
pr_stack()      Print 48 bytes of the stack before and after SP.

emu:set_paused  Set emulator state.
emu:tick()      Execute one command.
emu:shutdown()  Shutdown the emulator.

cpu.xxx         Get register value.

code            Access code. (By words, only use even address, otherwise program will panic)
data            Access data. (By bytes)
]])
end

function print_number(address) -- Calculator's 10-byte decimal fp number as hex.
	local x = {};
	for i = 0,9,1 do
		table.insert(x, string.format("%02x", data[address+i]));
	end;
	print(table.concat(x, ' '));
end

p = print

function inject(str)
	if #str > 200 then
		print "Input at most 200 hexadecimal digits please"
		return
	end
	if #str % 2 ~= 0 then
		print "Input an even number of hexadecimal digits please"
		return
	end

	adr = 0x81b8
	for byte in str:gmatch '..' do
		data[adr] = tonumber(byte, 16)
		adr = adr + 1
	end
end

function dump_data(adr)
	if not adr then
		adr = 0x8154
	end
	result = ''
	repeat
		byte = data[adr]
		result = result .. ('%02x'):format(byte)
		adr = adr + 1
	until byte == 0 or #result == 200
	print(result)
end


function pr_stack(radius)
	radius = radius or 48

	sp = cpu.sp
	w = io.write
	linecnt = 0
	for i = sp-radius, sp+radius-1 do
		if i >= 0x8e00 then
			break
		end
		
		w(  ('%s%02x'):format(i==sp and '*' or ' ', data[i])  )
		linecnt = linecnt+1
		if linecnt==16 then
			w('\n')
			linecnt = 0
		end
	end
	p()
end

function inject2(str)
	emu:set_paused(true)
	adr = 0x85ba
	for byte in str:gmatch '..' do
		data[adr] = tonumber(byte, 16)
		adr = adr + 1
	end
	cpu.pc = 0x2768
	cpu.sp = 0x85ba
	emu:set_paused(false)
end

function call(addr, args)
	io.stderr:write("[cpu] cpu reset\n");
	emu:set_paused(true)
	break_at(0x012345)
	for k, v in pairs(args)
	do cpu[k] = v
	end
	cpu.sp = cpu.sp - 4
	data[cpu.sp] = 0x45
	data[cpu.sp + 1] = 0x23
	data[cpu.sp + 2] = 0x01
	data[cpu.sp + 3] = 0x00
	cpu.csr = addr >> 16
	cpu.pc = addr & 65535
	emu:set_paused(false)
	return
end

function check_result()
	if cpu.pc ~= 0x2345 or cpu.csr ~= 0x0001 then return end
	emu:set_paused(true)
	unbreak_at(0x012345)
	print((cpu.r1 << 8) | cpu.r0, "("..tostring(cpu.r0)..")")
	io.stderr:write("[cpu] cpu reset\n")
end
