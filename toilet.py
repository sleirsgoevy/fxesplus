import os, sys

x = sys.stdin.read()

import keypairs

ans = [['', 0]]

for line in x.split('\n'):
    it = '%-128s'%line
    it = int(''.join(str(int(i != ' ')) for i in it), 2).to_bytes(16, 'big')
    for i in it:
        try: item = keypairs.get_pair(i)
        except IndexError: item = 'UNTYPABLE%02x'%i
        if ans[-1][0] == item: ans[-1][1] += 1
        else: ans.append([item, 1])

del ans[0]

print('Total length:', sum(i[1] for i in ans))

ans2 = []

for i, j in ans:
    if j != 1:
        ans2.append('%dx{%s}'%(j, i))
    else:
        ans2.append(i)

print(*ans2, sep='\n')
