import subprocess
import os
import logging


def dryRun():
    return os.getenv('DRY_RUN') == 'true'


def wrap(attributeName):
    original = getattr(subprocess, attributeName)

    def _wrappedInLogging(* args, ** kwargs):
        if type(args[0]) is list:
            commandString = ' '.join(args[0])
        else:
            commandString = args[0]
        logging.info('{}: {}'.format(attributeName, commandString))
        if dryRun():
            return original(['true'])
        return original(* args, ** kwargs)

    setattr(subprocess, attributeName, _wrappedInLogging)

wrap('Popen')
