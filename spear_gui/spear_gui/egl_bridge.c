#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <EGL/egl.h>
#include <gst/gst.h>
#include <gst/gl/gl.h>
#include <gst/gl/egl/gstgldisplay_egl.h>

/* ── get_egl_handles() ──────────────────────────────────────────────────────
 *
 * Call from QOpenGLWidget.initializeGL() — at that point Qt has already
 * called eglMakeCurrent so both handles are valid.
 *
 * Returns (egl_display_ptr, egl_context_ptr) as Python integers.
 */
static PyObject *
get_egl_handles(PyObject *self, PyObject *args)
{
    EGLDisplay display = eglGetCurrentDisplay();
    EGLContext context = eglGetCurrentContext();

    if (display == EGL_NO_DISPLAY) {
        PyErr_SetString(PyExc_RuntimeError,
            "eglGetCurrentDisplay() returned EGL_NO_DISPLAY — "
            "must be called from inside QOpenGLWidget.initializeGL()");
        return NULL;
    }
    if (context == EGL_NO_CONTEXT) {
        PyErr_SetString(PyExc_RuntimeError,
            "eglGetCurrentContext() returned EGL_NO_CONTEXT — "
            "must be called from inside QOpenGLWidget.initializeGL()");
        return NULL;
    }

    return Py_BuildValue("(KK)",
        (unsigned long long)(uintptr_t)display,
        (unsigned long long)(uintptr_t)context);
}

/* ── wrap_gst_gl_context(display_ptr, context_ptr) ──────────────────────────
 *
 * Takes the two integers from get_egl_handles() and wraps them into
 * GStreamer GL objects. Returns a PyCapsule containing a GstContext that
 * you set on the pipeline in response to a NEED_CONTEXT bus message.
 *
 * The GstGLDisplayEGL and GstGLContext are ref-counted; the capsule destructor
 * unrefs the GstContext when Python GCs the capsule.
 */
static void
gst_context_capsule_destructor(PyObject *capsule)
{
    GstContext *ctx = (GstContext *)PyCapsule_GetPointer(capsule, "GstContext");
    if (ctx)
        gst_context_unref(ctx);
}

static PyObject *
wrap_gst_gl_context(PyObject *self, PyObject *args)
{
    unsigned long long display_int, context_int;
    if (!PyArg_ParseTuple(args, "KK", &display_int, &context_int))
        return NULL;

    EGLDisplay egl_display = (EGLDisplay)(uintptr_t)display_int;
    EGLContext egl_context = (EGLContext)(uintptr_t)context_int;

    /* Wrap the EGL display */
    GstGLDisplayEGL *gst_display = gst_gl_display_egl_new_with_egl_display(egl_display);
    if (!gst_display) {
        PyErr_SetString(PyExc_RuntimeError, "gst_gl_display_egl_new_with_egl_display() failed");
        return NULL;
    }

    /* Wrap the EGL context — GL_API_OPENGL for Mesa/AMD, GL_API_OPENGL for NVIDIA */
    GstGLContext *gst_gl_ctx = gst_gl_context_new_wrapped(
        GST_GL_DISPLAY(gst_display),
        (guintptr)egl_context,
        GST_GL_PLATFORM_EGL,
        GST_GL_API_OPENGL3
    );
    if (!gst_gl_ctx) {
        gst_object_unref(gst_display);
        PyErr_SetString(PyExc_RuntimeError, "gst_gl_context_new_wrapped() failed");
        return NULL;
    }

    /* Build the two GstContext objects GStreamer expects from NEED_CONTEXT */
    GstContext *display_ctx = gst_context_new(GST_GL_DISPLAY_CONTEXT_TYPE, TRUE);
    gst_structure_set(
        gst_context_writable_structure(display_ctx),
        "display", GST_TYPE_GL_DISPLAY, gst_display, NULL
    );

    GstContext *app_ctx = gst_context_new("gst.gl.app_context", TRUE);
    gst_structure_set(
        gst_context_writable_structure(app_ctx),
        "context", GST_TYPE_GL_CONTEXT, gst_gl_ctx, NULL
    );

    gst_object_unref(gst_display);
    gst_object_unref(gst_gl_ctx);

    /* Return both contexts as capsules — caller sets them on the pipeline */
    PyObject *display_cap = PyCapsule_New(display_ctx, "GstContext", gst_context_capsule_destructor);
    PyObject *app_cap     = PyCapsule_New(app_ctx,     "GstContext", gst_context_capsule_destructor);
    return Py_BuildValue("(OO)", display_cap, app_cap);
}

/* ── set_pipeline_context(pipeline_ptr, capsule) ────────────────────────────
 *
 * Calls gst_element_set_context() on the pipeline. Called twice — once for
 * the display context and once for the app context — in response to each
 * NEED_CONTEXT bus message.
 *
 * pipeline_ptr: integer from id(pipeline) won't work — we accept the pipeline
 * as a PyCapsule produced by wrap_pipeline() below, or the caller passes the
 * Gst.Pipeline directly via its __gpointer__ attribute which gi exposes.
 *
 * Simpler: we expose a function that takes the two capsules and a pipeline
 * gpointer integer, and calls set_context on both.
 */
static PyObject *
set_pipeline_contexts(PyObject *self, PyObject *args)
{
    PyObject *pipeline_cap, *display_cap, *app_cap;
    if (!PyArg_ParseTuple(args, "OOO", &pipeline_cap, &display_cap, &app_cap))
        return NULL;

    /* pipeline.__gpointer__ is a PyCapsule in this version of PyGObject */
    GstElement *pipeline = (GstElement *)PyCapsule_GetPointer(pipeline_cap, NULL);
    if (!pipeline) {
        PyErr_SetString(PyExc_ValueError, "Invalid pipeline capsule");
        return NULL;
    }

    GstContext *display_ctx = (GstContext *)PyCapsule_GetPointer(display_cap, "GstContext");
    GstContext *app_ctx     = (GstContext *)PyCapsule_GetPointer(app_cap,     "GstContext");

    if (!display_ctx || !app_ctx) {
        PyErr_SetString(PyExc_ValueError, "Invalid GstContext capsule");
        return NULL;
    }

    gst_element_set_context(pipeline, display_ctx);
    gst_element_set_context(pipeline, app_ctx);

    Py_RETURN_NONE;
}

/* ── get_gl_texture_id(buffer_gpointer) ─────────────────────────────────────
 *
 * Extracts the OpenGL texture ID from a GstBuffer containing GLMemory.
 * The buffer is passed as its raw gpointer integer (from gi's __gpointer__).
 *
 * Returns the texture ID as a Python integer, or raises RuntimeError.
 */
static PyObject *
get_gl_texture_id(PyObject *self, PyObject *args)
{
    PyObject *buf_cap;
    if (!PyArg_ParseTuple(args, "O", &buf_cap))
        return NULL;

    GstBuffer *buf = (GstBuffer *)PyCapsule_GetPointer(buf_cap, NULL);
    if (!buf) {
        PyErr_SetString(PyExc_ValueError, "Invalid buffer capsule");
        return NULL;
    }

    GstMemory *mem = gst_buffer_peek_memory(buf, 0);
    if (!mem || !gst_is_gl_memory(mem)) {
        PyErr_SetString(PyExc_RuntimeError,
            "Buffer does not contain GLMemory — "
            "pipeline must end with appsink caps=video/x-raw(memory:GLMemory)");
        return NULL;
    }

    GstGLMemory *gl_mem = (GstGLMemory *)mem;
    guint texture_id = gst_gl_memory_get_texture_id(gl_mem);

    return PyLong_FromUnsignedLong((unsigned long)texture_id);
}

/* ── module ─────────────────────────────────────────────────────────────────*/

static PyMethodDef EglBridgeMethods[] = {
    {"get_egl_handles",       get_egl_handles,       METH_NOARGS,  "→ (display_ptr, context_ptr)"},
    {"wrap_gst_gl_context",   wrap_gst_gl_context,   METH_VARARGS, "(display_ptr, context_ptr) → (display_capsule, app_capsule)"},
    {"set_pipeline_contexts", set_pipeline_contexts, METH_VARARGS, "(pipeline_capsule, display_capsule, app_capsule) → None"},
    {"get_gl_texture_id",     get_gl_texture_id,     METH_VARARGS, "(buffer_capsule) → texture_id"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef egl_bridge_module = {
    PyModuleDef_HEAD_INIT, "egl_bridge", NULL, -1, EglBridgeMethods
};

PyMODINIT_FUNC
PyInit_egl_bridge(void)
{
    return PyModule_Create(&egl_bridge_module);
}