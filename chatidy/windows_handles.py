"""Small typed Win32 binding for local NTFS job storage (Windows only).

CreateFileW opens reparse points themselves and pins directories without
FILE_SHARE_DELETE. Protected inheritable DACLs grant only the current user and
SYSTEM; existing objects with broad write grants are refused, not repaired.
"""
import ctypes as c
from ctypes import wintypes as w
from contextlib import contextmanager
from pathlib import Path

kernel = c.WinDLL('kernel32', use_last_error=True)
security = c.WinDLL('advapi32', use_last_error=True)
HANDLE = w.HANDLE
INVALID_HANDLE = c.c_void_p(-1).value
READ_CONTROL = 0x20000
DELETE = 0x10000
SHARE_ALL = 7
SHARE_PIN = 3  # read/write allowed, rename/delete denied to other handles
OPEN_EXISTING, OPEN_ALWAYS, CREATE_NEW = 3, 4, 1
REPARSE = 0x400
DIRECTORY = 0x10


class FileInfo(c.Structure):
    _fields_ = [('attributes', w.DWORD), ('creation', w.FILETIME), ('access', w.FILETIME),
        ('write', w.FILETIME), ('volume', w.DWORD), ('size_high', w.DWORD), ('size_low', w.DWORD),
        ('links', w.DWORD), ('index_high', w.DWORD), ('index_low', w.DWORD)]


class SecurityAttributes(c.Structure):
    _fields_ = [('length', w.DWORD), ('descriptor', c.c_void_p), ('inherit', w.BOOL)]


class ACL(c.Structure):
    _fields_ = [('revision', w.BYTE), ('reserved', w.BYTE), ('size', w.WORD),
                ('count', w.WORD), ('reserved2', w.WORD)]


class AceHeader(c.Structure):
    _fields_ = [('kind', w.BYTE), ('flags', w.BYTE), ('size', w.WORD)]


class RenameInfo(c.Structure):
    _fields_ = [('replace', w.BOOLEAN), ('root', HANDLE), ('length', w.DWORD), ('name', w.WCHAR * 1)]


class DispositionInfo(c.Structure):
    _fields_ = [('delete', w.BOOLEAN)]


def bind(lib, name, args, result=w.BOOL):
    function = getattr(lib, name)
    function.argtypes, function.restype = args, result
    return function


CreateFile = bind(kernel, 'CreateFileW', [w.LPCWSTR, w.DWORD, w.DWORD,
    c.POINTER(SecurityAttributes), w.DWORD, w.DWORD, HANDLE], HANDLE)
Close = bind(kernel, 'CloseHandle', [HANDLE])
MoveFile = bind(kernel, 'MoveFileExW', [w.LPCWSTR, w.LPCWSTR, w.DWORD])
Info = bind(kernel, 'GetFileInformationByHandle', [HANDLE, c.POINTER(FileInfo)])
FileType = bind(kernel, 'GetFileType', [HANDLE], w.DWORD)
SetInfo = bind(kernel, 'SetFileInformationByHandle', [HANDLE, c.c_int, c.c_void_p, w.DWORD])
CreateDirectory = bind(kernel, 'CreateDirectoryW', [w.LPCWSTR, c.POINTER(SecurityAttributes)])
CurrentProcess = bind(kernel, 'GetCurrentProcess', [], HANDLE)
Duplicate = bind(kernel, 'DuplicateHandle', [HANDLE, HANDLE, HANDLE, c.POINTER(HANDLE), w.DWORD, w.BOOL, w.DWORD])
LocalFree = bind(kernel, 'LocalFree', [c.c_void_p], c.c_void_p)
DriveType = bind(kernel, 'GetDriveTypeW', [w.LPCWSTR], w.UINT)
VolumeInfo = bind(kernel, 'GetVolumeInformationW', [w.LPCWSTR, w.LPWSTR, w.DWORD,
    c.c_void_p, c.c_void_p, c.c_void_p, w.LPWSTR, w.DWORD])
OpenToken = bind(security, 'OpenProcessToken', [HANDLE, w.DWORD, c.POINTER(HANDLE)])
TokenInfo = bind(security, 'GetTokenInformation', [HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)])
SidString = bind(security, 'ConvertSidToStringSidW', [c.c_void_p, c.POINTER(w.LPWSTR)])
ConvertDescriptor = bind(security, 'ConvertStringSecurityDescriptorToSecurityDescriptorW',
    [w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p])
SecurityInfo = bind(security, 'GetSecurityInfo', [HANDLE, w.DWORD, w.DWORD,
    c.POINTER(c.c_void_p), c.c_void_p, c.POINTER(c.c_void_p), c.c_void_p,
    c.POINTER(c.c_void_p)], w.DWORD)
GetAce = bind(security, 'GetAce', [c.c_void_p, w.DWORD, c.POINTER(c.c_void_p)])


def checked(result):
    if not result:
        raise c.WinError(c.get_last_error())
    return result


def sid_text(pointer):
    result = w.LPWSTR()
    checked(SidString(pointer, c.byref(result)))
    try:
        return result.value
    finally:
        LocalFree(c.cast(result, c.c_void_p))


def current_sid():
    token = HANDLE()
    checked(OpenToken(CurrentProcess(), 8, c.byref(token)))
    try:
        size = w.DWORD()
        TokenInfo(token, 1, None, 0, c.byref(size))
        buffer = c.create_string_buffer(size.value)
        checked(TokenInfo(token, 1, buffer, size, c.byref(size)))
        # TOKEN_USER starts with SID_AND_ATTRIBUTES, whose first field is PSID.
        return sid_text(c.cast(buffer, c.POINTER(c.c_void_p))[0])
    finally:
        Close(token)


USER_SID = current_sid()
TRUSTED = frozenset((USER_SID, 'S-1-5-18', 'S-1-5-32-544'))


@contextmanager
def private_attributes():
    descriptor = c.c_void_p()
    checked(ConvertDescriptor('D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;'+USER_SID+')', 1,
                              c.byref(descriptor), None))
    try:
        yield SecurityAttributes(c.sizeof(SecurityAttributes), descriptor, False)
    finally:
        LocalFree(descriptor)


def check_acl(handle):
    owner, acl, descriptor = c.c_void_p(), c.c_void_p(), c.c_void_p()
    error = SecurityInfo(handle, 1, 1 | 4, c.byref(owner), None, c.byref(acl), None, c.byref(descriptor))
    if error:
        raise c.WinError(error)
    try:
        if not owner or sid_text(owner) not in TRUSTED or not acl:
            raise ValueError('Unsichere Windows-Berechtigungen des Importjobs.')
        # File data/attribute writes, DELETE_CHILD, DELETE, WRITE_DAC/OWNER and
        # generic write/all. Read-only grants to other identities are harmless.
        writes = 2 | 4 | 16 | 64 | 256 | DELETE | 0x40000 | 0x80000 | 0x40000000 | 0x10000000
        for index in range(c.cast(acl, c.POINTER(ACL)).contents.count):
            pointer = c.c_void_p()
            checked(GetAce(acl, index, c.byref(pointer)))
            header = c.cast(pointer, c.POINTER(AceHeader)).contents
            if header.flags & 8 or header.kind == 1:  # inherit-only or deny
                continue
            if header.kind != 0 or header.size < 12:
                raise ValueError('Nicht unterstützte Windows-Zugriffsregel im Importjob.')
            mask = c.c_uint32.from_address(pointer.value + 4).value
            if mask & writes and sid_text(pointer.value + 8) not in TRUSTED:
                raise ValueError('Importjob ist unter Windows für andere Benutzer schreibbar.')
    finally:
        LocalFree(descriptor)


def information(handle):
    result = FileInfo()
    checked(Info(handle, c.byref(result)))
    if result.attributes & REPARSE:
        raise ValueError('Symlinks, Junctions und Reparse Points sind in Importjob-Pfaden nicht erlaubt.')
    if FileType(handle) != 1:  # FILE_TYPE_DISK, no pipes/devices
        raise ValueError('Importjobs benötigen reguläre lokale Dateien.')
    return result


def identity(handle):
    info = information(handle)
    return info.volume, info.index_high, info.index_low


def open_handle(path, access, share=SHARE_ALL, disposition=OPEN_EXISTING, directory=False):
    with private_attributes() as attributes:
        handle = CreateFile(str(path), access | READ_CONTROL, share, c.byref(attributes),
                            disposition, 0x00200000 | (0x02000000 if directory else 0), None)
        error = c.get_last_error()
    if handle == INVALID_HANDLE:
        raise c.WinError(error)
    try:
        info = information(handle)
        if bool(info.attributes & DIRECTORY) != directory:
            raise ValueError('Ungültiger Dateityp im Importjob.')
        if not directory and info.links > 1:
            raise ValueError('Hardlinks sind in Importjobs nicht erlaubt.')
        return handle
    except BaseException:
        Close(handle)
        raise


def duplicate(handle):
    result = HANDLE()
    checked(Duplicate(CurrentProcess(), handle, CurrentProcess(), c.byref(result), 0, False, 2))
    return result.value


def validate_volume(path):
    path = Path(path)
    if not path.is_absolute() or len(path.drive) != 2 or path.drive[1] != ':':
        raise ValueError('Windows-Importjobs benötigen einen lokalen absoluten Laufwerkspfad; keine UNC-/Gerätepfade.')
    if any(':' in part or part.rstrip(' .') != part for part in path.parts[1:]):
        raise ValueError('Mehrdeutige Windows-Pfadkomponenten oder Alternate Data Streams sind nicht erlaubt.')
    anchor = path.anchor
    filesystem = c.create_unicode_buffer(32)
    if DriveType(anchor) != 3:
        raise ValueError('Importjobs benötigen ein lokales festes Windows-Laufwerk.')
    checked(VolumeInfo(anchor, None, 0, None, None, None, filesystem, len(filesystem)))
    if filesystem.value.upper() != 'NTFS':
        raise ValueError('Sichere Windows-Importjobs benötigen derzeit NTFS.')


def rename(handle, target):
    encoded = str(target).encode('utf-16-le')
    buffer = c.create_string_buffer(RenameInfo.name.offset + len(encoded))
    info = c.cast(buffer, c.POINTER(RenameInfo)).contents
    info.replace, info.root, info.length = False, None, len(encoded)
    c.memmove(c.addressof(buffer) + RenameInfo.name.offset, encoded, len(encoded))
    checked(SetInfo(handle, 3, buffer, len(buffer)))  # FileRenameInfo


def mark_delete(handle):
    info = DispositionInfo(True)
    checked(SetInfo(handle, 4, c.byref(info), c.sizeof(info)))  # FileDispositionInfo
