/*
  Rational module
  Copyright (c) 2001, Christopher A. Craig
  All rights reserved.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions are met:

  Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

  Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

  The name Christopher Craig may not be used to endorse or promote products
  derived from this software without specific prior written permission.

  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
  ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
  ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
  DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
  OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
  DAMAGE.  
*/

static char crat_module_documentation[] = \
"This modules defines a rational type for Python using the C extension\n"\
"language.  Rational numbers are infinitely accurate, but can take\n"\
"unbounded time and space.  Every effort has been made to make\n"\
"operations done on instances of this rational type as fast as\n"\
"possible.\n"\
"\n"\
"Rationals can be created in several ways\n"\
"   >>> rational(12)\n"\
"   12/1\n"\
"   >>> rational(12, 2)\n"\
"   6/1\n"\
"   >>> rational(1L<<40, 5)\n"\
"   1099511627776/5\n"\
"   >>> rational(12.5)\n"\
"   25/2\n"\
"   >>> rational(12.2)\n"\
"   3433994715870003/281474976710656\n"\
"   >>> rational('12.2')\n"\
"   61/5\n"\
"   >>> rational('12/5')\n"\
"   12/5\n"\
"\n"\
"\n"\
"Factors can grow quite large:\n"\
"   >>> import time\n"\
"   >>> def timetrial(a):\n"\
"   ...     t = time.time()\n"\
"   ...     accum = 0\n"\
"   ...     for i in xrange(1, 1000): accum += a / i    \n"\
"   ...     return accum, (time.time()-t)\n"\
"   ... \n"\
"   >>> r, t = timetrial(rational(1))\n"\
"   >>> r\n"\
"   53355784417020119952537879239887266136731803921522374204060897246465114565409520646006621457833121819822177013733448523121929191853817388455050878455561717371027592157489651884795570078464505321798967754860322188969172665004633935471096455470633645094270513262722579396248817332458071400971347691033193734596623333937737766140820373673275246317859525956885804716570122271771159715339438239613795876131660183846149167740477557199918997/7128865274665093053166384155714272920668358861885893040452001991154324087581111499476444151913871586911717817019575256512980264067621009251465871004305131072686268143200196609974862745937188343705015434452523739745298963145674982128236956232823794011068809262317708861979540791247754558049326475737829923352751796735248042463638051137034331214781746850878453485678021888075373249921995672056932029099390891687487672697950931603520000\n"\
"\n"\
"The above operation is also quite slow, but well optimized.\n"\
"    >>> r2, t2 = timetrial(1.)\n"\
"    >>> t < (t2*100)\n"\
"    1\n"\
"\n"\
"We can also directly access the numerator and denominator\n"\
"   >>> t = rational(12.5)\n"\
"   >>> t.numerator\n"\
"   25L\n"\
"   >>> t.denominator\n"\
"   2L\n"\
"\n"\
"or convert them to another type\n"\
"   >>> float(t)\n"\
"   12.5\n"\
"   >>> int(t)\n"\
"   12\n"\
"\n"\
"even when we would get NaN otherwise\n"\
"   >>> float(r)\n"\
"   7.4844708605503447\n"\
"   >>> try: print float(r.numerator)/float(r.denominator)\n"\
"   ... except OverflowError: print 'NaN'\n"\
"   NaN\n"\
"\n"\
"Rationals hash to the same value as native types:\n"\
"   >>> t = rational(12)\n"\
"   >>> hash(t) == hash(int(t))\n"\
"   1\n"\
"\n"\
"Even if they aren't equivelent\n"\
"   >>> t = rational('12.2')\n"\
"   >>> t == float(t)\n"\
"   0\n"\
"   >>> hash(t) == hash(float(t))\n"\
"   1\n";



#include "Python.h"
#include "structmember.h"
#include "longintrepr.h"

#include <ctype.h>

#define ABS(x) ((x) < 0 ? -(x) : (x))
#define SIZE(x) (((PyLongObject *)x)->ob_size)

/***************************************************************
 I should explain the following macros a bit.  
 When we get to the main body I'm making 7-10 calls against
 PyNumber per function.  Each of those needs to do error
 checking.  So, to make things cleaner, I maintain the guarantee
 that on each line all refrences are either active or NULL
 pointers, then I can just jump to code the xdecrefs everything
 in the event of a failure (and not have 60 lines of error
 cleanup for a 15 line function.)
***************************************************************/

/* checks for NULL returns */
#define CHECK(x) if(!(x)) goto onError

/* ensures that freed references are reset to NULL */
#define MYDECREF(x) { Py_DECREF(x); x=NULL; }

/* applies operation in place, also checks for null returns */
#define INPLACE1(op, x) { PyObject *tfoo; CHECK(tfoo=op(x)); \
     Py_DECREF(x); x=tfoo; }
#define INPLACE(op, x, y) { PyObject *tfoo; CHECK(tfoo=op(x,y)); \
                            Py_DECREF(x); x=tfoo; }

/* used for debugging */
#define PRINT_VAR(d, x) \
  printf("%s: ", d); \
  PyObject_Print(x, stdout, 0); printf("\n");\

#ifndef NDEBUG
#include <stdio.h>
#endif

staticforward PyTypeObject PyRational_Type;

/************************************************************
  factor math:
    the following allow me cheat like mad when taking the GCD
************************************************************/

/* factor_normalize: remove leading zeros from a factor.
   Exactly the same as long_normalize.  Used by shifts */
static PyLongObject *
factor_normalize(register PyLongObject *v)
{
     int j = ABS(v->ob_size);
     register int i = j;

     while(i>0 && v->ob_digit[i-1]==0) --i;
     if(i!=j) v->ob_size = (v->ob_size < 0) ? -(i) : i;
     return v;
}

/* shift right by 'shift' places. sign of 'a' is ignored,
   and result is always positive.
   
   This and lshift are mainly used to avoid having to construct
   PyLong_Objects for the shift variables in _factor_gcd_fast */
static PyObject *
factor_rshift(PyObject *aa, long shift)
{
     int wordshift, newsize, loshift, hishift, i, j;
     digit lomask, himask;
     PyLongObject *a=(PyLongObject *)aa;
     PyLongObject *new;

     wordshift = shift/SHIFT;
     newsize=ABS(a->ob_size) - wordshift;
     if(newsize <= 0) {
          return (PyObject *)PyLong_FromLong(0L);
     }
     loshift = shift % SHIFT;
     hishift = SHIFT - loshift;
     lomask = ((digit)1 << hishift)-1;
     himask = MASK ^ lomask;
     new = _PyLong_New(newsize);
     if (new==NULL) return NULL;
     for(i=0, j=wordshift; i<newsize; i++, j++){
          new->ob_digit[i] = (a->ob_digit[j]>>loshift)&lomask;
          if (i+1<newsize)
               new->ob_digit[i] |= (a->ob_digit[j+1]<<hishift)&himask;
     }
     return (PyObject *)factor_normalize(new);
}

/* same as rshift, but left shifts */
static PyObject *
factor_lshift(PyObject *aa, long shift)
{
     PyLongObject *a = (PyLongObject *)aa;
     PyLongObject *z;
     int oldsize, newsize, wordshift, remshift, i, j;
     twodigits accum=0;

     wordshift = (int)shift/SHIFT;
     remshift = (int)shift - wordshift * SHIFT;
     oldsize = ABS(a->ob_size);
     newsize = oldsize + wordshift;
     if (remshift) ++newsize;
     z = _PyLong_New(newsize);
     if(z==NULL) return NULL;
     for(i=0; i<wordshift; i++) z->ob_digit[i]=0;
     for(i=wordshift, j=0; j<oldsize; i++, j++) {
          accum |= a->ob_digit[j] << remshift;
          z->ob_digit[i] = (digit)(accum & MASK);
          accum >>= SHIFT;
     }
     if(remshift)
          z->ob_digit[newsize-1] = (digit)accum;
     else
          assert(!accum);
     return (PyObject *)factor_normalize(z);
}

static PyObject *
factor_muladd1(PyObject *aa, wdigit n, twodigits carry)
{
     int size_a = ABS(SIZE(aa));
     PyLongObject *a = (PyLongObject *)aa;
     PyLongObject *z = _PyLong_New(size_a+1);
     int i;
     
     if (z == NULL)
          return NULL;
     for (i = 0; i < size_a; ++i) {
          carry += (twodigits)a->ob_digit[i] * n;
          z->ob_digit[i] = (digit) (carry & MASK);
          carry >>= SHIFT;
     }
     z->ob_digit[i] = (digit) carry;
     return (PyObject *)factor_normalize(z);
}

/* find how many places one must rshift to make a number odd */
static long
factor_findshift(PyObject *aa)
{
     PyLongObject *f=(PyLongObject *)aa;
     int mask = 1;
     long bytenum = -1;
     long i = 0;

     /* find the first non-zero digit */
     while(f->ob_digit[++bytenum]==0) i+=SHIFT;

     /* find the first non-zero bit in that digit */
     while(!((f->ob_digit[bytenum])&mask)) {
          mask<<=1;
          i++;
     }
     return i;
}

/* find gcd(aa, bb) where aa->size <= 2 */
static PyObject *
_factor_gcd_euclid1(PyObject *aa, PyObject *bb)
{
     PyObject *bt;
     register long a, b, t;

     a = PyLong_AsLong(aa);
     if(SIZE(bb)<=2) b=PyLong_AsLong(bb);
     else {
	  if((bt = PyNumber_Remainder(bb, aa))==NULL) return NULL;
	  b = PyLong_AsLong(bt);
	  Py_DECREF(bt);
     }

     while (b) {
          t = a % b;
          a = b;
          b = t;
     }

     return PyLong_FromLong(a);
}

/* find gcd(a, b) where a<b */
static PyObject *
_factor_gcd_fast(PyObject *a, PyObject *b)
{
     PyObject *t=NULL;
     long shift;

     Py_INCREF(a);
     Py_INCREF(b);

	/* if b>>a then replace b with b%a to save work later */
     if (SIZE(a) != SIZE(b)) {
          CHECK(t = PyNumber_Remainder(b, a));
          Py_DECREF(b);
          b=t;
          t=NULL;
     }

	/* if a divides b, return a */
     if (SIZE(b) == 0) {
          Py_DECREF(b);
          return a;
     }

     {long shiftA, shiftB;
     shiftA = factor_findshift(a);
     shiftB = factor_findshift(b);
     shift = (shiftA < shiftB ? shiftA : shiftB);
     INPLACE(factor_rshift, a, shiftA);
     INPLACE(factor_rshift, b, shiftB);
     }

     CHECK(t = PyNumber_Subtract(a, b));

     while (SIZE(t)) {
          long s;

          s = factor_findshift(t);
          if(SIZE(t)<0) {
               Py_DECREF(b);
               CHECK(b = factor_rshift(t, s));
          } else {
               Py_DECREF(a);
               CHECK(a = factor_rshift(t, s));
          }
          /* we are in the inner loop, so I'll do anything to save a cycle */
          Py_DECREF(t);
          CHECK(t = PyLong_Type.tp_as_number->nb_subtract(a, b));
     }

     Py_DECREF(t);
     CHECK(t = factor_lshift(b, shift));
     Py_DECREF(a);
     Py_DECREF(b);

     return t;

 onError:
     Py_XDECREF(a); Py_XDECREF(b); Py_XDECREF(t);
     return NULL;
}

static PyObject *
factor_gcd(PyObject *aa, PyObject *bb)
{
     /* History:

        There are two main ways to do GCD: Euclid's algorithm and a
          binary method based on shifts and subtracts.

        Euclid takes less iterations, and takes time relative to the smaller
          of the two inputs.  But requires divides which are very expensive on
          large numbers.

        Binary uses much less expensive operations (esp. on smaller numbers),
          but takes time relative to the larger input and takes more
          iterations than Euclid to complete even if the numbers are similarly
          sized.

        I used to run Euclid iff the smaller element was less than half the
          size of the larger, and this worked pretty well.  Then I was
          thinking about the algorithms and the above properties and realized
          that I could do it much faster if I made a hybrid method that given
          (a < b) set b to b%a (reducing the problem space to the size of the
          smaller input) and then used the binary method.

        I also included a fast method for dealing with single length integers
          that uses C ints rather than PyLongs as intermediate values, which
          speeds up this case quite a bit.
     */

     PyObject *a, *b, *z;
     int sizea, sizeb;

     if(!(a=PyNumber_Absolute(aa))) return NULL;
     sizea=SIZE(a);
     
     if(!(b=PyNumber_Absolute(bb))) {
          Py_DECREF(a);
          return NULL;
     }
     sizeb=SIZE(b);
     

     if(sizea > sizeb) {
          long t; PyObject *tf;
          t = sizea; sizea = sizeb; sizeb = t;
          tf = a; a=b; b=tf;
     }

     if(sizea == 0) {
          Py_DECREF((PyObject *)a);
          return (PyObject *)b;
     }
     else if(sizea <= 2) z = _factor_gcd_euclid1(a, b); 
     else z = _factor_gcd_fast(a, b);

     Py_DECREF(a);
     Py_DECREF(b);
     return z;
}

static char crat_gcd_doc__[] = \
"gcd(long, long) -> long\n"\
"\n"\
"This is the gcd function used by crat.\n";

static PyObject *
crat_gcd(PyObject *self, PyObject *args)
{
     PyObject *a, *b, *retobj;
     
     if (!PyArg_ParseTuple(args, "OO", &a, &b)) return NULL;
     a = PyNumber_Long(a);
     b = PyNumber_Long(b);

     retobj = (PyObject *)factor_gcd(a, b);

     Py_DECREF((PyObject *)a);
     Py_DECREF((PyObject *)b);
     return (PyObject *)retobj;
}

/************************************************************
  Rational methods

  the meat of the object
************************************************************/


typedef struct {
     PyObject_HEAD
     PyObject *n; /* PyLong numerator */
     PyObject *d; /* PyLong denominator */
} PyRational_Object;

static char rational_doc[]= \
"rational(arg1, arg2) -> rational\n"\
"arg1 and arg2 can be of type int, long, float, or string.  If string\n"\
"then they must be of the form '<int>[.<int>]' or '<int>/<int>', \n"\
"for example '12', '12.1', '12/3'  are valid strings.\n"\
"\n"\
"Rational objects have the single method self.trim() and the attributes\n"\
"self.numerator and self.denominator\n";

static PyRational_Object *x_mul(PyObject *an, PyObject *ad,
                                PyObject *bn, PyObject *bd);
static PyRational_Object *x_add(PyObject *an, PyObject *ad,
                                PyObject *bn, PyObject *bd);
static int x_divmod(PyRational_Object *a, PyRational_Object *b,
				PyObject **div, PyRational_Object **mod);
static int convert_binop(PyObject *v, PyObject *w,
                         PyRational_Object **a, PyRational_Object **b);
static PyObject *r_trim(PyRational_Object *self, PyObject *max_d);
static PyObject *rational_div(PyObject *v, PyObject *w);


#define CONVERT_BINOP(v, w, a, b, op) \
        {PyObject *t; \
        if ((t=upcast_floats(v, w, op))) return t; \
        else if (PyErr_Occurred()) return NULL; }\
	if (!convert_binop(v, w, a, b)) { \
		Py_INCREF(Py_NotImplemented); \
		return Py_NotImplemented; \
	}


static int
PyRational_Check(PyObject *a)
{
	return PyObject_TypeCheck(a, &PyRational_Type);
}


/* WARNING: Steals references */
static PyRational_Object *
_PyRational_FROM_FACTORS(PyObject *zn, PyObject *zd)
{
     PyRational_Object *z=NULL;

     if (zn==NULL||zd==NULL) goto onError;
     if(SIZE(zd) < 0) {
          INPLACE1(PyNumber_Negative, zn);
          INPLACE1(PyNumber_Negative, zd);
     }

     CHECK(z = PyObject_NEW(PyRational_Object, &PyRational_Type));
     z->n = zn;
     z->d = zd;
     return z;

 onError:
     Py_XDECREF(zn); Py_XDECREF(zd);
     return NULL;
}

/* for export.  Does not steal references, reduces factors */
static PyObject *
PyRational_FromFactors(PyObject *v, PyObject *w)
{
	PyObject *n, *d;
	PyObject *zn, *zd, *g;

	n=d=zn=zd=g=NULL;

	if(!((PyInt_Check(v)||PyLong_Check(v))&&
		(PyInt_Check(w)||PyLong_Check(w)))) {
		PyErr_SetString(PyExc_TypeError,
					 "arguments must be of type int or long");
		return NULL;
	}

	CHECK(d=PyNumber_Long(w));
	if(SIZE(d)==0) {
		PyErr_SetString(PyExc_ZeroDivisionError, "divide by zero");
		Py_DECREF(d);
		return NULL;
	}
	CHECK(n=PyNumber_Long(v));

	CHECK(g=factor_gcd(n, d));
	CHECK(zn=PyNumber_FloorDivide(n, g));
	CHECK(zd=PyNumber_FloorDivide(d, g));
	Py_DECREF(n);
	Py_DECREF(d);
	Py_DECREF(g);
	return (PyObject *)_PyRational_FROM_FACTORS(zn, zd);

 onError:
	Py_XDECREF(zn);
	Py_XDECREF(zd);
	Py_XDECREF(g);
	return NULL;
}
	

static void
PyRational_AsFactors(PyRational_Object *self, PyObject **n, PyObject **d)
{
     *n = self->n;
     *d = self->d;
     Py_INCREF(self->n);
     Py_INCREF(self->d);
}


static PyRational_Object *
PyRational_FromString(char *s)
{
     int sign=1, esign=1;
     char *ts, *start=s;
     PyObject *n, *d;
     PyObject *exp;

     n = PyLong_FromLong(0);
     d = PyLong_FromLong(1);
     exp = PyLong_FromLong(1);
     CHECK(n&&d&&exp);

     while(*s != '\0' && isspace(Py_CHARMASK(*s))) ++s;
     if(*s == '+') ++s;
     else if (*s == '-') {
          ++s;
          sign = -1;
     }
     
     while (*s != '\0' && isspace(Py_CHARMASK(*s))) ++s;
     if (*s == '.') goto strDecimal;
     ts = s;

     for(; n != NULL; ++s) {
          int k = -1;
          PyObject *t;

          if (*s <= '9') k = *s - '0';
          if (k < 0 || k > 9) break;

          CHECK(t = factor_muladd1(n, (digit)10, (digit)k));
          Py_DECREF(n);
          n=t;
     }

     if (n == NULL) return NULL;
     if (s == ts)
          goto onError;

     if (*s == 'L' || *s == 'l') ++s;
     if (*s == '\0')
          goto strReturn;
     if (*s == '/') goto strFraction;
     if (*s != '.')
          goto onError;

 strDecimal:
     for(s++; n!=NULL && d!=NULL; ++s) {
          int k = -1;
          PyObject *tn;

          if(*s <= '9') k = *s - '0';
          if(k<0 || k > 9) break;

          CHECK(tn = factor_muladd1(n, (digit)10, (digit)k));
          Py_DECREF(n);
          n = tn;
          CHECK(tn = factor_muladd1(exp, (digit)10, (digit)0));
	  Py_DECREF(exp);
	  exp = tn;
     }
     
     if(*s=='L' || *s == 'l') ++s;
     while (*s != '\0' && isspace(Py_CHARMASK(*s))) ++s;

	if(*s == '.') {
		if(*++s != '.') goto onError;
		if(*++s != '.') goto onError;
		if(*++s != '\0') goto onError;
		goto strReturn;
	}

     if (*s == '\0')
          goto strReturn;
     else
          goto onError;

 strFraction:
     Py_DECREF(d);
     CHECK(d = PyLong_FromLong(0));

     if (*(++s) == '-') {
	  esign=-1;
	  s++;
     } else if (*s == '+') {
	  s++;
     }
     
     for(; d != NULL; ++s) {
          int k = -1;
          PyObject *t;

          if (*s <= '9') k = *s - '0';
          if (k < 0 || k > 9) break;

          CHECK(t = factor_muladd1(d, (digit)10, (digit)k));
          Py_DECREF(d);
          d=t;
     }

	if(SIZE(d)==0) {
		Py_XDECREF(n);
		Py_XDECREF(d);
		Py_XDECREF(exp);
		PyErr_SetString(PyExc_ZeroDivisionError, "divide by zero");
		return NULL;
	}
	
     while (*s != '\0' && isspace(Py_CHARMASK(*s))) ++s;
     if(*s != '\0') goto onError;

 strReturn:
     INPLACE(PyNumber_Multiply, d, exp);
     Py_DECREF(exp);

     CHECK(exp = factor_gcd((PyObject *)n, (PyObject *)d));
     INPLACE(PyNumber_Divide, n, exp);
     INPLACE(PyNumber_Divide, d, exp);
     Py_DECREF(exp);

     return _PyRational_FROM_FACTORS(n, d);

 onError:
     Py_XDECREF(n); Py_XDECREF(d);
     Py_XDECREF(exp); 
     PyErr_Format(PyExc_ValueError,
                  "invalid literal for rational(): %.200s", start);
     return NULL;
}

static PyRational_Object *
PyRational_FromDouble(double s)
{
     double base;
     int exp, sign=1;
     PyObject *n, *d, *t;

     if(Py_IS_INFINITY(s)) {
          PyErr_SetString(PyExc_OverflowError,
                          "cannot convent unbounded float");
          return NULL;
     }

     n = PyLong_FromLong(0);
     d = PyLong_FromLong(1);
     t = NULL;

     CHECK(n&&d);

     base = frexp(s, &exp);
     if(base<0) {
          sign=-1;
          base=-base;
     }

     while(base) {
          const int shift=SHIFT;
          int t;
          PyObject *f;

          base = ldexp(base, shift);
          t = floor(base);
          base -= t;
          exp -= shift;

          CHECK(f = PyLong_FromLong((long)t));
          INPLACE(factor_lshift, n, shift);
          INPLACE(PyNumber_Add, n, f);
          Py_DECREF(f);
     }

     if(exp > 0) {
          INPLACE(factor_lshift, n, exp);
     } else {
          INPLACE(factor_lshift, d, -exp);
     }

     if(sign < 0){
          INPLACE1(PyNumber_Negative, n);
     }
     CHECK(t = factor_gcd(n, d));
     INPLACE(PyNumber_Divide, n, t);
     INPLACE(PyNumber_Divide, d, t);
     Py_DECREF(t);

     return _PyRational_FROM_FACTORS(n, d);

 onError:
     Py_XDECREF(t); Py_XDECREF(n); Py_XDECREF(d);
     return NULL;
}

static double 
PyRational_AsDouble(PyRational_Object *self) 
{ 
 	int size_n = ABS(SIZE(self->n)), size_d = ABS(SIZE(self->d)); 
 	int shift = (size_n-size_d-5)*SHIFT; 
 	PyObject *tn, *t; 
 	double z;

	tn=t=NULL;

	/*********************************************************
      shifts such that n is exactly 5 digits (75 bits) longer
      than d, then creates float from floordivision

      result exponent is modified to account for shift
	**********************************************************/

 	if (shift > 0) { 
 		CHECK(tn = factor_lshift(self->d, shift)); 
 		CHECK(t = PyNumber_FloorDivide(self->n, tn)); 
 		MYDECREF(tn); 
 	} else if (shift < 0) { 
 		CHECK(tn = factor_lshift(self->n, -shift)); 
 		CHECK(t = PyNumber_FloorDivide(tn, self->d)); 
 		MYDECREF(tn); 
 	} else { 
 		CHECK(t = PyNumber_FloorDivide(self->n, self->d)); 
 	} 

 	if((z = PyLong_AsDouble(t))==-1 && PyErr_Occurred()) goto onError;
	Py_DECREF(t);
 	z = ldexp(z, shift);

	if((z<0)^(SIZE(self->n)<0)) z=-z;

 	return z;

 onError:
	Py_XDECREF(tn); Py_XDECREF(t);
	return -1;
	
} 

	
static PyRational_Object *
r_convert(PyObject *a)
{
     if(a==NULL) {
          return _PyRational_FROM_FACTORS(PyLong_FromLong(1),
								 PyLong_FromLong(1));
     } else if(PyRational_Check(a)) {
          Py_INCREF(a);
          return (PyRational_Object *)a;
     } else if(PyInt_Check(a) || PyLong_Check(a)) {
          return _PyRational_FROM_FACTORS(PyNumber_Long(a), PyLong_FromLong(1));
     } else if (PyString_Check(a)) {
          return PyRational_FromString(PyString_AsString(a));
     } else if(PyFloat_Check(a)) {
          return PyRational_FromDouble(PyFloat_AsDouble(a));
     }
     return NULL;
}


static PyObject *
rational_subtype_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
     
static PyObject *
rational_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	PyObject *aa, *bb;
	PyObject *n, *d;

     n=d=aa=bb=NULL;

	if(type != &PyRational_Type) {
		return rational_subtype_new(type, args, kwds);
	}
		
     if(!PyArg_ParseTuple(args, "|OO", &aa, &bb)) return NULL;

	if(aa==NULL) {
		/* no arguments, return 1 */
		CHECK(n=PyLong_FromLong(0));
		CHECK(d=PyLong_FromLong(1));
          return (PyObject *)_PyRational_FROM_FACTORS(n, d);
	}

	if(bb!=NULL) {
		/* two arguments, both arguments must be int/longs */
		if(!((PyInt_Check(aa)||PyLong_Check(aa))&&
			(PyInt_Check(bb)||PyLong_Check(bb)))) {
			PyErr_SetString(PyExc_TypeError,
						 "if two args given, both must be of type int or long");
			return NULL;
		}
		CHECK(n=PyNumber_Long(aa));
		CHECK(d=PyNumber_Long(bb));

		if(SIZE(d)==0) {
			/* divide by zero */
			PyErr_SetString(PyExc_ZeroDivisionError, "Divide by zero");
			goto onError;
		}

		return PyRational_FromFactors(n, d);
	}

	/* one argument.  Accept int,long,float, or string */
	n = (PyObject *)r_convert(aa);
	if(n==NULL && ! PyErr_Occurred()) {
		PyErr_Format(PyExc_TypeError,
				   "Cannot create rational from argument of type %s",
				   aa->ob_type->tp_name);
	}
	return n;

 onError:
	Py_XDECREF(n);
	Py_XDECREF(d);
	return NULL;
}

static PyObject *
rational_subtype_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	PyRational_Object *t, *new;

	t = (PyRational_Object *)rational_new(&PyRational_Type, args, kwds);
	if (t==NULL)
		return NULL;
	new = (PyRational_Object *)type->tp_alloc(type, 0);
	if (new == NULL) {
		Py_DECREF(t);
		return NULL;
	}
	new->n = t->n;
	new->d = t->d;
	Py_INCREF(new->n);
	Py_INCREF(new->d);
	Py_DECREF(t);
	return (PyObject *)new;
}


static void
rational_dealloc(PyRational_Object *self)
{
     Py_DECREF(self->n);
     Py_DECREF(self->d);
	self->ob_type->tp_free((PyObject *)self);
}

/* I would prefer not to do this at all, but 2.2 includes have a problem
   with not actually #defining PyObject_Del
*/
static inline void
rational_free(PyObject *self)
{
	PyObject_Del(self);
}

static int
rational_cmp(PyRational_Object *a, PyRational_Object *b)
{
     PyObject *ta, *tb;
     int t;

     ta = PyNumber_Multiply(a->n, b->d);
     tb = PyNumber_Multiply(b->n, a->d);

     CHECK(ta&&tb);

     t = PyObject_Compare(ta, tb);
     Py_DECREF(ta);
     Py_DECREF(tb);

     return t;

 onError:
     Py_XDECREF(ta);
     Py_XDECREF(tb);
     return -1;     
}

/* test two rationals for equality (1 if equal, 0 if unequal) */
static int
x_ratrateq(PyObject *v, PyObject *w)
{
	int cmp0, cmp1;
	PyRational_Object *a = (PyRational_Object *)v;
	PyRational_Object *b = (PyRational_Object *)w;
	if (PyObject_Cmp(a->n, b->n, &cmp0)==-1)
		return -1;
	if (PyObject_Cmp(a->d, b->d, &cmp1)==-1)
		return -1;
	return (cmp0==0)&&(cmp1==0);
}

/* test a rational and an integer/long for equality (1 if equal, 0 if uneq) */
static int
x_ratinteq(PyObject *v, PyObject *w)
{
	PyRational_Object *r = (PyRational_Object *)v;
	int cmp;

	/* rational denominator must be 1 */
	if (!((SIZE(r->d)==1) &&
		 (((PyLongObject *)(r->d))->ob_digit[0]==1)))
		return 0;

	/* compare the numerator to the int */
	if (PyObject_Cmp(r->n, w, &cmp)==-1) return -1;
	return cmp==0;
}

	
static PyObject *
rational_richcompare(PyObject *v, PyObject *w, int op)
{
	PyObject *z;
	int cmp;

	assert(PyRational_Check(v) || PyRational_Check(w));
	
	if (op==Py_EQ || op == Py_NE) {
		if (PyRational_Check(v) && PyRational_Check(w)) {
			if((cmp = x_ratrateq(v, w))==-1) return NULL;
			z = (cmp == (op == Py_EQ)) ? Py_True : Py_False;
		} else {
			/* make v the rational */
			if(PyRational_Check(w)) {
				PyObject *t=v;
				v=w;
				w=t;
			}
			
			if(PyInt_Check(w)||PyLong_Check(w)) {
				if((cmp = x_ratinteq(v, w))==-1) return NULL;
				z = (cmp == (op == Py_EQ)) ? Py_True : Py_False;
			} else {
				z = Py_NotImplemented;
			}
		}
	} else {
		z = Py_NotImplemented;
	}
	Py_INCREF(z);
	return z;
}

static PyObject *
rational_repr(PyRational_Object *self)
{
     PyObject *a, *b, *t;

     a=b=t=NULL;

     CHECK(a = PyObject_Str(self->n));
     CHECK(b = PyString_FromString("/"));
     CHECK(t = PySequence_Concat(a, b));
     Py_DECREF(a);
     CHECK(a = PyObject_Str(self->d));
     Py_DECREF(b);
     CHECK(b = PySequence_Concat(t, a));

     Py_DECREF(t);
     Py_DECREF(a);
     return (PyObject *)b;

 onError:
     Py_XDECREF(a);
     Py_XDECREF(b);
     Py_XDECREF(t);
     return NULL;
}

/*************************************************************
 * returns a string of the form NNNN[.NNNN[...]] with at
 * least 'precision' digits after the decimal place (if needed)
 * '...' is appended if precision isn't enough to precisely
 * represent the fraction
 *************************************************************/
static PyObject *
r_str(PyRational_Object *self, int precision)
{
     PyObject *ip, *fp, *tthou, *s,
          *t1, *t2;

     char *sp, sp5[5];
     int len=0;
		
     ip=fp=s=tthou=NULL;
     t1=t2=NULL;

	/***************************************************
	 * ip, fp = divmod(self.numerator, self.denominator
	 * s = str(ip)
	 * if not fp: return s
	 * s += '.'
	 * while len<precision:
	 *    ip, fp = divmod(fp*10000, self.denominator)
	 *    s += '%.4d' % ip
	 *    if not fp: break
	 * else:
	 *    return s+'...'
	 * while s[-1] == '0': s=s[:-1]
	 * return s
	 **************************************************/

	/* because of the complexity of this function, I'm repeating the
	   Python code above the C */

     /* ip, fp = divmod(self.numerator, self.denominator) */
     /*# ip and fp references are active until after the main loop */
     CHECK(t1=PyNumber_Divmod(self->n, self->d));
     CHECK(ip = PyTuple_GET_ITEM(t1, 0));
     Py_INCREF(ip);
     CHECK(fp = PyTuple_GET_ITEM(t1, 1));
     Py_INCREF(fp);
     MYDECREF(t1);

     /* s = str(ip) */
     CHECK(s = PyObject_Str(ip));
	/* if not fp: return s */
     if (SIZE(fp)==0) {
          Py_DECREF(ip);
          Py_DECREF(fp);
          return s;
     }
     /* s += '.' */
     CHECK(t1 = PyString_FromString("."));
     PyString_Concat(&s, t1);
     if(s==NULL) goto onError;
     MYDECREF(t1);

     /* # 10000 allows the PyLong operations to work on single 'digits',
	   # which is faster.  
	*/
     CHECK(tthou=PyLong_FromLong(10000));

	/* while len<precision: */
     do {
          /* ip, fp = divmod(fp*10000, self.denominator) */
          CHECK(t1=PyNumber_Multiply(fp, tthou));
          CHECK(t2=PyNumber_Divmod(t1, self->d));
          MYDECREF(t1);
          MYDECREF(ip);
          MYDECREF(fp);
          CHECK(ip = PyTuple_GET_ITEM(t2, 0));
          Py_INCREF(ip);
          CHECK(fp = PyTuple_GET_ITEM(t2, 1));
          Py_INCREF(fp);
          MYDECREF(t2);

          /* s += '%.4d' % ip */
          snprintf(sp5, 5, "%.4ld", PyLong_AsLong(ip));
          CHECK(t1 = PyString_FromStringAndSize(sp5, 4));
          PyString_Concat(&s, t1);
          if(s==NULL) goto onError;
          MYDECREF(t1);

          /* if not fp: break */
          if (SIZE(fp)==0) {
			/* # I do this here, rather than as a list post condition
			   # because it makes reference management cleaner, imho
			*/
               len = 0;
               break;
          }

          /* len += 4 */
          len += 4;
     } while (len<precision);
     MYDECREF(ip);
     MYDECREF(fp);
     MYDECREF(tthou);

     /* else: */
     if(len!=0) {
		/* # we didn't finish */
		/* return s+'...' */
          CHECK(t1 = PyString_FromString("..."));
          PyString_Concat(&s, t1);
          if(s==NULL) goto onError;
          MYDECREF(t1);
		return s;
     }

     /* while s[-1] == '0': s=s[:-1] */
     if(PyString_AsStringAndSize(s, &sp, &len)==-1) goto onError;
     for(; sp[--len]=='0';);
     CHECK(t1 = PyString_FromStringAndSize(sp, len+1));
     Py_DECREF(s);

     /* return s */
     return t1;

 onError:
     Py_XDECREF(ip);
     Py_XDECREF(fp);
     Py_XDECREF(t1);
     Py_XDECREF(t2);
     Py_XDECREF(s);
     Py_XDECREF(tthou);
     return NULL;
}

static PyObject *
rational_str(PyRational_Object *self)
{
     return r_str(self, 500);
}

static int
rational_print(PyRational_Object *s, FILE *fp, int flags)
{
	PyObject *str;

	if((str = r_str(s, 500))==NULL) return -1;
	fputs(PyString_AsString(str), fp);
	Py_DECREF(str);
	return 0;
}
	

static char rational_str_doc__[] = \
"r.str(precision) -> <str>\n"\
"returns a string containing a decimal float representation of 'r' with\n"\
"at least 'precision' digits of precision after the decimal place.\n";

static PyObject *
rational_str_method(PyObject *self, PyObject *args)
{
     long l;

     if(!PyArg_ParseTuple(args, "l", &l)) return NULL;
     return r_str((PyRational_Object *)self, l);
}

static long
rational_hash(PyRational_Object *self)
{
     /* hash the same as all ints and longs if self->d==1 */
     if (SIZE(self->d)==1 && ((PyLongObject *)self->d)->ob_digit[0]==1){
          return PyObject_Hash(self->n);
     } else {
          double t;
          t = PyRational_AsDouble(self);
          /* guarantee that large numbers have different hashes */
          if ((t==-1.0 && PyErr_Occurred())) 
               if (PyErr_ExceptionMatches(PyExc_OverflowError)) 
                    return PyObject_Hash(self->n) ^ PyObject_Hash(self->d);
			else
                    return -1;
          /* this test is for pre-2.2 Python where overflow
             errors didn't happen */
		else if (Py_IS_INFINITY(t))
               return PyObject_Hash(self->n) ^ PyObject_Hash(self->d);
          else
               return _Py_HashDouble(t);
     }
}

static PyObject *upcast_floats(PyObject *v, PyObject *w,
			       binaryfunc func)
{
     PyObject *t=NULL, *ans=NULL;

     if(PyFloat_Check(v)) {
	  CHECK(t = PyNumber_Float(w));
	  ans = func(v, t);
	  Py_DECREF(t);
	  return ans;
     }

     if(PyFloat_Check(w)) {
	  CHECK(t=PyNumber_Float(v));
	  ans = func(t, w);
	  Py_DECREF(t);
	  return ans;
     }
     return NULL;

 onError:
     Py_DECREF(t);
     return NULL;
}
	
     

static int convert_binop(PyObject *v, PyObject *w,
                         PyRational_Object **a, PyRational_Object **b)
{
     if(!(PyNumber_Check(v) && PyNumber_Check(w))) {
          return 0;
     }

     if((*a=r_convert(v))==NULL) {
          *b=NULL;
          return 0;
     }

     if((*b=r_convert(w))==NULL) {
          MYDECREF(*a);
          return 0;
     }
     return 1;
}

static PyRational_Object *
x_mul(PyObject *an, PyObject *ad,
      PyObject *bn, PyObject *bd)
{
     PyObject *g1, *g2, *ta, *tb;
     PyObject *zn, *zd;

     g1=g2=ta=tb=zn=zd=NULL;

	/************************
      * g1 = gcd(an, bd)     *
	 * g2 = gcd(ad, bn)     *
	 * zn = (an/g1)(bn/g2)  *
	 * zd = (ad/g2)(bd/g1)  *
	 ************************/
     
     CHECK(g1 = factor_gcd(an, bd));
     CHECK(g2 = factor_gcd(ad, bn));

     CHECK(ta = PyNumber_Divide(an, g1));
     CHECK(tb = PyNumber_Divide(bn, g2));
     CHECK(zn = PyNumber_Multiply(ta, tb));

     Py_DECREF(ta); 
     CHECK(ta = PyNumber_Divide(ad, g2));
     Py_DECREF(tb);
     CHECK(tb = PyNumber_Divide(bd, g1));
     CHECK(zd = PyNumber_Multiply(ta, tb));

     Py_DECREF(ta); Py_DECREF(tb);
     Py_DECREF(g1); Py_DECREF(g2);

     return _PyRational_FROM_FACTORS(zn, zd);

 onError:
     Py_XDECREF(g1); Py_XDECREF(g2);
     Py_XDECREF(ta); Py_XDECREF(tb);
     Py_XDECREF(zn); Py_XDECREF(zd);
     return NULL;
}

static PyRational_Object *
x_add(PyObject *an, PyObject *ad,
      PyObject *bn, PyObject *bd)
{
     PyObject *g1, *g2, *ta, *tb, *tc;
     PyObject *zn, *zd;

     g1=g2=ta=tb=tc=zn=zd=NULL;

     CHECK(g1 = factor_gcd(ad, bd));
	/* if gcd(ad, bd)==1: */
     if(SIZE(g1)==1 && ((PyLongObject *)g1)->ob_digit[0] == 1) {
		/************************************
           * zn = (an*bd)+(ad*bn)             *
           * zd = (ad*bd)                     *
		 ************************************/
          CHECK(ta = PyNumber_Multiply(an, bd));
          CHECK(tb = PyNumber_Multiply(bn, ad));
          CHECK(zn = PyNumber_Add(ta, tb));
          CHECK(zd = PyNumber_Multiply(ad, bd));


          MYDECREF(g1); 
          MYDECREF(ta); MYDECREF(tb);

     } else {
		/*************************************
		 * t = an(bd/g1)+bn(ad/g1)           *
		 * g2 = gcd(t, g1)                   *
		 * zn = t/g2                         *
		 * zd = (ad/g1)(bd/g2)               *
		 * See Knuth Vol. 2, Pp 330          *
		 *************************************/
          CHECK(ta = PyNumber_Divide(bd, g1));
          CHECK(tb = PyNumber_Multiply(an, ta));
          Py_DECREF(ta);
          CHECK(ta = PyNumber_Divide(ad, g1));
          CHECK(tc = PyNumber_Multiply(bn, ta));
          Py_DECREF(ta);
          CHECK(ta = PyNumber_Add(tb, tc));


          CHECK(g2 = factor_gcd(ta, g1));

          CHECK(zn = PyNumber_Divide(ta, g2));

          Py_DECREF(tb); 
          CHECK(tb = PyNumber_Divide(ad, g1));
          Py_DECREF(tc);
          CHECK(tc = PyNumber_Divide(bd, g2));
          CHECK(zd = PyNumber_Multiply(tb, tc));

          Py_DECREF(ta);

          Py_DECREF(tb); Py_DECREF(tc);
          Py_DECREF(g1); Py_DECREF(g2);
     }

     return _PyRational_FROM_FACTORS(zn, zd);
 onError:
     Py_XDECREF(g1); Py_XDECREF(g2);
     Py_XDECREF(ta); Py_XDECREF(tb); Py_XDECREF(tc);
     Py_XDECREF(zn); Py_XDECREF(zd);
     return NULL;
}

static PyObject *
rational_add(PyObject *v, PyObject *w)
{
     PyRational_Object *a, *b, *z;

     CONVERT_BINOP(v, w, &a, &b, PyNumber_Add);

     z = x_add(a->n, a->d, b->n, b->d);
     Py_DECREF(a);
     Py_DECREF(b);
     return (PyObject *)z;
}

static PyObject *
rational_sub(PyObject *v, PyObject *w)
{
     PyRational_Object *a, *b, *z;
     PyObject *t;

     CONVERT_BINOP(v, w, &a, &b, PyNumber_Subtract);

     if(!(t = PyNumber_Negative(b->n))) {
          Py_DECREF(a);
          Py_DECREF(b);
          return NULL;
     }
     z = x_add(a->n, a->d, t, b->d);
     Py_DECREF(a);
     Py_DECREF(b);
     Py_DECREF(t);
     return (PyObject *)z;
}
     

static PyObject *
rational_mul(PyObject *v, PyObject *w)
{
     PyRational_Object *a, *b, *z;

     CONVERT_BINOP(v, w, &a, &b, PyNumber_Multiply);

     z= x_mul(a->n, a->d, b->n, b->d);
     Py_DECREF(a);
     Py_DECREF(b);
     return (PyObject *)z;
}

static PyObject *
rational_floor_div(PyObject *v, PyObject *w)
{
	PyRational_Object *a, *b, *mod;
	PyObject *div;
	CONVERT_BINOP(v, w, &a, &b, PyNumber_FloorDivide);
	
	if(x_divmod(a, b, &div, &mod)==-1) {
		Py_XDECREF(a);
		Py_XDECREF(b);
		Py_XDECREF(div);
		Py_XDECREF(mod);
		return NULL;
	}

	Py_DECREF(a);
	Py_DECREF(b);
	Py_DECREF(mod);
	
	return (PyObject *)div;
}

static PyObject *
rational_div(PyObject *v, PyObject *w)
{
     PyRational_Object *a, *b, *z;

     CONVERT_BINOP(v, w, &a, &b, PyNumber_Divide);
     
     if(SIZE(b->n)==0) {
          PyErr_SetString(PyExc_ZeroDivisionError, "Divide by zero");
          Py_DECREF(a); Py_DECREF(b);
          return NULL;
     }

     z= x_mul(a->n, a->d, b->d, b->n);
     Py_DECREF(a);
     Py_DECREF(b);
     return (PyObject *)z;
}




static int
x_divmod(PyRational_Object *a, PyRational_Object *b,
         PyObject **div, PyRational_Object **mod)
{
     PyRational_Object *t;
     PyObject *t2;

     t2=*div=NULL;
     t=*mod=NULL;
     
     if(SIZE(b->n)==0) {
	  PyErr_SetString(PyExc_ZeroDivisionError, "Divide by zero");
	  return -1;
     }

     CHECK(t = x_mul(a->n, a->d, b->d, b->n));
     CHECK(t2 = PyNumber_Divmod(t->n, t->d));
     CHECK(*div = PyTuple_GET_ITEM(t2, 0));
     Py_INCREF(*div);
     CHECK(*mod = x_mul(PyTuple_GET_ITEM(t2, 1), t->d, b->n, b->d));
     Py_DECREF(t);
     Py_DECREF(t2);
     return 0;

 onError:
     Py_XDECREF(t); Py_XDECREF(t2);
     Py_XDECREF(*div); Py_XDECREF(*mod);
     *div=NULL; *mod=NULL;
     return -1;

}

static PyObject *
rational_mod(PyObject *v, PyObject *w)
{
     PyRational_Object *a, *b, *mod;
     PyObject *div;

     CONVERT_BINOP(v, w, &a, &b, PyNumber_Remainder);

     if(x_divmod(a, b, &div, &mod)==-1) {
          Py_XDECREF(a);
          Py_XDECREF(b);
          Py_XDECREF(div);
          Py_XDECREF(mod);
          return NULL;
     }

     Py_DECREF(a);
     Py_DECREF(b);
     Py_DECREF(div);

     return (PyObject *)mod;
}
     

static PyObject *
rational_divmod(PyObject *v, PyObject *w)
{
     PyRational_Object *a, *b, *mod;
     PyObject *div, *tup;

     CONVERT_BINOP(v, w, &a, &b, PyNumber_Divmod);

     if(x_divmod(a, b, &div, &mod)==-1) return NULL;

     tup = PyTuple_New(2);
     if(tup!=NULL) {
          PyTuple_SetItem(tup, 0, div);
          PyTuple_SetItem(tup, 1, (PyObject *)mod);
     } else {
          Py_DECREF(div);
          Py_DECREF(mod);
     }
     Py_DECREF(a);
     Py_DECREF(b);
     return tup;
}

static PyObject *
rational_pow(PyObject *bb, PyObject *ee, PyObject *mm)
{
     PyObject *e, *zn, *zd, *bn, *bd;
     PyRational_Object *b, *z;

     e=zn=zd=bn=bd=NULL;
     z=NULL;
     b=(PyRational_Object *)bb; /* b is never used if it isn't a rational */

	/* don't allow third argument (and give same error as floats) */
     if(mm != Py_None) {
          PyErr_SetString(PyExc_TypeError, "pow() 3rd argument not "
                          "allowed unless all arguments are integers");
          return NULL;
     }
     
     /* switch to floats if any argument is a float, or if
        exp is a rational */
     if(PyFloat_Check(bb) || PyFloat_Check(ee) || PyRational_Check(ee)) {
          PyObject *c;

          CHECK(bn=PyNumber_Float(bb));
          CHECK(bd=PyNumber_Float(ee));
          c = PyNumber_Power(bn, bd, mm); /* mm is Py_None */
          Py_DECREF(bn);
          Py_DECREF(bd);
          return c;
     }

	/* convert e to a long */
     e = PyNumber_Long(ee);
     if(e==NULL) {
          Py_INCREF(Py_NotImplemented);
          return Py_NotImplemented;
     }

	/* invert for negative exponents */
     if(SIZE(e)>=0) {
          PyRational_AsFactors(b, &bn, &bd);
     } else {
          PyRational_AsFactors(b, &bd, &bn);
          INPLACE1(PyNumber_Absolute, e);
     }

	/* raise numerator and denominator */
     CHECK(zn = PyNumber_Power(bn, e, Py_None));
     CHECK(zd = PyNumber_Power(bd, e, Py_None));
     z = _PyRational_FROM_FACTORS(zn, zd);

     Py_DECREF(bn); Py_DECREF(bd);
     Py_DECREF(e);
     return (PyObject *)z;

 onError:
     Py_XDECREF(e); Py_XDECREF(zn); Py_XDECREF(zd);
     Py_XDECREF(bn); Py_XDECREF(bd);
     return NULL;
}

static PyObject *
rational_neg(PyRational_Object *self)
{
     PyObject *t;

     if(!(t=PyNumber_Negative(self->n))) return NULL;
     Py_INCREF(self->d);
     return (PyObject *)_PyRational_FROM_FACTORS(t, self->d);
}

static PyObject *
rational_pos(PyRational_Object *self)
{
     Py_INCREF(self);
     return (PyObject *)self;
}

static PyObject *
rational_abs(PyRational_Object *self)
{
     if(SIZE(self->n)<0)
          return rational_neg(self);
     else
          return rational_pos(self);
}

static int 
rational_nonzero(PyRational_Object *self)
{
     return SIZE(self->n)!=0;
}

static int
rational_coerce(PyObject **aa, PyObject **bb)
{
     PyObject *z;

     if(!PyNumber_Check(*bb)) {
          return 1;
     }

     if((z=(PyObject *)r_convert(*bb))==NULL) {
          if(PyErr_Occurred()) {
               return -1;
          }
          
#ifndef WITHOUT_COMPLEX
          if(PyComplex_Check(*bb)) {
               z = PyComplex_FromDoubles(
                    PyRational_AsDouble((PyRational_Object *)*aa),
                    (double)0);
               *aa=z;
               Py_INCREF(*bb);
               return 0;
          }
#endif

	  /* we don't know how to convert */
	  return 1;
     }

     *bb = z;
     Py_INCREF(*aa);
     return 0;
}

static PyObject *
rational_aslong(PyRational_Object *self)
{
     return PyNumber_Divide(self->n, self->d);
}

static PyObject *
rational_asint(PyRational_Object *self)
{
     return PyNumber_Int(rational_aslong(self));
}
 
static PyObject *
rational_asfloat(PyRational_Object *self)
{
     double d;

     d = PyRational_AsDouble(self);
     if(d==-1.0 && PyErr_Occurred()) return NULL;
     else return PyFloat_FromDouble(d);
}


static char rational_trim_doc__[] = \
"in.trim(max_d) -> <rational>\n"\
"returns the closest rational r to in such that r.denominator <= max_d\n";

/************************************************************************
ugly, ugly code.  But I couldn't find a more elegant way to express it.

Credit goes to Moshe Zadka and Tim Peters for working this out in a
Python module I drew from
*************************************************************************/

static PyObject *
r_trim(PyRational_Object *self, PyObject *max_d)
{
     PyObject *n, *d,
          *last_n, *last_d,
          *cur_n, *cur_d,
          *next_n, *next_d,
          *blast_n, *blast_d,
          *alt_n, *alt_d,
          *t, *t2, *t3;
     PyObject *div, *mod, *tup;
     PyRational_Object *r, *r1, *r2, *z;

     /* set everything to NULL */
     n=d=last_n=last_d=cur_n=cur_d=next_n=next_d=NULL;
     blast_n=blast_d=alt_n=alt_d=t=t2=t3=div=mod=tup=NULL;
     r=r1=r2=z=NULL;

     assert(SIZE(max_d)!=0);

     /* special case when self->d <= max_d */
     if(PyObject_Compare(self->d, max_d)!=1) {
          Py_INCREF(self);
          return (PyObject *)self;
     }
     
     /* special case when max_d == 1 */
     if ((SIZE(max_d)==1) && (((PyLongObject *)max_d)->ob_digit[0]==1)) {
          CHECK(next_n = PyNumber_Divide(self->n, self->d));
          CHECK(next_d = PyLong_FromLong(1L));
          return (PyObject *)_PyRational_FROM_FACTORS(next_n, next_d);
     }

     n = self->n;
     d = self->d;
     Py_INCREF(n); Py_INCREF(d);
     CHECK(cur_n = PyLong_FromLong(1));
     CHECK(cur_d = PyLong_FromLong(0));
     CHECK(last_n = PyLong_FromLong(0));
     CHECK(last_d = PyLong_FromLong(1));

     do {
          CHECK(tup = PyNumber_Divmod(n, d));
          CHECK(div = PyTuple_GET_ITEM(tup, 0));
          CHECK(mod = PyTuple_GET_ITEM(tup, 1));
          Py_INCREF(div); Py_INCREF(mod);
          MYDECREF(tup);
          Py_DECREF(n); 
          n = d;
          d = mod;
          mod = NULL;

          CHECK(t = PyNumber_Multiply(cur_n, div));
          CHECK(next_n = PyNumber_Add(last_n, t));

          Py_DECREF(t);
          CHECK(t = PyNumber_Multiply(cur_d, div));
          CHECK(next_d = PyNumber_Add(last_d, t));
          MYDECREF(t);

          Py_XDECREF(blast_n); Py_XDECREF(blast_d);
          blast_n = last_n; blast_d = last_d;
          last_n = cur_n; last_d = cur_d;
          cur_n = next_n; cur_d = next_d;
          next_n = next_d = NULL;
          MYDECREF(div); 

     } while (SIZE(d)!=0 && PyObject_Compare(cur_d, max_d)==-1) ;
     MYDECREF(n); MYDECREF(d);
     
     if(PyObject_Compare(cur_d, max_d)==0) {
          Py_INCREF(cur_n); Py_INCREF(cur_d);
          z = _PyRational_FROM_FACTORS(cur_n, cur_d);
          goto end;
     }

     CHECK(t2 = PyNumber_Subtract(max_d, blast_d));
     CHECK(t = PyNumber_Divide(t2, last_d));

     Py_DECREF(t2);
     CHECK(t2 = PyNumber_Multiply(t, last_n));
     CHECK(alt_n = PyNumber_Add(blast_n, t2));

     Py_DECREF(t2);
     CHECK(t2 = PyNumber_Multiply(t, last_d));
     CHECK(alt_d = PyNumber_Add(blast_d, t2));
     MYDECREF(t2);
     MYDECREF(t);

     CHECK(t3 = PyNumber_Negative(self->n));
     CHECK(r = x_add(alt_n, alt_d, t3, self->d));
     CHECK(r1 = (PyRational_Object *)rational_abs((PyRational_Object *)r));
     
     Py_DECREF(r);
     CHECK(r = x_add(last_n, last_d, t3, self->d));
     CHECK(r2 = (PyRational_Object *)rational_abs((PyRational_Object *)r));
     MYDECREF(r);
     MYDECREF(t3);

     if (rational_cmp(r1, r2)==-1) {
          Py_DECREF(r1); Py_DECREF(r2);
          Py_INCREF(alt_n); Py_INCREF(alt_d);
          z = _PyRational_FROM_FACTORS(alt_n, alt_d);
          goto end;
     } else {
          Py_DECREF(r1); Py_DECREF(r2);
          Py_INCREF(last_n); Py_INCREF(last_d);
          z = _PyRational_FROM_FACTORS(last_n, last_d);
          goto end;
     }

 onError:
     Py_XDECREF(n); Py_XDECREF(d);
     Py_XDECREF(next_n); Py_XDECREF(next_d);
     Py_XDECREF(t); Py_XDECREF(t2); Py_XDECREF(t3);
     Py_XDECREF(r); Py_XDECREF(r1); Py_XDECREF(r2);
     Py_XDECREF(div); Py_XDECREF(mod); Py_XDECREF(tup);
 end:
     Py_XDECREF(cur_n); Py_XDECREF(cur_d);
     Py_XDECREF(last_n);  Py_XDECREF(last_d);
     Py_XDECREF(blast_n); Py_XDECREF(blast_d);
     Py_XDECREF(alt_n);  Py_XDECREF(alt_d);
     return (PyObject *)z;
}

static PyObject *
rational_trim(PyObject *self, PyObject *args)
{
     PyObject *max_d;
     PyObject *z;

     if(!PyArg_ParseTuple(args, "O", &max_d)) return NULL;
     

     if(!(PyInt_Check(max_d) || PyLong_Check(max_d))) {
          PyErr_Format(PyExc_TypeError,
                       "integer expected, %.80s found",
                       max_d->ob_type->tp_name);
          return NULL;
     }

     if((max_d = PyNumber_Long(max_d))==NULL) return NULL;

     z = r_trim((PyRational_Object *)self, max_d);
     Py_DECREF(max_d);
     return z;

}

     

static PyMethodDef rational_methods[] = {
     {"trim", rational_trim, METH_VARARGS, rational_trim_doc__},
     {"str", rational_str_method, METH_VARARGS, rational_str_doc__},
     {NULL, NULL}
};

static PyMemberDef rational_members[] = {
     {"numerator", T_OBJECT, offsetof(PyRational_Object, n), READONLY},
     {"denominator", T_OBJECT, offsetof(PyRational_Object, d), READONLY},
     // Added for compatibility with Rat.py
     {"num", T_OBJECT, offsetof(PyRational_Object, n), READONLY},
     {"den", T_OBJECT, offsetof(PyRational_Object, d), READONLY},
     {0},
};

static PyMethodDef crat_methods[] = {
     {"gcd", crat_gcd, METH_VARARGS, crat_gcd_doc__},
     {NULL, NULL}
};



void
initcrat(void)
{
     PyObject *m, *d;

     /* patch object type for broken MSVC */
     PyRational_Type.ob_type = &PyType_Type; 

     /* Set this here because gcc 3.3 complains */
     PyRational_Type.tp_getattro = &PyObject_GenericGetAttr;
     PyRational_Type.tp_alloc = &PyType_GenericAlloc;

     m = Py_InitModule3("crat", crat_methods, crat_module_documentation);
	d = PyModule_GetDict(m);

	PyDict_SetItemString(d, "rational", (PyObject *)&PyRational_Type);

     if (PyErr_Occurred()) Py_FatalError("can't initialize module crat.");
}

static PyNumberMethods PyRationalAsNumber = {
     (binaryfunc)rational_add,	/*nb_add*/
     (binaryfunc)rational_sub,	/*nb_subtract*/
     (binaryfunc)rational_mul,	/*nb_multiply*/
     (binaryfunc)rational_div,	/*nb_divide*/
     (binaryfunc)rational_mod,	/*nb_remainder*/
     (binaryfunc)rational_divmod,	/*nb_divmod*/
     (ternaryfunc)rational_pow,	/*nb_power*/
     (unaryfunc)rational_neg,	/*nb_negative*/
     (unaryfunc)rational_pos,	/*tp_positive*/
     (unaryfunc)rational_abs,	/*tp_absolute*/
     (inquiry)rational_nonzero,	/*tp_nonzero*/
     0,	/*nb_invert*/
     0,	/*nb_lshift*/
     0,	/*nb_rshift*/
     0,	/*nb_and*/
     0,	/*nb_xor*/
     0,	/*nb_or*/
     (coercion)rational_coerce,	/*nb_coerce*/
     (unaryfunc)rational_asint,	/*nb_int*/
     (unaryfunc)rational_aslong,	/*nb_long*/
     (unaryfunc)rational_asfloat,	/*nb_float*/
     0,	/*nb_oct*/
     0,	/*nb_hex*/
     0,				/*nb_inplace_add*/
     0,				/*nb_inplace_subtract*/
     0,				/*nb_inplace_multiply*/
     0,				/*nb_inplace_divide*/
     0,				/*nb_inplace_remainder*/
     0,				/*nb_inplace_power*/
     0,				/*nb_inplace_lshift*/
     0,				/*nb_inplace_rshift*/
     0,				/*nb_inplace_and*/
     0,				/*nb_inplace_xor*/
     0,				/*nb_inplace_or*/
	(binaryfunc)rational_floor_div,  /* nb_floor_divide */
	(binaryfunc)rational_div,        /* nb_true_divide */
	0,                       /* nb_inplace_floor_divide */
	0,                       /* nb_inplace_true_divide */
};

static PyTypeObject PyRational_Type = {
     PyObject_HEAD_INIT(NULL) /* set by init function for broken MSVC */
     0,
     "rational",
     sizeof(PyRational_Object),
     0,
     (destructor)rational_dealloc,	/*tp_dealloc*/
     (printfunc)rational_print,				/*tp_print*/
     0,                         /*tp_getattr*/
     0,				/*tp_setattr*/
     (cmpfunc)rational_cmp,	/*tp_compare*/
     (reprfunc)rational_repr,	/*tp_repr*/
     &PyRationalAsNumber, /*tp__as_number*/
     0,				/*tp_as_sequence*/
     0,				/*tp_as_mapping*/
     (hashfunc)rational_hash,   /*tp_hash*/
     0,              		/*tp_call*/
     (reprfunc)rational_str,	/*tp_str*/
     0, /*PyObject_GenericGetAttr,*/	/*tp_getattro*/
     0,				/*tp_setattro*/
     0,				/*tp_as_buffer*/
     Py_TPFLAGS_DEFAULT|Py_TPFLAGS_CHECKTYPES|
	 Py_TPFLAGS_BASETYPE,    /*tp_flags*/
     rational_doc,				/* tp_doc */
     0,					/* tp_traverse */
     0,					/* tp_clear */
     rational_richcompare,	/* tp_richcompare */
     0,					/* tp_weaklistoffset */
     0,					/* tp_iter */
     0,					/* tp_iternext */
     rational_methods,			/* tp_methods */
     rational_members,			/* tp_members */
     0,					/* tp_getset */
     0,					/* tp_base */
     0,					/* tp_dict */
     0,					/* tp_descr_get */
     0,					/* tp_descr_set */
     0,					/* tp_dictoffset */
     0,					/* tp_init */
     0, /* PyType_GenericAlloc, */		/* tp_alloc */
     rational_new,			/* tp_new */
     rational_free,           /* tp_free can't be PyObject_Del because
						   of a bug in 2.2 includes */
};
