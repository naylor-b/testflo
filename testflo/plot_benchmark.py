import csv
import numpy as np

from matplotlib import pyplot

benchmarks = {}

with open('benchmark_data.csv', 'r') as csvfile:
    for row in csv.reader(csvfile):
        spec = row[1].rsplit('.', 1)[1]
        benchmarks.setdefault(spec, {})
        benchmarks[spec].setdefault('timestamp', []).append(row[0])
        benchmarks[spec].setdefault('status', []).append(row[2])
        benchmarks[spec].setdefault('elapsed', []).append(row[3])
        benchmarks[spec].setdefault('maxrss', []).append(row[4])

from pprint import pprint
pprint(benchmarks)

for spec, data in benchmarks.items():
    timestamp = np.array(data['timestamp'])
    # status    = np.array(data['status'])
    elapsed   = np.array(data['elapsed'])
    maxrss    = np.array(data['maxrss'])

    fig, a1 = pyplot.subplots()
    x = np.array(range(len(timestamp)))

    a1.plot(x, elapsed, 'b-')
    a1.set_xlabel('run#')
    a1.set_ylabel('elapsed', color='b')
    for tl in a1.get_yticklabels():
        tl.set_color('b')

    a2 = a1.twinx()
    a2.plot(x, maxrss, 'r-')
    a2.set_ylabel('maxrss', color='r')
    for tl in a2.get_yticklabels():
        tl.set_color('r')

    pyplot.title(spec)
    pyplot.show()
