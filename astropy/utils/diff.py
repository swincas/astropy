import difflib
import functools
import operator
import sys
from functools import reduce
from itertools import islice

import numpy as np

from .misc import indent

__all__ = ['fixed_width_indent', 'diff_values', 'report_diff_values',
           'where_not_allclose']

# Smaller default shift-width for indent
fixed_width_indent = functools.partial(indent, width=2)


def diff_values(a, b, rtol=0.0, atol=0.0):
    """
    Diff two scalar values. If both values are floats, they are compared to
    within the given absolute and relative tolerance.

    Parameters
    ----------
    a, b : int, float, str
        Scalar values to compare.

    rtol, atol : float
        Relative and absolute tolerances as accepted by
        :func:`numpy.allclose`.

    Returns
    -------
    is_different : bool
        `True` if they are different, else `False`.

    """
    if isinstance(a, float) and isinstance(b, float):
        if np.isnan(a) and np.isnan(b):
            return False
        return not np.allclose(a, b, rtol=rtol, atol=atol)
    else:
        return a != b


def report_diff_values(a, b, fileobj=sys.stdout, indent_width=0):
    """
    Write a diff report between two values to the specified file-like object.

    Parameters
    ----------
    a, b
        Values to compare. Anything that can be turned into strings
        and compared using :py:mod:`difflib` should work.

    fileobj : obj
        File-like object to write to.
        The default is ``sys.stdout``, which writes to terminal.

    indent_width : int
        Character column(s) to indent.

    Returns
    -------
    identical : bool
        `True` if no diff, else `False`.

    """
    typea = type(a)
    typeb = type(b)

    if (isinstance(a, str) and not isinstance(b, str)):
        a = repr(a).lstrip('u')
    elif (isinstance(b, str) and not isinstance(a, str)):
        b = repr(b).lstrip('u')

    if isinstance(a, (int, float, complex, np.number)):
        a = repr(a)

    if isinstance(b, (int, float, complex, np.number)):
        b = repr(b)

    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        diff_indices = np.where(a != b)
        # NOTE: Two 5x5 arrays that are completely different would
        # report num_diffs of 625 (25 * 25).
        num_diffs = reduce(operator.mul, map(len, diff_indices), 1)
        for idx in islice(zip(*diff_indices), 3):
            fileobj.write(
                fixed_width_indent('  at {!r}:\n'.format(list(idx)),
                                   indent_width))
            report_diff_values(a[idx], b[idx], fileobj=fileobj,
                               indent_width=indent_width + 1)

        if num_diffs > 3:
            fileobj.write(fixed_width_indent(
                '  ...and at {} more indices.\n'.format(num_diffs - 3),
                indent_width))
        return num_diffs == 0

    padding = max(len(typea.__name__), len(typeb.__name__)) + 3
    identical = True

    for line in difflib.ndiff(str(a).splitlines(), str(b).splitlines()):
        if line[0] == '-':
            identical = False
            line = 'a>' + line[1:]
            if typea != typeb:
                typename = '(' + typea.__name__ + ') '
                line = typename.rjust(padding) + line

        elif line[0] == '+':
            identical = False
            line = 'b>' + line[1:]
            if typea != typeb:
                typename = '(' + typeb.__name__ + ') '
                line = typename.rjust(padding) + line
        else:
            line = ' ' + line
            if typea != typeb:
                line = ' ' * padding + line
        fileobj.write(fixed_width_indent(
            '  {}\n'.format(line.rstrip('\n')), indent_width))

    return identical


def where_not_allclose(a, b, rtol=1e-5, atol=1e-8):
    """
    A version of :func:`numpy.allclose` that returns the indices
    where the two arrays differ, instead of just a boolean value.

    Parameters
    ----------
    a, b : array_like
        Input arrays to compare.

    rtol, atol : float
        Relative and absolute tolerances as accepted by
        :func:`numpy.allclose`.

    Returns
    -------
    idx : tuple of arrays
        Indices where the two arrays differ.

    """
    # Create fixed mask arrays to handle INF and NaN; currently INF and NaN
    # are handled as equivalent
    if not np.all(np.isfinite(a)):
        a = np.ma.fix_invalid(a).data
    if not np.all(np.isfinite(b)):
        b = np.ma.fix_invalid(b).data

    if atol == 0.0 and rtol == 0.0:
        # Use a faster comparison for the most simple (and common) case
        return np.where(a != b)
    return np.where(np.abs(a - b) > (atol + rtol * np.abs(b)))
