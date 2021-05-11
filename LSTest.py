from LakeShore372Logger import LakeShore
port = "\\\\.\\COM4"
ls = LakeShore(port)

#print(lm.send('MEAS? 1'))
print(ls.readTemp(channel=2))
