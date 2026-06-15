============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\saiyu
plugins: anyio-4.12.0, langsmith-0.6.4
collecting ... collected 0 items / 2 errors

=================================== ERRORS ====================================
_ ERROR collecting Desktop/projects/KI_projects/hermes_jarvis_war_room/tests/test_orchestrator.py _
ImportError while importing test module 'C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room\tests\test_orchestrator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Desktop\projects\KI_projects\hermes_jarvis_war_room\tests\test_orchestrator.py:2: in <module>
    from backend.core.orchestrator import OrchestrationEngine
E   ModuleNotFoundError: No module named 'backend'
_ ERROR collecting Desktop/projects/KI_projects/hermes_jarvis_war_room/tests/test_budgets.py _
ImportError while importing test module 'C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room\tests\test_budgets.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Desktop\projects\KI_projects\hermes_jarvis_war_room\tests\test_budgets.py:2: in <module>
    from backend.core.budgets import CostOptimizer
E   ModuleNotFoundError: No module named 'backend'
=========================== short test summary info ===========================
ERROR Desktop/projects/KI_projects/hermes_jarvis_war_room/tests/test_orchestrator.py
ERROR Desktop/projects/KI_projects/hermes_jarvis_war_room/tests/test_budgets.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!
============================== 2 errors in 0.43s ==============================
