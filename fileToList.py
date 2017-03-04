import random
import codecs
fname = "hitchhikers_guide_to_the_galaxy_quotes.txt"
f = codecs.open(fname, encoding="utf-8")
fileList = []
for line in f:
    fileList.append(line.rstrip())
outputList = [line for line in fileList if random.random()<0.34]
outputList.append(fileList[-1])
print(outputList)
