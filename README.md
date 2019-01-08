# TCP AT Modem

[![Build Status](https://travis-ci.com/stblassitude/tcpatmodem.svg?branch=master)](https://travis-ci.com/stblassitude/tcpatmodem)[![Coverage Status](https://coveralls.io/repos/github/stblassitude/tcpatmodem/badge.svg?branch=master)](https://coveralls.io/github/stblassitude/tcpatmodem?branch=master)

This module implements an AT command interpreter as you would normally find in a modem. On the local data terminal (DTE) side, it can be connected to through standard in and out, while on the remote data communication (DCE) side, it can connect to a configurable TCP address and port.

## Installation

You can install this Python module from pypi:

```bash
pip install tcpatmodem
```

### Interactive Use

To run the AT command interpreter over standard in and out, and connect to any TCP address and port:

```bash
$ python -m tcpatmodem

```

### Exiting The AT Command Interpreter

When using the interpreter interactively, it might be useful to stop the interpreter, since Control-C does not exit the Python process. Setting the register 99 to the value 99 will stop the program. Note that any connection will be closed immediately.

Note that not all applications using this module might honor this command.

```
ATS99=99
```


## Testing

```
coverage run -m unittest discover && coverage html
```
