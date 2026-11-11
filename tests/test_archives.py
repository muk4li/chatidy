import io
import json
import struct
import unittest
import zipfile
from unittest.mock import patch
from chatidy.importer import parse_export


def archive(files, compression=zipfile.ZIP_STORED):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=compression) as z:
        for name, body in files:
            z.writestr(name, body)
    return output.getvalue()


VALID = json.dumps({'id': 'synthetic', 'messages': [{'role': 'user', 'content': 'Synthetic'}]})


class ArchiveTests(unittest.TestCase):
    def test_bad_json_never_silently_skipped(self):
        for invalid in ('{', '\ufffd', '[null]', '{"wrong":true}', '[1]', '[]'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_export(archive([('good.json', VALID), ('bad.json', invalid)]), 'synthetic.zip')

    def test_truncated_archive_and_crc_failure(self):
        data = archive([('synthetic.json', VALID)])
        for damaged in (b'not a zip', data[:-25], data.replace(b'Synthetic', b'Corrupted')):
            with self.subTest(), self.assertRaises(ValueError):
                parse_export(damaged, 'synthetic.zip')

    def test_duplicate_conversation_and_official_filenames(self):
        for files in ([('a.json', VALID), ('b.json', VALID)],
                      [('a/conversations.json', VALID), ('b/conversations.json', VALID)]):
            with self.assertRaises(ValueError):
                parse_export(archive(files), 'synthetic.zip')

    def test_encrypted_archive_is_controlled_error(self):
        data = bytearray(archive([('synthetic.json', VALID)]))
        for signature, offset in ((b'PK\x03\x04', 6), (b'PK\x01\x02', 8)):
            index = data.index(signature) + offset
            bits = struct.unpack_from('<H', data, index)[0]
            struct.pack_into('<H', data, index, bits | 1)
        with self.assertRaisesRegex(ValueError, 'Verschlüsselte'):
            parse_export(data, 'synthetic.zip')

    def test_size_count_and_compression_bomb_limits(self):
        data = archive([('synthetic.json', VALID)])
        for constant, limit in (('MAX_UPLOAD', 2), ('MAX_UNCOMPRESSED', 2), ('MAX_ENTRIES', 0)):
            with patch('chatidy.importer.' + constant, limit), self.assertRaises(ValueError):
                parse_export(data, 'synthetic.zip')
        bomb = archive([('synthetic.json', ' ' * 1000000)], zipfile.ZIP_DEFLATED)
        with self.assertRaisesRegex(ValueError, 'Kompressionsrate'):
            parse_export(bomb, 'synthetic.zip')

    def test_strict_json_keys_numbers_and_encoding(self):
        for invalid in (b'{"id":"a","id":"b","messages":[]}', b'[NaN]', b'\xff', b'[{'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_export(invalid, 'synthetic.json')

    def test_official_archive_ignores_unrelated_metadata_and_never_extracts_paths(self):
        data = archive([('../../conversations.json', VALID), ('user.json', '{}'), ('image.png', b'')])
        self.assertEqual(parse_export(data, 'synthetic.zip')[0]['id'], 'synthetic')
