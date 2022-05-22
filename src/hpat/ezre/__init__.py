"""
Helpers for manipulating regular expressions. 
"""
from __future__ import annotations


from typing import *
import re
from weakref import WeakValueDictionary
from reprlib import recursive_repr
import operator
import unittest
import doctest


__author__ = "Heuron Patapon"
__email__ = "heuron-patapon@laposte.net"
__version__ = "1.2.0"


__all__ = (
    "Ezre",
    "EZRE",
    "Cardinality",
    "CARDINALITY",
)


oo = float("inf")


CompleteIN = int | Literal[+oo]
MinMax = Literal[min] | Literal[max]


def load_tests(loader, tests, ignore):
    """Interface between unittest and doctest"""
    tests.addTests(doctest.DocTestSuite(__name__))
    return tests


class Cardinality:
    """
    Cardinality of a regular expression. 

    Examples
    --------
    ~~~python
    # basic usage:

    >>> str(Cardinality(1, 2))
    '{1,2}'
    >>> str(Cardinality(2, 2))
    '{2}'
    >>> str(Cardinality(2, None))
    '{2,}'
    >>> str(Cardinality(2))
    '{,2}'

    # shortcuts:

    >>> str(CARDINALITY.One)
    ''
    >>> str(CARDINALITY.Many)
    '+'
    >>> str(CARDINALITY.Any)
    '*'
    >>> str(CARDINALITY.Maybe)
    '?'

    # equalities:

    >>> Cardinality(2, 2) == Cardinality(2, 2, max)
    True
    >>> Cardinality(2) == Cardinality(0, 2) == Cardinality(None, 2)
    True
    >>> CARDINALITY.One == Cardinality(1, 1) == Cardinality(1, 1, max)
    True
    >>> CARDINALITY.Many == Cardinality(1, None)
    True
    >>> CARDINALITY.Any == Cardinality(None) == Cardinality(None, None)
    True
    >>> CARDINALITY.Maybe == Cardinality(1) == Cardinality(0, 1)
    True

    # non-greedy operations:

    >>> str(Cardinality(1, 2, min))
    '{1,2}?'
    >>> str(Cardinality(2, None, min))
    '{2,}?'
    >>> str(Cardinality(None, 2, min))
    '{,2}?'
    >>> str(Cardinality(1, None, min))
    '+?'
    >>> str(Cardinality(None, None, min))
    '*?'
    >>> str(Cardinality(0, 1, min))
    '??'

    # errors:

    >>> str(Cardinality(0.5))  # will be rounded
    '{,0}'

    >>> Cardinality(None, "hello")
    Traceback (most recent call last):
    ...
    ValueError: invalid literal for int() with base 10: 'hello'

    >>> Cardinality(None, None, 1)
    Traceback (most recent call last):
    ...
    IndexError: step=1 not in typing.Union[typing.Literal[<built-in function min>], typing.Literal[<built-in function max>]]

    >>> Cardinality(5, 3)
    Traceback (most recent call last):
    ...
    IndexError: 0 <= start=5 <= stop=3 must hold

    >>> Cardinality(5, 5, min)
    Traceback (most recent call last):
    ...
    ValueError: step=<built-in function min> cannot be used when start=5 == stop=5

    ~~~
    """
    start: int
    stop: CompleteIN
    step: MinMax

    @overload
    def __init__(self, stop: int | None):
        ...

    @overload
    def __init__(self, start: int | None, stop: CompleteIN | None, step: MinMax | None=None):
        ...

    def __init__(self, *slice_args):
        """
        Parameters
        ----------
        start
            Minimum number of repetitions.  0 and None are equivalent. 

        stop
            Maximum number of repetitions.  None is equivalent to indefinite number of repetitions. 

        step
            Greediness of regex pattern.  Default to non-greedy (when None or `max`).  `min` indicates greedy number of repetitions. 

        Caution
        -------
        Greediness is not defined when `start` is equal to `stop` (and not None values). 

        Raises
        ------
        IndexError
            - If parameters are of invalid types. 
            - If not `0 <= start <= stop`. 

        ValueError
            - If parameters are of invalid types. 
            - When `start` and `stop` are equal (not None values) and `step` is `min`. 
        """
        slice_ = slice(*slice_args)
        start, stop, step = slice_.start, slice_.stop, slice_.step
        # typing:
        start: int = 0 if start is None else int(start)
        stop: CompleteIN = +oo if stop is None else int(stop)
        step: MinMax = max if step is None else step
        # conditions:
        if step not in (min, max):
            raise IndexError(f"{step=} not in {MinMax}")
        elif not 0 <= start <= stop:
            raise IndexError(f"0 <= {start=} <= {stop=} must hold")
        elif start == stop and step is min:
            raise ValueError(f"{step=} cannot be used when {start=} == {stop=}")
        # actual work:
        elif start == 0:
            if stop == 1:
                str_ = "?"
            elif stop is +oo:
                str_ = "*"
            else:
                str_ = rf"{{,{stop}}}"
        elif start == 1:
            if stop == 1:
                str_ = str()
            elif stop is +oo:
                str_ = "+"
            else:
                str_ = rf"{{{start},{stop}}}"
        else:
            if start == stop:
                str_ = rf"{{{start}}}"
            elif stop is +oo:
                str_ = rf"{{{start},}}"
            else:
               str_ = rf"{{{start},{stop}}}"
        # non-greedy option:
        if start != stop and step is min:
            str_ += "?"
        # end of work:
        self._str = str_
        self.start: int = start
        self.stop: CompleteIN = stop
        self.step: MinMax = step

    def __str__(self):
        return self._str

    def __repr__(self):
        start, stop, step = self.start, self.stop, self.step
        return (
            f"{self.__class__.__name__}"
            "("
            f"{start=}"
            ", "
            f"{stop=}"
            ", "
            f"{step=}"
            ")"
        )

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        else:
            return str(self) == str(other)


class CARDINALITY:
    """Enumeration of human-readable shortcuts of Cardinality instances. """
    One = Cardinality(1, 1)
    Many = Cardinality(1, None)
    Any = Cardinality(None)
    Maybe = Cardinality(1)


class Var(str):
    """
    String represented without quotes. 

    Caution
    -------
    Internal usage. 
    """
    __repr__ = str.__str__


class Label:
    """
    Label of a regular expression. 

    Examples
    --------
    ~~~python
    # basic usage

    >>> a, b, c = Label(Var("A")), Label(Var("B")), Label(Var("C"))
    >>> a, b, c
    (A, B, C)

    # addition

    >>> a + b
    AB
    >>> a + b + c
    ABC

    # union

    >>> a | b
    (A|B)
    >>> a | b | c
    ((A|B)|C)

    # precedence

    >>> a + b | c
    (AB|C)
    >>> a + (b | c)
    A(B|C)

    ~~~
    """
    class And:
        def __init__(self, *items: Label):
            self._items: Sequence[Label] = tuple(items)

        @property
        def items(self):
            return self._items

        @recursive_repr()
        def __repr__(self):
            return "".join(map(repr, self._items))

    class Or:
        def __init__(self, *items: Label):
            self._items: Sequence[Label] = tuple(items)

        @property
        def items(self):
            return self._items

        @recursive_repr()
        def __repr__(self):
            free = "|".join(map(repr, self._items))
            if len(self._items) > 1:
                return f"({free})"
            else:
                return free

    def __init__(self, expr: Any | And | Or):
        self._expr = expr

    def __add__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        else:
            return self.__class__(self.And(self, other))

    def __or__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        else:
            return self.__class__(self.Or(self, other))

    @recursive_repr()
    def __repr__(self):
        return repr(self._expr)


class Ezre:
    """
    Helper for the definition of regular expressions. 

    Examples
    --------
    ~~~python
    # basic usage:

    >>> a = Ezre.from_sequence(["A", "B"], label="a")
    >>> a
    a
    >>> x = Ezre.from_sequence(["X", "Y"], label="x")
    >>> x
    x

    # addition:

    >>> expr = a + x
    >>> expr
    ax
    >>> expr.re
    '(A|B)(X|Y)'

    # union:

    >>> expr = a | x
    >>> expr
    (a|x)
    >>> expr.re
    '((A|B)|(X|Y))'

    # precedence:

    >>> expr = a + x | x
    >>> expr
    (ax|x)
    >>> expr.re
    '((A|B)(X|Y)|(X|Y))'
    >>> expr = a + (x | x)
    >>> expr
    a(x|x)
    >>> expr.re
    '(A|B)((X|Y)|(X|Y))'

    # cardinality:

    >>> a[1]
    a
    >>> a[2]
    a{2}
    >>> a[:1]
    a?
    >>> a[:2]
    a{,2}
    >>> a[:]
    a*
    >>> a[1:]
    a+
    >>> a[2:]
    a{2,}
    >>> a[2:3]
    a{2,3}
    >>> a[:] + x[3]
    a*x{3}

    # sequence ordering:

    >>> Ezre.from_sequence(["c", "a", "ab"]).re
    '(ab|a|c)'

    # use case, with special characters:

    >>> XSAMPA_TO_IPA = {"M*": "ɰ", "r\\\\": "ɹ", "?": "ʔ", "U": "ʊ", "1": "ɨ"}
    >>> XSAMPA = Ezre.from_sequence(XSAMPA_TO_IPA).re
    >>> in_ = "fweM*o ta?i r\\\\oUz1z"
    >>> out_ = re.sub(XSAMPA, lambda m: XSAMPA_TO_IPA[m.group(0)], in_)
    >>> XSAMPA
    '(M\\\\*|r\\\\\\\\|\\\\?|1|U)'
    >>> out_
    'fweɰo taʔi ɹoʊzɨz'

    ~~~
    """
    _instances = WeakValueDictionary()
    get_re: Callable[[], str] = operator.attrgetter("re")

    class And:
        def __init__(self, *items: Ezre):
            self._items: Sequence[Ezre] = tuple(items)
            self._re = r"".join(map(Ezre.get_re, self._items))

        @property
        def items(self):
            return self._items

        @property
        def re(self) -> re.Pattern:
            return self._re

    class Or:
        def __init__(self, *items: Ezre):
            self._items: Sequence[Ezre] = tuple(items)
            # re attribute:
            re_ = r"|".join(map(Ezre.get_re, self._items))
            if len(self._items) > 1:
                re_ = rf"({re_})"
            else:
                pass  # nothing to do
            self._re = re_

        @property
        def items(self):
            return self._items

        @property
        def re(self) -> re.Pattern:
            return self._re

    def __init__(
            self,
            expr: And | Or | str,
            *,
            label: str | Label | None=None,
            cardinality: Cardinality | None=None):
        # keep weakref:
        self._id = len(self._instances)
        self._instances[self._id] = self
        # typing:
        label: str | Label = label or f"#{self._id}"
        self.as_(label)
        # actual work:
        self._expr: And | Or | str = expr
        self._cardinality: Cardinality = cardinality or CARDINALITY.One
        # re attribute:
        if isinstance(self._expr, str):
            re_ = self._expr + str(self._cardinality)
        else:
            # recursivity:
            re_ = self.get_re(self._expr) + str(self._cardinality)
        self._re = re_

    @staticmethod
    def string_key(item: str) -> Tuple[int, str]:
        """
        Reference
        ---------
        https://stackoverflow.com/questions/4659524/how-to-sort-by-length-of-string-followed-by-alphabetical-order
        """
        return -len(item), item

    @classmethod
    def from_sequence(cls, expr: Sequence[str], *args, **kwargs)  -> Ezre:
        """
        Build an instance from a sequence of strings. 
        Strings will be sorted by length first (descending order)
        then alphabetically. 

        Implementation
        --------------
        Input strings in `expr` are escaped with `re.escape`. 
        """
        expr: Or = cls.Or(
            *map(cls.from_str, sorted(set(map(re.escape, expr)), key=cls.string_key)))
        return cls(expr=expr, *args, **kwargs)

    @classmethod
    def from_str(cls, expr: str, *args, **kwargs) -> Ezre:
        """Build an instance from a string. """
        return cls(expr=expr, *args, **kwargs)

    @property
    def expr(self) -> And | Or | str:
        return self._expr

    @property
    def re(self) -> str:
        return self._re

    @property
    def compiled(self) -> re.Pattern:
        return re.compile(self._re)

    @property
    def label(self) -> Label:
        return self._label

    def as_(self, label: str | Label) -> Ezre:
        """Return a copy of this instance with the desired `label`. """
        if isinstance(label, str):
            # use Var to remove quotes in string representation:
            self._label = Label(Var(label))
        elif isinstance(label, Label):
            self._label = label
        else:
            raise TypeError(f"{(type(label) == Union[str, Label])=}")
        return self

    def group(self, name: str) -> Ezre:
        """Return a copy of this instance with a regex group named `name`. """
        start = self.from_str(rf"(?P<{name}>")
        end = self.from_str(r")")
        expr = self.And(start, self, end)
        return self.__class__(
            expr=expr, label=self.label)

    @property
    def cardinality(self) -> Cardinality:
        return self._cardinality

    def __repr__(self):
        return str(self._label)

    def __str__(self):
        return self._re

    def __or__(self, other) -> Ezre:
        """Union of instances"""
        if not isinstance(other, self.__class__):
            return NotImplemented
        else:
            return self.__class__(
                expr=self.Or(self, other),
                label=self.label | other.label)

    def __add__(self, other) -> Ezre:
        """Concatenate instances"""
        # typing:
        if other is None:
            other = EZRE.End
        elif not isinstance(other, self.__class__):
            return NotImplemented
        # actual work:
        return self.__class__(
            expr=self.And(self, other),
            label=self.label + other.label)

    def __radd__(self, other) -> Ezre:
        if other is None:
            other = EZRE.Begin
            return other + self
        else:
            return NotImplemented

    def __getitem__(self, cardinality: int | slice | Cardinality) -> Ezre:
        """
        Return of copy of this instance with the desired cardinality. 

        See Also
        --------
        Cardinality
        """
        # typing:
        if isinstance(cardinality, int):
            cardinality = Cardinality(cardinality, cardinality)
        elif isinstance(cardinality, slice):
            cardinality = Cardinality(
                cardinality.start, cardinality.stop, cardinality.step)
        elif isinstance(cardinality, Cardinality):
            pass  # nothing to do
        else:
            raise TypeError(f"{(type(cardinality) == int | slice)=}")
        # actual work:
        if cardinality == CARDINALITY.One:
            return self
        else:
            return self.__class__(
               expr=self.expr,
               label=self.label + Label(Var(cardinality)),
               cardinality=cardinality)


class EZRE:
    """Enumeration of human-readable shortcuts of Ezre instances. """
    Begin = Ezre(r"^", label="^")
    End = Ezre(r"$", label="$")


if __name__ == '__main__':
    doctest.testmod()
