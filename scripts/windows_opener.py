"""Owned read-only open protocol. Scope/provenance/confinement are not granted."""
from dataclasses import dataclass, field
import re
import threading
from functools import wraps
from contextlib import contextmanager

from windows_paths import validate_namespace, NamespaceError
from windows_handle_observer import require_context
from windows_pair_observer import require_ordinary_facts


class OpenError(ValueError):
    """Fixed stage and bounded status only; no names/handles/identity output."""
    def __init__(self, stage, status=None):
        super().__init__('read_only_open_refused')
        self.stage = stage if type(stage) is str and stage in {'scope', 'state', 'context_changed',
            'metadata_changed', 'object_alias', 'operation_busy', 'completion', 'cleanup', 'runtime', 'load_system_dll'} else 'state'
        self.status = status if type(status) is int and 0 <= status <= 0xFFFFFFFF else None


@dataclass(frozen=True, eq=False)
class OwnedObject:
    handle: int = field(repr=False)
    facts: object = field(repr=False)
    parent: object = field(default=None, repr=False)


def require_component(component):
    if (type(component) is not str
            or re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9._-]{0,79}', component) is None):
        raise OpenError('scope')
    try:
        validate_namespace((component,))
    except NamespaceError:
        raise OpenError('scope') from None


def _serialized(operation):
    @wraps(operation)
    def guarded(self, *args, **kwargs):
        if not self._operation_lock.acquire(blocking=False):
            raise OpenError('operation_busy')
        try:
            return operation(self, *args, **kwargs)
        finally:
            self._operation_lock.release()
    return guarded


class WindowsOpener:
    """Reader and API are system adapters; injected recordings are simulations.

    API.open returns (NTSTATUS, IO status, IO information, handle-or-None).
    API.close returns (success, bounded Win32 error). Only exact successful
    completions transfer ownership. Uncertain/denied opens are never reissued.
    No result establishes local-volume, root provenance, or edge/race admission.
    Only one live node per observed (volume, object ID) is permitted here. This
    does not authenticate IDs after closure/restart or govern external handles.
    """
    def __init__(self, reader, api):
        self._operation_lock = threading.Lock()
        self.reader, self.api = reader, api
        self.owned = []
        self.failed = False
        self.root_attempted = False
        self.cleanup_errors = []

    def _context(self):
        if self.failed or self.cleanup_errors or self.reader.cleanup_errors:
            raise OpenError('state')
        value = self.reader.context()
        require_context(value)
        if self.reader.cleanup_errors:
            raise OpenError('cleanup')
        return value

    def _metadata(self, handle):
        facts = self.reader.metadata(handle)
        require_ordinary_facts(facts)
        if self.reader.cleanup_errors:
            raise OpenError('cleanup')
        return facts

    @contextmanager
    def retained_file(self, node):
        """Keep public lifecycle operations out of a separately authorized query.

        This is local ownership custody, not namespace/race admission. Direct
        reader/private access and external handle closure remain outside it.
        A failed observation preserves owned objects for explicit cleanup.
        """
        if not self._operation_lock.acquire(blocking=False):
            raise OpenError('operation_busy')
        try:
            if (not any(item is node for item in self.owned)
                    or node.facts is None or node.facts.directory):
                raise OpenError('scope')
            owned = tuple(self.owned)
            ancestor = node.parent
            visited = {id(node)}
            while ancestor is not None:
                if (id(ancestor) in visited
                        or not any(item is ancestor for item in owned)
                        or ancestor.facts is None or not ancestor.facts.directory):
                    raise OpenError('state')
                visited.add(id(ancestor))
                ancestor = ancestor.parent
            try:
                context = self._context()
                if self._metadata(node.handle) != node.facts:
                    raise OpenError('metadata_changed')
                yield node.handle
                if (len(self.owned) != len(owned)
                        or any(a is not b for a, b in zip(self.owned, owned))):
                    raise OpenError('state')
                if self._metadata(node.handle) != node.facts:
                    raise OpenError('metadata_changed')
                if self._context() != context:
                    raise OpenError('context_changed')
            except BaseException:
                self.failed = True
                raise  # No cleanup queries or closes replace the primary error.
        finally:
            self._operation_lock.release()

    @_serialized
    def open_root(self):
        if self.root_attempted:
            raise OpenError('state')
        self.root_attempted = True
        return self._open(None, '\\??\\C:\\', True)

    @_serialized
    def open_child(self, parent, component, *, directory):
        if (not any(item is parent for item in self.owned) or not parent.facts.directory
                or type(directory) is not bool):
            raise OpenError('scope')
        require_component(component)
        return self._open(parent, component, directory)

    def _open(self, parent, name, directory):
        node = None
        try:
            context = self._context()
            if parent is not None and self._metadata(parent.handle) != parent.facts:
                raise OpenError('metadata_changed')
            completion = self.api.open(None if parent is None else parent.handle, name)
            if type(completion) is not tuple or len(completion) != 4:
                raise OpenError('completion')
            status, io_status, information, handle = completion
            if type(status) is not int or status != 0:
                # No output ownership on failure/pending/unknown completion.
                raise OpenError('completion', status)
            if (type(handle) is not int or not 0 < handle < 2**64 - 1
                    or any(item.handle == handle for item in self.owned)):
                raise OpenError('completion')
            node = OwnedObject(handle, None, parent)
            self.owned.append(node)  # Own successful handle before further checks.
            if type(io_status) is not int or io_status != 0 or type(information) is not int or information != 1:
                raise OpenError('completion')
            facts = self._metadata(handle)
            if facts.directory != directory or (parent is not None and
                    (facts.volume != parent.facts.volume or facts.object_id == parent.facts.object_id)):
                raise OpenError('metadata_changed')
            if any(item is not node and item.facts is not None
                   and (item.facts.volume, item.facts.object_id) == (facts.volume, facts.object_id)
                   for item in self.owned):
                raise OpenError('object_alias')
            if parent is not None and self._metadata(parent.handle) != parent.facts:
                raise OpenError('metadata_changed')
            if self._context() != context:
                raise OpenError('context_changed')
            updated = OwnedObject(handle, facts, parent)
            self.owned[self.owned.index(node)] = updated
            return updated
        except BaseException:
            self.failed = True
            if node is not None:
                try:
                    self._close_known(node)
                except BaseException:
                    pass  # close recorded uncertainty; preserve primary failure.
            raise

    @_serialized
    def close(self, node):
        return self._close_known(node)

    def _close_known(self, node):
        if not any(item is node for item in self.owned):
            raise OpenError('state')
        if any(item.parent is node for item in self.owned):
            raise OpenError('state')  # Retain every ancestor until children close.
        self.owned.remove(node)  # Never retry a failed/uncertain close.
        try:
            ok, code = self.api.close(node.handle)
            if ok is not True:
                self.failed = True
                self.cleanup_errors.append(code if type(code) is int and 0 <= code <= 0xFFFFFFFF else None)
        except BaseException:
            self.failed = True
            self.cleanup_errors.append(None)
            raise

    @_serialized
    def close_all(self):
        """Close each known-owned object once; record uncertainty, never retry."""
        for node in tuple(reversed(self.owned)):
            try:
                self._close_known(node)
            except BaseException:
                pass  # Other distinct known-owned handles still need cleanup.
        return tuple(self.cleanup_errors)
