# Shadow File IO for Python

[![Build Status](https://travis-ci.org/motion-workshop/shadow-fileio-python.svg?branch=master)](https://travis-ci.org/motion-workshop/shadow-fileio-python)
[![codecov](https://codecov.io/gh/motion-workshop/shadow-fileio-python/branch/master/graph/badge.svg)](https://codecov.io/gh/motion-workshop/shadow-fileio-python)

## Introduction

Python module to read a Shadow take.


## Quick Start

```python
import shadow.fileio

# Search for the most recent take in our ~/Documents/Motion folder.
prefix = shadow.fileio.find_newest_take()

# Read the binary stream header, list of nodes, and big pool of frame data.
with open('{}/data.mStream'.format(prefix), 'rb') as f:
    info, node_list, data = shadow.fileio.read_stream(f)

# Use the list of nodes and the take definition (JSON text) to create a string
# name and channel mapping into the frame data.
with open('{}/take.mTake'.format(prefix)) as f:
    node_map = shadow.fileio.make_node_map(f, node_list)
```

## License

This project is distributed under a permissive [BSD License](LICENSE).
