import os
from tempfile import TemporaryDirectory

from indexed_file import indexed_file


def test_read_write_consistency():
    temp_dir_obj = TemporaryDirectory()
    with indexed_file(os.path.join(temp_dir_obj.name, 'test'), 'w+') as fd:
        print(len(fd))
        print('aa', file=fd)
        print(len(fd))
        assert len(fd) == 0
        fd.end_entry()
        print(len(fd))
        assert len(fd) == 1
        print(repr(fd.read(0)))
        assert fd[0] == 'aa' + os.linesep
        print('bbb', file=fd)
        print(len(fd))
        assert len(fd) == 1
        print(repr(fd[0]))
        assert fd[0] == 'aa' + os.linesep
        fd.end_entry()
        print(len(fd))
        assert len(fd) == 2
        print(repr(fd.read(1)))
        assert fd[1] == 'bbb' + os.linesep
        print('cccc', file=fd)
        print(len(fd))
        assert len(fd) == 2
        fd.end_entry()
        print(len(fd))
        assert len(fd) == 3
        print(repr(fd.read(2)))
        assert fd[2] == 'cccc' + os.linesep
        fd.write_line_entry('ddd')
        print(repr(fd.read(3)))
        assert fd[3] == 'ddd' + os.linesep
        #print(repr(fd.read(4))) # should raise an exception
