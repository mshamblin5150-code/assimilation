"""Optional trusted-process version observation; no discovery or qualification."""
import os
import re
import subprocess
import threading
import time
import unicodedata

LIMIT = 4096
DEADLINE = 5.0


def valid_selection(value):
    if type(value) is not str or not 4 <= len(value) <= 32767:
        return False
    if not re.match(r'^[A-Za-z]:[\\/]', value):
        return False
    parts = re.split(r'[\\/]', value[3:])
    if not parts or not parts[-1].lower().endswith('.exe'):
        return False
    for part in parts:
        if (not part or part in ('.', '..') or part[-1] in '. '
                or any(unicodedata.category(c) in ('Cc', 'Cs') or c in '<>:"|?*' for c in part)):
            return False
        stem = part.split('.')[0].upper()
        if stem in ('CON', 'PRN', 'AUX', 'NUL') or re.fullmatch(r'(COM|LPT)[1-9]', stem):
            return False
    return True


def child_environment(inherited):
    # Required Windows loader/temp variables only; never log their values.
    allowed = {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'}
    env = {key: value for key, value in inherited.items() if key.upper() in allowed}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_SYSTEM='NUL',
               GIT_CONFIG_GLOBAL='NUL', GIT_ATTR_NOSYSTEM='1',
               GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='', SSH_ASKPASS='',
               GIT_ALLOW_PROTOCOL='', GIT_CONFIG_COUNT='4')
    for ordinal, (key, value) in enumerate((('core.hooksPath', 'NUL'),
            ('init.templateDir', ''), ('credential.helper', ''), ('core.fsmonitor', 'false'))):
        env['GIT_CONFIG_KEY_' + str(ordinal)] = key
        env['GIT_CONFIG_VALUE_' + str(ordinal)] = value
    return env


class ProcessResources:
    """Real resources; tests inject replacements, never launch this adapter."""
    spawn = staticmethod(subprocess.Popen)
    clock = staticmethod(time.monotonic)
    tick = staticmethod(time.sleep)

    @staticmethod
    def start_reader(target):
        reader = threading.Thread(target=target, daemon=True)
        reader.start()
        return reader


def capture_version(selected, *, resources=None, environment=None):
    """Bound captured bytes during reading; close/reap owned resources once.

    The five-second deadline starts after creation. Creation, termination and
    OS pipe-close latency are not hard wall-clock bounded. Descendant processes
    are not contained. Cleanup failures are reported without retry.
    """
    if not valid_selection(selected):
        return None, 'invalid-selection'
    resources = ProcessResources() if resources is None else resources
    inherited = os.environ if environment is None else environment
    try:
        proc = resources.spawn([selected, '--version'], executable=selected,
                shell=False, bufsize=0, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=child_environment(inherited), close_fds=True)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, 'launch-failed'
    end = resources.clock() + DEADLINE
    pipes = (proc.stdout, proc.stderr)
    readers = []
    lock = threading.Lock()
    stop = threading.Event()
    buffers = (bytearray(), bytearray())
    done = [False, False]
    state = {'count': 0, 'error': None}
    reason = None
    code = None

    def drain(index):
        try:
            while not stop.is_set():
                byte = pipes[index].read(1)
                if byte == b'':
                    break
                with lock:
                    if type(byte) is not bytes or len(byte) != 1:
                        state['error'] = 'cleanup-failed'
                        stop.set()
                        break
                    if state['count'] >= LIMIT:
                        state['error'] = 'output-limit'
                        stop.set()
                        break
                    buffers[index].extend(byte)
                    state['count'] += 1
        except (OSError, ValueError):
            with lock:
                state['error'] = 'cleanup-failed'
                stop.set()
        finally:
            with lock:
                done[index] = True

    try:
        for index in range(2):
            readers.append(resources.start_reader(lambda index=index: drain(index)))
        while True:
            with lock:
                error, finished = state['error'], all(done)
            if error:
                reason = error
                break
            code = proc.poll()
            remaining = end - resources.clock()
            if remaining <= 0:
                reason = 'timeout'
                break
            if finished and code is not None:
                break
            resources.tick(min(0.01, remaining))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        reason = 'cleanup-failed'
    finally:
        stop.set()
        cleanup_failed = False
        try:
            if reason is not None and proc.poll() is None:
                proc.kill()
        except (OSError, ValueError, subprocess.SubprocessError):
            cleanup_failed = True
        try:
            proc.wait(timeout=DEADLINE)
        except (OSError, ValueError, subprocess.SubprocessError):
            cleanup_failed = True
        for pipe in pipes:
            try:
                pipe.close()
            except (OSError, ValueError):
                cleanup_failed = True
        for reader in readers:
            try:
                reader.join(timeout=0.1)
                if reader.is_alive():
                    cleanup_failed = True
            except RuntimeError:
                cleanup_failed = True
        if cleanup_failed:
            reason = 'cleanup-failed'
    if reason:
        return None, reason
    if code != 0:
        return None, 'nonzero-exit'
    match = re.fullmatch(rb'git version ([0-9]+\.[0-9]+[A-Za-z0-9.+_-]*)(?:\r?\n)?', bytes(buffers[0]))
    if buffers[1] or match is None:
        return None, 'invalid-output'
    return match.group(1).decode('ascii'), None
