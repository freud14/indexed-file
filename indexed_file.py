import os


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
        self.lengths = None
        self.offsets = None
        self._isopen = False
        self._current_written_entry = None

    def __enter__(self):
        return self.open()

    def __exit__(self, type, value, traceback):
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
        with open(length_filename, 'r') as fd:
            self.lengths = [int(line) for line in fd]

        self.offsets = []
        offset = 0
        for length in [0] + self.lengths:
            offset += length
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

    def _get_files(self):
        entry_file = os.path.join(self.directory, 'entries.data')
        length_file = os.path.join(self.directory, 'lengths.txt')
        return entry_file, length_file

    def read(self, index):
        assert 'r' in self.mode or '+' in self.mode
        if index >= len(self.lengths):
            raise IndexError
        offset = self.offsets[index]
        length = self.lengths[index]
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

    def end_entry(self):
        assert self._is_write_mode()
        if self._current_written_entry is not None:
            # seek end of files
            self.entry_fd.seek(0, 2)
            self.length_fd.seek(0, 2)

            # write in files
            self.entry_fd.write(self._current_written_entry)
            print(len(self._current_written_entry), file=self.length_fd)

            # maintain lengths and offsets cache
            self.lengths.append(len(self._current_written_entry))
            self.offsets.append(self.offsets[-1] + len(self._current_written_entry))

            self._current_written_entry = None


def indexed_file(*args, **kwargs):
    return IndexedFile(*args, **kwargs).open()


if __name__ == '__main__':
    with indexed_file('test', 'w+') as fd:
        print('aa', file=fd)
        fd.end_entry()
        print(repr(fd.read(0)))
        print('bbb', file=fd)
        print(repr(fd.read(0)))
        fd.end_entry()
        print(repr(fd.read(1)))
        print('cccc', file=fd)
        fd.end_entry()
        print(repr(fd.read(2)))
        #print(repr(fd.read(3)))
