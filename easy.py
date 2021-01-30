with open(filename, r) as file:
    contents = file.read()

file = open(newFilename, a)
resString = []

for line in contents.splitlines():
    tableName = line.split()[2]
    newLine = f'grant select, insert, update, delete on muniarb.{tableName} to ARBINTEGRATOR'
    resString.append(newLine)
    file.write(newLine + '\n')
    file.flush()

file.close()