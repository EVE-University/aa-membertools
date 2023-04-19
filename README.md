# E-Uni Alliance Auth Member Tools

EVE University's Member Administration Tools

## Features

Requires membertools.basic_access to see applicant areas.

## Installation

1. Clone this repo somewhere

2. Inside your alliance auth environment run 'pip install [path to repo clone]'

3. Add this app to your installed apps in `/myauth/settings/local.py`:

    ```python
    INSTALLED_APPS += ["membertools"]
    ```

4. Useful commands after installing.

    ```shell
    python manage.py migrate membertools

    python manage.py collectstatic
    ```
