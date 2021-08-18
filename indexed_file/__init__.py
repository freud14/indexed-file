import os
from array import array

from .version import __version__


class IndexedFile:
    # See https://stackoverflow.com/questions/16208206/confused-by-python-file-mode-w and
    # https://docs.python.org/3.8/library/functions.html#open for the modes.
    MODES = 'rwxabt+'

    def __init__(self, directory, mode='r'):
        assert all(c in IndexedFile.MODES for c in mode)
        self.mode = mode
        self.directory = directory
        self._reset()

    def _reset(self):
        self.length_fd = None
        self.entry_fd = None
        self.offsets = None
        self._isopen = False
        self._current_written_entry = None

    def __enter__(self):
        return self.open()

    def __exit__(self, type_, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def open(self):
        if self.isopen():
            return self

        entry_filename, length_filename = self._get_files()

        if 'x' in self.mode and os.path.exists(self.directory):
            raise ValueError(f"Directory {self.directory} already exists.")

        if ('w' in self.mode or 'a' in self.mode) and not os.path.exists(self.directory):
            os.mkdir(self.directory)

        self.length_fd = None
        if self._is_write_mode():
            self.length_fd = open(length_filename, self.mode.replace('b', ''))

        self.entry_fd = open(entry_filename, self.mode)

        # Open and read the filename for the lengths.
        self.offsets = array('Q', [0])
        offset = 0
        with open(length_filename, 'r') as fd:
            for line in fd:
                offset += int(line)
                self.offsets.append(offset)

        self._isopen = True
        return self

    def close(self):
        if self.isopen():
            if self._is_write_mode():
                self.end_entry()
            if self.length_fd is not None:
                self.length_fd.close()
            self.entry_fd.close()
            self._reset()

    def isopen(self):
        return self._isopen

    def __len__(self):
        assert self.isopen()
        return len(self.offsets) - 1

    def _get_files(self):
        entry_file = os.path.join(self.directory, 'entries.data')
        length_file = os.path.join(self.directory, 'lengths.txt')
        return entry_file, length_file

    def __getitem__(self, index):
        return self.read(index)

    def read_entry(self, index):
        return self.read(index)

    def read(self, index):
        assert 'r' in self.mode or '+' in self.mode
        if index >= len(self):
            raise IndexError
        offset = self.offsets[index]
        length = self.offsets[index + 1] - offset
        return self._read_n_bytes(offset, length)

    def _read_n_bytes(self, offset, n):
        self.entry_fd.seek(offset)
        last_read = self.entry_fd.read(n)
        read = last_read
        while len(read) != n and len(last_read) != 0:
            last_read = self.entry_fd.read(n - len(read))
            read += last_read
        return read

    def _is_write_mode(self):
        return 'w' in self.mode or 'a' in self.mode or '+' in self.mode

    def write(self, data):
        assert self._is_write_mode()

        if self._current_written_entry is not None:
            self._current_written_entry += data
        else:
            self._current_written_entry = data

    def write_entry(self, data):
        assert self._is_write_mode()
        self.write(data)
        self.end_entry()

    def write_line_entry(self, data):
        assert 'b' not in self.mode
        self.write_entry(data + os.linesep)

    def end_entry(self):
        assert self._is_write_mode()
        if self._current_written_entry is not None:
            # seek end of files
            self.entry_fd.seek(0, 2)
            self.length_fd.seek(0, 2)

            # write in files
            self.entry_fd.write(self._current_written_entry)
            print(len(self._current_written_entry), file=self.length_fd)

            # maintain offsets cache
            self.offsets.append(self.offsets[-1] + len(self._current_written_entry))

            self._current_written_entry = None


def indexed_file(directory, mode='r'):
    return IndexedFile(directory, mode=mode).open()
