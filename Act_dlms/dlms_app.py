from dlms import *

meter = Dlms("/dev/ttyS2")

values = meter.query().strip()
print("%16s: %s" % ("identifier", values[0]))
print("")
for i in values[1]:
    j = values[1][i]
    if len(j) == 2:
        print("%16s: %s [%s]" % (i, j[0], j[1]))
    else:
        print("%16s: %s" % (i, j[0]))



