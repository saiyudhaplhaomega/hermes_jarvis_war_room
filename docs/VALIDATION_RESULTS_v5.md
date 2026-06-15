============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room
plugins: anyio-4.12.0, langsmith-0.6.4
collecting ... collected 0 items / 1 error

=================================== ERRORS ====================================
________________ ERROR collecting tests/test_observability.py _________________
ImportError while importing test module 'C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room\tests\test_observability.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\tests\test_observability.py:2: in <module>
    from backend.core.observability import ShadowAIDetector, ComplianceMonitor
E   ModuleNotFoundError: No module named 'backend'
=========================== short test summary info ===========================
ERROR ..\tests\test_observability.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 0.25s ===============================
