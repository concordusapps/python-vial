# vial
[![Build Status](https://travis-ci.org/concordusapps/python-vial.png?branch=master)](https://travis-ci.org/concordusapps/python-vial)
[![Coverage Status](https://coveralls.io/repos/concordusapps/python-vial/badge.png?branch=master)](https://coveralls.io/r/concordusapps/python-vial?branch=master)
[![PyPi Version](https://pypip.in/v/vial/badge.png)](https://pypi.python.org/pypi/vial)
![PyPi Downloads](https://pypip.in/d/vial/badge.png)
> A session store backed by redis.

## Installation

### Automated

1. **Vial** can be installed using `pip` or `easy_install`.

   ```sh
   pip install vial
   ```

### Manual

1. Clone the **vial** repository to your local computer.

   ```sh
   git clone git://github.com/vial/python-vial.git
   ```

2. Change into the **vial** root directory.

   ```sh
   cd /path/to/python-vial
   ```

3. Install the project and all its dependencies using `pip`.

   ```sh
   pip install .
   ```

   Additional *extra* requirements may be specified in brackets following
   the `.`.

   ```sh
   # Install vial as well as the additional dependencies to use
   # the unit test suite.
   pip install ".[test]"
   ```

## Usage

The session object is a standard mutable mapping with a few additional methods to facilitate a session.

#### Establish a new session

```python
>>> from vial import Vial

# By default the session connects to redis on `localhost:6379`.
>>> vial = Vial(host='localhost', port=9001)

>>> session = vial.Session()
>>> session.id
None

>>> session.save()
>>> session.id
'8379fh98302hf8hg8hrligh908h490nvn9gn389tb038n'

# Add some more values to the session.
>>> session['color'] = 'blue'
>>> session.save()

# Fetch the session and check the value.
>>> vial.Session(id=session.id)['color']
'blue'
```

#### Retrieve an existing session

This will create the session object bound to the passed identifier.

```python
>>> from vial import Vial
>>> vial = Vial()
>>> session = vial.Session(id='8379fh98302hf8hg8hrligh908h490nvn9gn389tb038n')

# This will identify if the session is persisted in redis
>>> session.is_new
False
```

## Contributing

### Setting up your environment
1. Follow steps 1 and 2 of the [manual installation instructions][].

[manual installation instructions]: #manual

2. Initialize a virtual environment to develop in. This is done so as to ensure every contributor is working with close-to-identicial versions of packages.

   ```sh
   mkvirtualenv vial
   ```

   The `mkvirtualenv` command is available from `virtualenvwrapper` which can be installed as follows:

   ```sh
   pip install virtualenvwrapper
   ```

3. Install **vial** in development mode with testing enabled. This will download all dependencies required for running the unit tests.

   ```sh
   pip install -e ".[test]"
   ```

### Running the test suite
1. [Set up your environment](#setting-up-your-environment).

2. Run the unit tests.

   ```sh
   py.test
   ```


## License

Unless otherwise noted, all files contained within this project are liensed under the MIT opensource license. See the included file LICENSE or visit [opensource.org][] for more information.

[opensource.org]: http://opensource.org/licenses/MIT
