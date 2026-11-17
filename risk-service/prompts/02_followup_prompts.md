
$ python -m unittest discover -s tests -v
test_service (unittest.loader._FailedTest.test_service) ... ERROR

======================================================================
ERROR: test_service (unittest.loader._FailedTest.test_service)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_service
Traceback (most recent call last):
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 433, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 374, in _get_module_from_name
    __import__(name)
    ~~~~~~~~~~^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\tests\test_service.py", line 12, in <module>
    from app.main import create_app  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\app\main.py", line 9, in <module>
    from flask import Flask, Response, g, jsonify, request
ModuleNotFoundError: No module named 'flask'


----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (errors=1)

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ ^C

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ py -m pip install ruff
Requirement already satisfied: ruff in C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages (0.17.5)

[notice] A new release of pip is available: 26.2.1 -> 26.3
[notice] To update, run: C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pip install --upgrade pip

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ py -m unittest discover -s tests -v
test_service (unittest.loader._FailedTest.test_service) ... ERROR

======================================================================
ERROR: test_service (unittest.loader._FailedTest.test_service)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_service
Traceback (most recent call last):
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 433, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 374, in _get_module_from_name
    __import__(name)
    ~~~~~~~~~~^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\tests\test_service.py", line 12, in <module>
    from app.main import create_app  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\app\main.py", line 9, in <module>
    from flask import Flask, Response, g, jsonify, request
ModuleNotFoundError: No module named 'flask'


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ py -m unittest discover -s tests -v
test_service (unittest.loader._FailedTest.test_service) ... ERROR

======================================================================
ERROR: test_service (unittest.loader._FailedTest.test_service)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_service
Traceback (most recent call last):
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 433, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 374, in _get_module_from_name
    __import__(name)
    ~~~~~~~~~~^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\tests\test_service.py", line 12, in <module>
    from app.main import create_app  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\app\main.py", line 9, in <module>
    from flask import Flask, Response, g, jsonify, request
ModuleNotFoundError: No module named 'flask'


----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (errors=1)

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ py -m unittest discover -s tests -v
test_service (unittest.loader._FailedTest.test_service) ... ERROR

======================================================================
ERROR: test_service (unittest.loader._FailedTest.test_service)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_service
Traceback (most recent call last):
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 433, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 374, in _get_module_from_name
    __import__(name)
    ~~~~~~~~~~^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\tests\test_service.py", line 12, in <module>
    from app.main import create_app  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\app\main.py", line 9, in <module>
    from flask import Flask, Response, g, jsonify, request
ModuleNotFoundError: No module named 'flask'


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ py -m unittest discover -s tests -v
test_service (unittest.loader._FailedTest.test_service) ... ERROR

======================================================================
ERROR: test_service (unittest.loader._FailedTest.test_service)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_service
Traceback (most recent call last):
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 433, in _find_test_path
    module = self._get_module_from_name(name)
  File "C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\unittest\loader.py", line 374, in _get_module_from_name
    __import__(name)
    ~~~~~~~~~~^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\tests\test_service.py", line 12, in <module>
    from app.main import create_app  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\kumarsid\OneDrive - Zinnia\Desktop\ML\risk-service\app\main.py", line 9, in <module>
    from flask import Flask, Response, g, jsonify, request
ModuleNotFoundError: No module named 'flask'


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ py -m ruff check --fix
All checks passed!

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ py -m pip install ruff
Requirement already satisfied: ruff in C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages (0.17.5)

[notice] A new release of pip is available: 26.2.1 -> 26.3
[notice] To update, run: C:\Users\kumarsid\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pip install --upgrade pip

kumarsid@BVCYZY4 UCRT64 ~/OneDrive - Zinnia/Desktop/ML/risk-service (feature/inference-api)
$ py -m ruff check .
All checks passed!
