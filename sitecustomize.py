# Windows USB support for brother_ql's pyusb backend.
#
# On Windows there is no system libusb-1.0 on the default search path, so
# pyusb's usb.core.find() finds no backend. The `libusb-package` wheel bundles
# a libusb-1.0 DLL; here we transparently inject it as the default backend for
# every usb.core.find() call (which is how brother_ql opens the printer).
#
# Python imports `sitecustomize` automatically at interpreter startup when it is
# found on sys.path (the app directory and site-packages), so no app code needs
# to change.
try:
    import libusb_package
    import usb.core

    _backend = libusb_package.get_libusb1_backend()
    _original_find = usb.core.find

    def find(*args, **kwargs):
        kwargs.setdefault("backend", _backend)
        return _original_find(*args, **kwargs)

    usb.core.find = find
except Exception:
    # If anything is missing (e.g. non-Windows host), fall back to defaults.
    pass
