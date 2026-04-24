#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdbool.h>
#include <stdint.h>

#include "axidev-io/c_api.h"


static PyObject *listener_callback = NULL;


static void clear_listener_callback(void) {
  PyObject *callback = listener_callback;
  listener_callback = NULL;
  Py_XDECREF(callback);
}


static PyObject *bool_result(bool value) {
  if (value) {
    Py_RETURN_TRUE;
  }
  Py_RETURN_FALSE;
}


static int set_dict_bool(PyObject *dict, const char *key, bool value) {
  PyObject *item = value ? Py_True : Py_False;
  return PyDict_SetItemString(dict, key, item);
}


static PyObject *build_capabilities_dict(
    const axidev_io_keyboard_capabilities_t *capabilities) {
  PyObject *dict = PyDict_New();
  if (dict == NULL) {
    return NULL;
  }

  if (set_dict_bool(dict, "can_inject_keys", capabilities->can_inject_keys) < 0 ||
      set_dict_bool(dict, "can_inject_text", capabilities->can_inject_text) < 0 ||
      set_dict_bool(dict, "can_simulate_hid", capabilities->can_simulate_hid) < 0 ||
      set_dict_bool(dict, "supports_key_repeat", capabilities->supports_key_repeat) < 0 ||
      set_dict_bool(dict, "needs_accessibility_perm",
                    capabilities->needs_accessibility_perm) < 0 ||
      set_dict_bool(dict, "needs_input_monitoring_perm",
                    capabilities->needs_input_monitoring_perm) < 0 ||
      set_dict_bool(dict, "needs_uinput_access",
                    capabilities->needs_uinput_access) < 0) {
    Py_DECREF(dict);
    return NULL;
  }

  return dict;
}


static PyObject *build_key_mod_dict(
    axidev_io_keyboard_key_with_modifier_t key_mod) {
  return Py_BuildValue("{s:i,s:i}", "key", (int)key_mod.key, "mods",
                       (int)key_mod.mods);
}


static PyObject *build_listener_event_dict(
    uint32_t codepoint, axidev_io_keyboard_key_with_modifier_t key_mod,
    bool pressed) {
  return Py_BuildValue("{s:I,s:i,s:i,s:O}", "codepoint", codepoint, "key",
                       (int)key_mod.key, "mods", (int)key_mod.mods, "pressed",
                       pressed ? Py_True : Py_False);
}


static void listener_bridge(
    uint32_t codepoint, axidev_io_keyboard_key_with_modifier_t key_mod,
    bool pressed, void *user_data) {
  (void)user_data;

  PyGILState_STATE gil_state = PyGILState_Ensure();
  if (listener_callback != NULL) {
    PyObject *event = build_listener_event_dict(codepoint, key_mod, pressed);
    if (event != NULL) {
      PyObject *result = PyObject_CallOneArg(listener_callback, event);
      if (result == NULL) {
        PyErr_WriteUnraisable(listener_callback);
      } else {
        Py_DECREF(result);
      }
      Py_DECREF(event);
    }
  }
  PyGILState_Release(gil_state);
}


static PyObject *mod_initialize(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  return bool_result(axidev_io_keyboard_initialize());
}


static PyObject *mod_free(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  axidev_io_listener_stop();
  clear_listener_callback();
  axidev_io_keyboard_free();
  Py_RETURN_NONE;
}


static PyObject *mod_is_ready(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  return bool_result(axidev_io_keyboard_is_ready());
}


static PyObject *mod_get_backend(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  return PyLong_FromLong((long)axidev_io_keyboard_type());
}


static PyObject *mod_get_capabilities(PyObject *self, PyObject *Py_UNUSED(args)) {
  axidev_io_keyboard_capabilities_t capabilities;
  (void)self;

  axidev_io_keyboard_get_capabilities(&capabilities);
  return build_capabilities_dict(&capabilities);
}


static PyObject *mod_request_permissions(PyObject *self,
                                         PyObject *Py_UNUSED(args)) {
  (void)self;
  return bool_result(axidev_io_keyboard_request_permissions());
}


static PyObject *mod_key_down(PyObject *self, PyObject *args) {
  int key = 0;
  int mods = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "ii", &key, &mods)) {
    return NULL;
  }

  return bool_result(axidev_io_keyboard_key_down(
      (axidev_io_keyboard_key_with_modifier_t){.key = (axidev_io_keyboard_key_t)key,
                                               .mods = (axidev_io_keyboard_modifier_t)mods}));
}


static PyObject *mod_key_up(PyObject *self, PyObject *args) {
  int key = 0;
  int mods = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "ii", &key, &mods)) {
    return NULL;
  }

  return bool_result(axidev_io_keyboard_key_up(
      (axidev_io_keyboard_key_with_modifier_t){.key = (axidev_io_keyboard_key_t)key,
                                               .mods = (axidev_io_keyboard_modifier_t)mods}));
}


static PyObject *mod_key_repeat(PyObject *self, PyObject *args) {
  int key = 0;
  int mods = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "ii", &key, &mods)) {
    return NULL;
  }

  return bool_result(axidev_io_keyboard_key_repeat(
      (axidev_io_keyboard_key_with_modifier_t){.key = (axidev_io_keyboard_key_t)key,
                                               .mods = (axidev_io_keyboard_modifier_t)mods}));
}


static PyObject *mod_tap(PyObject *self, PyObject *args) {
  int key = 0;
  int mods = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "ii", &key, &mods)) {
    return NULL;
  }

  return bool_result(axidev_io_keyboard_tap(
      (axidev_io_keyboard_key_with_modifier_t){.key = (axidev_io_keyboard_key_t)key,
                                               .mods = (axidev_io_keyboard_modifier_t)mods}));
}


static PyObject *mod_active_modifiers(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  return PyLong_FromUnsignedLong(axidev_io_keyboard_active_modifiers());
}


static PyObject *mod_hold_modifiers(PyObject *self, PyObject *args) {
  unsigned int mods = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "I", &mods)) {
    return NULL;
  }

  return bool_result(
      axidev_io_keyboard_hold_modifier((axidev_io_keyboard_modifier_t)mods));
}


static PyObject *mod_release_modifiers(PyObject *self, PyObject *args) {
  unsigned int mods = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "I", &mods)) {
    return NULL;
  }

  return bool_result(
      axidev_io_keyboard_release_modifier((axidev_io_keyboard_modifier_t)mods));
}


static PyObject *mod_release_all_modifiers(PyObject *self,
                                           PyObject *Py_UNUSED(args)) {
  (void)self;
  return bool_result(axidev_io_keyboard_release_all_modifiers());
}


static PyObject *mod_type_text(PyObject *self, PyObject *args) {
  PyObject *text_obj = NULL;
  const char *text = NULL;
  (void)self;

  if (!PyArg_ParseTuple(args, "U", &text_obj)) {
    return NULL;
  }

  text = PyUnicode_AsUTF8(text_obj);
  if (text == NULL) {
    return NULL;
  }

  return bool_result(axidev_io_keyboard_type_text(text));
}


static PyObject *mod_type_character(PyObject *self, PyObject *args) {
  unsigned int codepoint = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "I", &codepoint)) {
    return NULL;
  }

  return bool_result(axidev_io_keyboard_type_character((uint32_t)codepoint));
}


static PyObject *mod_flush(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  axidev_io_keyboard_flush();
  Py_RETURN_NONE;
}


static PyObject *mod_set_key_delay(PyObject *self, PyObject *args) {
  unsigned int delay_us = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "I", &delay_us)) {
    return NULL;
  }

  axidev_io_keyboard_set_key_delay((uint32_t)delay_us);
  Py_RETURN_NONE;
}


static PyObject *mod_start_listener(PyObject *self, PyObject *args) {
  PyObject *callback = NULL;
  PyObject *previous = NULL;
  bool ok = false;
  (void)self;

  if (!PyArg_ParseTuple(args, "O", &callback)) {
    return NULL;
  }

  if (!PyCallable_Check(callback)) {
    PyErr_SetString(PyExc_TypeError, "listener must be callable");
    return NULL;
  }

  Py_INCREF(callback);
  previous = listener_callback;
  listener_callback = callback;

  if (axidev_io_listener_is_listening()) {
    Py_XDECREF(previous);
    Py_RETURN_TRUE;
  }

  ok = axidev_io_listener_start(listener_bridge, NULL);
  if (!ok) {
    listener_callback = previous;
    Py_DECREF(callback);
    return bool_result(false);
  }

  Py_XDECREF(previous);
  Py_RETURN_TRUE;
}


static PyObject *mod_stop_listener(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  axidev_io_listener_stop();
  clear_listener_callback();
  Py_RETURN_NONE;
}


static PyObject *mod_is_listening(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  return bool_result(axidev_io_listener_is_listening());
}


static PyObject *mod_key_to_string(PyObject *self, PyObject *args) {
  int key = 0;
  char *text = NULL;
  PyObject *result = NULL;
  (void)self;

  if (!PyArg_ParseTuple(args, "i", &key)) {
    return NULL;
  }

  text = axidev_io_keyboard_key_to_string((axidev_io_keyboard_key_t)key);
  if (text == NULL) {
    Py_RETURN_NONE;
  }

  result = PyUnicode_FromString(text);
  axidev_io_free_string(text);
  return result;
}


static PyObject *mod_string_to_key(PyObject *self, PyObject *args) {
  PyObject *text_obj = NULL;
  const char *text = NULL;
  (void)self;

  if (!PyArg_ParseTuple(args, "U", &text_obj)) {
    return NULL;
  }

  text = PyUnicode_AsUTF8(text_obj);
  if (text == NULL) {
    return NULL;
  }

  return PyLong_FromLong((long)axidev_io_keyboard_string_to_key(text));
}


static PyObject *mod_key_to_string_with_modifier(PyObject *self, PyObject *args) {
  int key = 0;
  int mods = 0;
  char *text = NULL;
  PyObject *result = NULL;
  (void)self;

  if (!PyArg_ParseTuple(args, "ii", &key, &mods)) {
    return NULL;
  }

  text = axidev_io_keyboard_key_to_string_with_modifier(
      (axidev_io_keyboard_key_with_modifier_t){.key = (axidev_io_keyboard_key_t)key,
                                               .mods = (axidev_io_keyboard_modifier_t)mods});
  if (text == NULL) {
    Py_RETURN_NONE;
  }

  result = PyUnicode_FromString(text);
  axidev_io_free_string(text);
  return result;
}


static PyObject *mod_string_to_key_with_modifier(PyObject *self, PyObject *args) {
  PyObject *text_obj = NULL;
  const char *text = NULL;
  axidev_io_keyboard_key_with_modifier_t key_mod = {
      .key = AXIDEV_IO_KEY_UNKNOWN,
      .mods = AXIDEV_IO_MOD_NONE,
  };
  (void)self;

  if (!PyArg_ParseTuple(args, "U", &text_obj)) {
    return NULL;
  }

  text = PyUnicode_AsUTF8(text_obj);
  if (text == NULL) {
    return NULL;
  }

  if (!axidev_io_keyboard_string_to_key_with_modifier(text, &key_mod)) {
    Py_RETURN_NONE;
  }

  return build_key_mod_dict(key_mod);
}


static PyObject *mod_version(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  return PyUnicode_FromString(axidev_io_library_version());
}


static PyObject *mod_get_last_error(PyObject *self, PyObject *Py_UNUSED(args)) {
  char *text = NULL;
  PyObject *result = NULL;
  (void)self;

  text = axidev_io_get_last_error();
  if (text == NULL) {
    Py_RETURN_NONE;
  }

  result = PyUnicode_FromString(text);
  axidev_io_free_string(text);
  return result;
}


static PyObject *mod_clear_last_error(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  axidev_io_clear_last_error();
  Py_RETURN_NONE;
}


static PyObject *mod_log_set_level(PyObject *self, PyObject *args) {
  unsigned int level = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "I", &level)) {
    return NULL;
  }

  axidev_io_log_set_level((axidev_io_log_level_t)level);
  Py_RETURN_NONE;
}


static PyObject *mod_log_get_level(PyObject *self, PyObject *Py_UNUSED(args)) {
  (void)self;
  return PyLong_FromUnsignedLong(axidev_io_log_get_level());
}


static PyObject *mod_log_is_enabled(PyObject *self, PyObject *args) {
  unsigned int level = 0;
  (void)self;

  if (!PyArg_ParseTuple(args, "I", &level)) {
    return NULL;
  }

  return bool_result(axidev_io_log_is_enabled((axidev_io_log_level_t)level));
}


static PyObject *mod_log_message(PyObject *self, PyObject *args) {
  unsigned int level = 0;
  PyObject *message_obj = NULL;
  const char *message = NULL;
  (void)self;

  if (!PyArg_ParseTuple(args, "IU", &level, &message_obj)) {
    return NULL;
  }

  message = PyUnicode_AsUTF8(message_obj);
  if (message == NULL) {
    return NULL;
  }

  axidev_io_log_message((axidev_io_log_level_t)level, "axidev_io", 0, "%s",
                        message);
  Py_RETURN_NONE;
}


static void module_free(void *module) {
  (void)module;
  axidev_io_listener_stop();
  clear_listener_callback();
  axidev_io_keyboard_free();
}


static PyMethodDef module_methods[] = {
    {"initialize", mod_initialize, METH_NOARGS, NULL},
    {"free", mod_free, METH_NOARGS, NULL},
    {"is_ready", mod_is_ready, METH_NOARGS, NULL},
    {"get_backend", mod_get_backend, METH_NOARGS, NULL},
    {"get_capabilities", mod_get_capabilities, METH_NOARGS, NULL},
    {"request_permissions", mod_request_permissions, METH_NOARGS, NULL},
    {"key_down", mod_key_down, METH_VARARGS, NULL},
    {"key_up", mod_key_up, METH_VARARGS, NULL},
    {"key_repeat", mod_key_repeat, METH_VARARGS, NULL},
    {"tap", mod_tap, METH_VARARGS, NULL},
    {"active_modifiers", mod_active_modifiers, METH_NOARGS, NULL},
    {"hold_modifiers", mod_hold_modifiers, METH_VARARGS, NULL},
    {"release_modifiers", mod_release_modifiers, METH_VARARGS, NULL},
    {"release_all_modifiers", mod_release_all_modifiers, METH_NOARGS, NULL},
    {"type_text", mod_type_text, METH_VARARGS, NULL},
    {"type_character", mod_type_character, METH_VARARGS, NULL},
    {"flush", mod_flush, METH_NOARGS, NULL},
    {"set_key_delay", mod_set_key_delay, METH_VARARGS, NULL},
    {"start_listener", mod_start_listener, METH_VARARGS, NULL},
    {"stop_listener", mod_stop_listener, METH_NOARGS, NULL},
    {"is_listening", mod_is_listening, METH_NOARGS, NULL},
    {"key_to_string", mod_key_to_string, METH_VARARGS, NULL},
    {"string_to_key", mod_string_to_key, METH_VARARGS, NULL},
    {"key_to_string_with_modifier", mod_key_to_string_with_modifier, METH_VARARGS,
     NULL},
    {"string_to_key_with_modifier", mod_string_to_key_with_modifier, METH_VARARGS,
     NULL},
    {"version", mod_version, METH_NOARGS, NULL},
    {"get_last_error", mod_get_last_error, METH_NOARGS, NULL},
    {"clear_last_error", mod_clear_last_error, METH_NOARGS, NULL},
    {"log_set_level", mod_log_set_level, METH_VARARGS, NULL},
    {"log_get_level", mod_log_get_level, METH_NOARGS, NULL},
    {"log_is_enabled", mod_log_is_enabled, METH_VARARGS, NULL},
    {"log_message", mod_log_message, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL},
};


static struct PyModuleDef module_definition = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_native",
    .m_doc = NULL,
    .m_size = -1,
    .m_methods = module_methods,
    .m_free = module_free,
};


PyMODINIT_FUNC PyInit__native(void) {
  return PyModule_Create(&module_definition);
}
