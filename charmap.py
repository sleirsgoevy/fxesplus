import lib_570esp

cols = [[] for i in range(16)]

for i in range(256):
    approx = lib_570esp.to_key(i)
    cols[i % 16].append(approx[:7])

width = [max(map(len, i)) for i in cols]

for i in range(16):
    it = []
    for j in range(16):
        it.append('%%%ds'%width[j]%cols[j][i])
    print(*it)
