#!/bin/sh
cd "$(dirname $0)"

if which luajit; then
	cmd=luajit
else
	cmd=lua
fi

$cmd CasioEmu/disassembler/disassembler.lua \
	input='CasioEmu/models/fx570esplus/rom.bin' \
	output='./fx_570es+_disas.txt' \
	entry='1,2,4,5,6,7,8,9,10,11,12,13,14,15,16' \
	strict='true' addresses='true' rom_window='0x8000' \
	names='./570es+_names.txt' \
	"$@"
