# This is just a helper module to load Fredrick Lundh's ElementTree

# It tries the uber-fast C version first, then falls back to the
# globally installed version, then to the version bundled with
# pyScore 

## try:
##    from cElementTree import *
##    def iselement(element):
##       return hasattr(element, "tag")
##    raise ImportError() # This won't work yet, since there is no .remove method
## except ImportError:
##    from elementtree.ElementTree import *
## except ImportError:
from pyScore.elementtree.ElementTree import *
