# epicsdb2bob

[![CI](https://github.com/NSLS2/epicsdb2bob/actions/workflows/ci.yml/badge.svg)](https://github.com/NSLS2/epicsdb2bob/actions/workflows/ci.yml) [![License](https://img.shields.io/badge/license-BSD--3--Clause-blue?style=flat-square)](https://opensource.org/license/bsd-3-clause)

CLI utility for auto-creating phoebus engineering screens from EPICS db templates.

During development of EPICS IOC applications, it is generally desirable to be able to use engineering screens for testing functionality as it is being added, rather than using put/get commands with long PV names.
Engineering screens are also a key deliverable for any IOC, and the creation of these can generally be fairly rote.

This tool allows for automatically (re)generating Phoebus engineering screens recursively for an entire repository, allowing for quickly standing up screens that can be used for testing during development, and as a starting point for creating finalized interfaces.

### Installation

`epicsdb2bob` can be installed with `pip`. At the moment it has not been released on pypi, so you must use the git install candidate. Python 3.10 or newer is required.

```bash
python3.12 -m pip install --user git+https://github.com/NSLS2/epicsdb2bob
```

You can confirm that it was installed successfully by running:

```bash
jwlodek@alma10:~$ epicsdb2bob --version
0.1.dev1+gf552480.d20250723
```

### Usage

To use the tool, two arguments are passed in, an input location, and an output location. These can either be files or directories.

The input location will be searched recursively for `*.db` and `*.template` files, which will be parsed and used to create phoebus engineering screens that will be installed to the output location. One screen will be created for each `*.db` or `*.template` file found and parsed successfully. If the output location is a filename in this case, an error will be raised.

The input location will also be searched for substitution files. If found, one screen per substitution file will be created, with buttons that open screens for the corresponding `*.db` or `*.template` files.

A typical command to auto-generate screens that are then included with the module is as follows:

```bash
epicsdb2bob ~/Workspace/TektronixAFG3K/afg3kApp/Db ~/Workspace/TektronixAFG3K/afg3kApp/op/bob
```

The above was used during the development of an IOC application for [Tektronix 3000 series arbitrary function generators](https://github.com/NSLS2/TektronixAFG3K).

* [Source](https://github.com/NSLS2/epicsdb2bob)
* [Releases](https://github.com/NSLS2/epicsdb2bob/releases)
