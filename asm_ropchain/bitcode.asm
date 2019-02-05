# 255 - er0 = [er0]
# 254 - [er0] = er2
# 253 - [er0] = r2
# 252 - add
# 251 - mul
# 250 - slot = er2
# 249 - er0 = slot
# 248 - xchg er0, er2
# 0-248 - select slot

main_loop:
set lr

# read instruction and increment PC
pop er0
pc:
adr_of program_start
er8 = [er0]
er0 = er8
pop er8
adr_of pc
pop er2
0x0001
[er8] += er2, pop xr8
0x00000000

# switch-case based on opcode
er2 = 0x0000
r2 = r0
er0 = adr_of saved_r0
[er0] = r2
er0 = 0x00f7
er0 = max<unsigned>(er0, er2)
er2 = er0, pop er8
0x0000
er0 += er2
er2 = adr_of [-512] switch_arr
er0 += er2, er8 = [er0]
er0 = er8
er2 = er0, pop er8
adr_of switch_tgt
er0 = er8
[er0] = er2

# pop registers
pop er0
er0_value:
0x0000
pop er2
er2_value:
0x0000

# jump to handler
pop er14
switch_tgt:
0x0000
sp = er14, pop er14

# jump table
adr_of select_slot
adr_of xchg_slot
adr_of load_slot
adr_of store_slot
adr_of mul_slot
adr_of add_slot
adr_of store1_slot
adr_of store2_slot
adr_of load2_slot
switch_arr:

# handlers

select_slot:
adr_of [-2] main_loop
pop er0
saved_r0:
0x0000
er2 = er0, pop er8
0x0000
er0 += er2
er2 = adr_of slot_arr
er0 += er2, er8 = [er0]
er0 = er8
er2 = er0, pop er8
adr_of slot_pp
er0 = er8
[er0] = er2
er0 = adr_of slot_pp_2
[er0] = er2
sp = er14, pop er14

xchg_slot:
adr_of [-2] save_regs
er2 = er0, pop er8
adr_of er2_value
er0 = er8
er8 = [er0]
er0 = er8
sp = er14, pop er14

load_slot:
adr_of [-2] save_regs
pop er0
slot_pp:
0x0000
er8 = [er0]
er0 = er8
sp = er14, pop er14

store_slot:
adr_of [-2] main_loop
pop er0
slot_pp_2:
0x0000
[er0] = er2
sp = er14, pop er14

mul_slot: #er2 = r0 * r2
adr_of [-2] save_er2
call 0x134a8
sp = er14, pop er14

add_slot: #er0 += er2
adr_of [-2] save_regs
er0 += er2
sp = er14, pop er14

store1_slot:
adr_of [-2] main_loop
[er0] = r2
sp = er14, pop er14

store2_slot:
adr_of [-2] main_loop
[er0] = er2
sp = er14, pop er14

load2_slot:
adr_of [-2] save_regs
er8 = [er0]
er0 = er8
sp = er14, pop er14

# save registers
save_regs:
er8 = er0
er0 = adr_of er2_tmp
[er0] = er2
er0 = er8
er2 = er0, pop er8
adr_of er0_value
er0 = er8
[er0] = er2
pop er2
er2_tmp:
0x0000
save_er2: #er2 only
er0 = adr_of er2_value
[er0] = er2
goto main_loop

#the main program

slot_arr:
slot_0:
adr_of slot_1
slot_1:
0xf046
slot_2:
0xf040
slot_3:
adr_of slot_4
slot_4:
0xf830
slot_5:
adr_of pc
slot_6:
adr_of slot_7
slot_7:
adr_of program_start
slot_8:
adr_of slot_9
slot_9:
0xffff
program_start:
0x08 #slot 9
0xf9 #er0 = slot
0xf8 #xchg
0x00 #slot 0
0xf9 #er0 = slot
0xfd #[er0] = r2
0x02 #slot 2
0xf9 #er0 = slot
0xf8 #xchg
0x03 #slot 3
0xf9 #er0 = slot
0xfd #[er0] = r2
0x06 #slot 6
0xf9 #er0 = slot
0xf8 #xchg
0x05 #slot 5
0xfa #slot = er2
