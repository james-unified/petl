"""
As the root :mod:`petl` module but with optimisations for use in an interactive
session.

"""


from itertools import islice
import sys
from .util import valueset, RowContainer
import petl.fluent
from petl.io import tohtml, StringSource


petl = sys.modules['petl']
thismodule = sys.modules[__name__]


cachesize = 1000
debug = False
representation = petl.look


class InteractiveWrapper(petl.fluent.FluentWrapper):
    
    def __init__(self, inner=None):
        super(InteractiveWrapper, self).__init__(inner)
        object.__setattr__(self, '_cache', [])
        object.__setattr__(self, '_tag', None)
        object.__setattr__(self, '_cachecomplete', False)
        
    def __iter__(self):
        try:
            tag = self._inner.cachetag()
        except:
            # cannot cache for some reason, just pass through
            if debug: print repr(self._inner) + ' :: uncacheable'
            return iter(self._inner)
        else:
            if self._tag is None or self._tag != tag:
                # _tag is not fresh
                if debug: print repr(self._inner) + ' :: stale, clearing cache'
                object.__setattr__(self, '_cache', []) # reset cache
                object.__setattr__(self, '_tag', tag)
                object.__setattr__(self, '_cachecomplete', False)
            return self._iterwithcache()
            
    def _iterwithcache(self):
        if debug: print repr(self._inner) + ' :: serving from cache, cache size ' + str(len(self._cache))

        # serve whatever is in the cache first
        for row in self._cache:
            yield row
            
        if not self._cachecomplete:
            # serve the remainder from the inner iterator
            if debug: print repr(self._inner) + ' :: cache exhausted, serving from inner iterator'    
            it = iter(self._inner)
            for row in islice(it, len(self._cache), None):
                # maybe there's more room in the cache?
                if len(self._cache) < cachesize:
                    self._cache.append(row)
                yield row
                
        if len(self._cache) < cachesize:
            object.__setattr__(self, '_cachecomplete', True)
        
    def __repr__(self):
        if representation is not None:
            return repr(representation(self))
        else:
            return object.__repr__(self)
        
    def _repr_html_(self):
        buf = StringSource()
        tohtml(self, buf)
        return buf.getvalue()
            
    
def wrap(f):
    def wrapper(*args, **kwargs):
        _innerresult = f(*args, **kwargs)
        if isinstance(_innerresult, RowContainer):
            return InteractiveWrapper(_innerresult)
        else:
            return _innerresult
    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper

        
# import and wrap all functions from root petl module
for n, c in petl.__dict__.items():
    if callable(c):
        setattr(thismodule, n, wrap(c))
    else:
        setattr(thismodule, n, c)
        
        
# add module functions as methods on the wrapper class
# TODO add only those methods that expect to have row container as first argument
for n, c in thismodule.__dict__.items():
    if callable(c):
        if n.startswith('from'): # avoids having to import anything other than "etl"
            setattr(InteractiveWrapper, n, staticmethod(c))
        else:
            setattr(InteractiveWrapper, n, c) 
        
        
# need to manually override for facet, because it returns a dict 
def facet(table, field):
    fct = dict()
    for v in valueset(table, field):
        fct[v] = getattr(thismodule, 'selecteq')(table, field, v)
    return fct


# need to manually override for diff(), because it returns a tuple 
def diff(*args, **kwargs):
    a, b = petl.diff(*args, **kwargs)
    return InteractiveWrapper(a), InteractiveWrapper(b)


# short alias to wrap explicitly
etl = InteractiveWrapper    

    