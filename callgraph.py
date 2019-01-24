data = {None: []}

cur = None

while True:
    try: l = input().strip()
    except EOFError: break
    if not l: cur = None
    if l.startswith('f_') and l.endswith(':'):
        cur = l[:-1]
    if l.startswith('bl '):
        if cur not in data: data[cur] = []
        data[cur].append(l.split()[1])

del data[None]

for k, v in data.items():
    print(k+': '+', '.join(v))
