#include <Python.h>
#include "unicode/ustring.h"
#include "unicode/ubidi.h"

#define ALLOWED_CONTROL_CHARS "\t\n\v\f\r"

char allowed_control_lut[128] = {0}; // filled in mod_exec

static int
raise_icu_error(UErrorCode err) {
    if (U_FAILURE(err)) {
        PyErr_Format(PyExc_RuntimeError, "ICU error: %s", u_errorName(err));
        return 1;
    }
    return 0;
}
static int
append_nit_args(PyObject *list, char *format, ...) {
    va_list vl;
    va_start(vl, format);
    PyObject *warning = Py_VaBuildValue(format, vl);
    va_end(vl);
    if (!warning) return 1;
    int res = PyList_Append(list, warning);
    Py_DECREF(warning);
    if (res != 0) return 1;
    return 0;
}

static PyObject *
process_source(PyObject *module, PyObject *buf) {
    PyObject *retval = NULL;
    PyObject *result = NULL;
    PyObject *bidimap_bytes = NULL;
    UChar *u_buf = NULL;
    int32_t *bidimap_source = NULL;
    UBiDi *bidi = NULL;
    int res;
    if (!PyUnicode_Check(buf)) {
        PyErr_SetString(PyExc_TypeError, "buf must be a string");
        goto finally;
    }
    Py_ssize_t num_codepoints = PyUnicode_GetLength(buf);
    result = PyList_New(0);
    if (!result) goto finally;

    // Get the UTF-8 buffer
    Py_ssize_t utf8_size;
    const unsigned char* utf8_buf =
        (const unsigned char*)PyUnicode_AsUTF8AndSize(buf, &utf8_size);
    if (!utf8_buf) goto finally;

    // Get the ICU buffer
    // There's always more utf8 bytes than utf8 UChars.
    // This might allocate a bit more memory than necessary.
    int32_t u_size;
    u_buf = PyMem_Malloc(utf8_size * sizeof(UChar));
    if (!u_buf) goto finally;
    UErrorCode err = U_ZERO_ERROR;
    u_strFromUTF8(u_buf, utf8_size, &u_size, (const char*)utf8_buf, utf8_size, &err);
    if (raise_icu_error(err)) goto finally;

    // Search for non-allowed control characters
    UChar32 c;
    for (int32_t u_pos=0, index=0; u_pos < u_size; /*U16_NEXT, */ index++ ) {
        int is_bad_control;
        if ((c = u_buf[u_pos]) < sizeof(allowed_control_lut)) {
            // ASCII case, check our lookup table
            u_pos++;
            is_bad_control = !allowed_control_lut[c];
        } else {
            // Check Unicode database. All nonascii controls are bad.
            U16_NEXT(u_buf, u_pos, u_size, c);
            is_bad_control =
                u_getIntPropertyValue(c, UCHAR_GENERAL_CATEGORY_MASK)
                & U_GC_C_MASK;
        }
        if (is_bad_control) {
            res = append_nit_args(result, "si", "ControlChar", (int)index);
            if (res != 0) goto finally;
        }
    }

    // Build the BIDI map
    bidi = ubidi_open();
    if (!bidi) {
        PyErr_NoMemory();
        goto finally;
    }
    ubidi_setPara(bidi, u_buf, u_size, UBIDI_DEFAULT_LTR, NULL, &err);
    if (raise_icu_error(err)) goto finally;
    if (ubidi_getDirection(bidi) != UBIDI_LTR) {
        // XXX this allocates lots of memory: ~8 bytes for each char
        // First. 4B per UTF-16 char for ICU to work with
        bidimap_source = PyMem_Malloc(u_size * sizeof(int32_t));
        if (!bidimap_source) goto finally;
        // Then. 4B per Unicode codepoint for Python-compatible indexing
        // (a Python bytes object is abused for the storage)
        bidimap_bytes = PyBytes_FromStringAndSize(
            NULL, num_codepoints * sizeof(int32_t));
        if (!bidimap_bytes) goto finally;
        int32_t *bidimap = (int32_t *)PyBytes_AsString(bidimap_bytes);
        if (!bidimap) goto finally;
        // Perform the BIDI algorithm & get the logical map
        ubidi_getLogicalMap(bidi, bidimap_source, &err);
        if (raise_icu_error(err)) goto finally;
        // Copy to the Python-compatible buffer
        for (int32_t u_pos=0, index=0; u_pos < u_size; /*U16_NEXT, */ index++ ) {
            assert(index < num_codepoints);
            bidimap[index] = bidimap_source[u_pos];
            U16_NEXT(u_buf, u_pos, u_buf, c);
        }
        assert(index == num_codepoints);
    }

    retval = Py_BuildValue(
        "OO", result, bidimap_bytes ? bidimap_bytes : Py_None);
finally:
    Py_XDECREF(result);
    Py_XDECREF(bidimap_bytes);
    PyMem_Free(u_buf);
    PyMem_Free(bidimap_source);
    if (bidi) ubidi_close(bidi);
    return retval;
}


static int mod_exec(PyObject *module) {
    PyModule_AddStringMacro(module, ALLOWED_CONTROL_CHARS);
    // allow exceptions
    for (char *s=ALLOWED_CONTROL_CHARS; *s; s++) {
        assert(*s < sizeof(allowed_ascii_control_lut));
        allowed_control_lut[(int)*s] = 1;
    }
    // allow non-controls
    for (int c=32; c<127; c++) {
        assert(c < sizeof(allowed_control_lut));
        allowed_control_lut[c] = 1;
    }
    return 0;
}

static PyMethodDef mod_methods[] = {
    {"process_source", process_source, METH_O, NULL},
    //{"process_token", process_token, METH_VARARGS, NULL},
    {NULL, NULL}
};

static PyModuleDef_Slot mod_slots[] = {
    {Py_mod_exec, mod_exec},
    {0},
};

PyDoc_STRVAR(mod_doc, "linter internals");

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_linter",
    .m_doc = mod_doc,
    .m_size = 0,
    .m_methods = mod_methods,
    .m_slots = mod_slots,
};

PyMODINIT_FUNC
PyInit__linter(void)
{
    return PyModuleDef_Init(&module);
}
