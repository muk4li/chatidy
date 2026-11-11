"""Incremental standard-library JSON array reader with strict decoding."""
import io
import json


class BudgetReader(io.RawIOBase):
    def __init__(self, source, budget):
        self.source, self.budget = source, budget

    def readable(self):
        return True

    def readinto(self, buffer):
        data = self.source.read(min(len(buffer), self.budget[0] + 1))
        self.budget[0] -= len(data)
        if self.budget[0] < 0:
            raise ValueError('Entpacktes JSON überschreitet das Größenlimit.')
        buffer[:len(data)] = data
        return len(data)


def json_values(source, budget, decoder, chunk_size=65536):
    """Stream a top-level array one element at a time; single objects stay whole.

    Memory is bounded by the largest conversation, not the whole array. Legacy
    object envelopes are supported but buffered as one object.
    """
    stream = io.TextIOWrapper(io.BufferedReader(BudgetReader(source, budget)), encoding='utf-8-sig')
    buffer, pos, eof = '', 0, False

    def more():
        nonlocal buffer, pos, eof
        data = stream.read(chunk_size)
        buffer = buffer[pos:] + data
        pos = 0
        eof = not data
        return buffer

    def peek():
        nonlocal pos, eof
        while True:
            while pos < len(buffer) and buffer[pos].isspace():
                pos += 1
            if pos < len(buffer):
                return buffer[pos]
            if eof:
                return ''
            more()

    def value():
        nonlocal pos
        while True:
            try:
                result, end = decoder.raw_decode(buffer, pos)
                pos = end
                return result
            except json.JSONDecodeError as exc:
                if eof:
                    raise ValueError('Ungültiges oder unvollständiges JSON im Export.') from exc
                more()

    try:
        if peek() != '[':
            # Objects include legacy {conversations: [...]} envelopes.
            # Ensure the complete document is read so numeric/string prefixes
            # and trailing garbage cannot be accepted accidentally.
            while not eof:
                more()
            yield value()
        else:
            pos += 1
            if peek() == ']':
                pos += 1
                raise ValueError('Leerer Konversationsexport.')
            while True:
                if peek() != '{':
                    raise ValueError('Ungültige Konversation im Export.')
                yield value()
                separator = peek()
                if separator == ']':
                    pos += 1
                    break
                if separator != ',':
                    raise ValueError('Ungültiges oder unvollständiges JSON im Export.')
                pos += 1
        if peek():
            raise ValueError('Unerwartete Daten nach JSON-Export.')
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Ungültiges oder zu tief verschachteltes JSON im Export.') from exc
    finally:
        stream.close()
