# E-Uni Alliance Auth Application HR Applications Next

HR Applications Next Application

## Features

Temporarily requires auth.human_resources permission to access recruitment side.

No permissions required to access and submit applications

## Installation

1. Clone this repo somewhere

2. Inside your alliance auth environment run 'pip install [path to repo clone]'

3. Add this app to your installed apps in `/myauth/settings/local.py`:

    ```python
    INSTALLED_APPS += [
        'membertools'
    ]
    ```

4. Useful commands after installing an app, but not required for the base membertools.

    ```shell
    python manage.py makemigrations membertools
    python manage.py migrate

    python manage.py collectstatic
    ```
