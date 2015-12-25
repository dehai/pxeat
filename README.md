# pxeat
Web based management tool for PXE service

The project is based on [Flask](http://flask.pocoo.org/) framework. It save and manage pxe entries in a sqlite database backend.

This tool provide a web interface that allow user in local network to deploy their own PXE entries. The tool can help to:

1. Download necessary kernel and initrd files.
2. Generate a pxe entry and add it to pxe config file.
3. Save the entry to database for further manage usage.
4. Provide a history overview for all entries.

Special thanks to [openSUSE](https://www.opensuse.org/) community for the supports.

## Deployment

The files you need to care:

### pxeat.cfg
Main config file of PXEAT.

### customized.cfg
the config file for PXE entries, you need to include it as a sub menu in main pxe config file (usually pxelinux.cfg/default).

eg.
```
    label H
    menu label ^H - Other Distributions
    menu indent 2
    TEXT HELP
        Your custiomized entries ...
    ENDTEXT
    kernel menu.c32
    append others.cfg
```
### pxeb.db
The sqlite database file by default. You can change the file and path in pxeat.cfg

Generate with command `python3 pxeat.py --initdb`

## To do
* Complete documents
* Downloading process tips
* Better history page view
* Clone function for history entries
* Trigger funtion after the entries added
