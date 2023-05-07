# E-Uni Alliance Auth Member Tools

EVE University's Member Administration Tools

## Features

Accepts and processes applications

## Production Installation

**Always remember to back up your database before performing any migrations!**

1. Setup your Alliance Auth environment to access the EVE Uni PyPy repository

2. Inside your alliance auth environment run 'pip install aa-membertools'

3. Add this app to your installed apps in `/myauth/settings/local.py`:

    ```python
    INSTALLED_APPS += ["membertools"]
    ```

4. Run the following commands from your Auth directory [myauth]

    ```shell
    python manage.py migrate

    python manage.py collectstatic --no-input
    ```

5. If you need to import hrappsnext data also run
    ```shell
    python manage.py membertools_import_hrappsnext --confirm
    python manage.py membertools_create_members
    ```

## Upgrading from Alliance Auth 2.x

After installing the app and adding it to your local.py run

  ```shell
  python manage.py migrate
  python manage.py structures_preload_eveuniverse
  python manage.py migrate
  python manage.py collectstatic --no-input
  python manage.py membertools_import_hrappsnext --confirm
  python manage.py membertools_create_members
```
**Note:** that you may need to upgrade to a patched version of hrappsnext to perform the above commands.
