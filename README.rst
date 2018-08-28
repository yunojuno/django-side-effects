.. image:: https://travis-ci.org/yunojuno/django-side-effects.svg?branch=master
    :target: https://travis-ci.org/yunojuno/django-side-effects

.. image:: https://badge.fury.io/py/django-side-effects.svg
    :target: https://badge.fury.io/py/django-side-effects

Django Side Effects
===================

Django app for managing external side effects.

Python2/3
---------

**This project is now Python3, Django 1.11+ only on master.**

The legacy Python2 code is now parked in the python2 branch.

Background
----------

This project was created to try and bring some order to the use of external
side-effects within the YunoJuno platform. External side-effects are (as
defined by us) those actions that affect external systems, and that are not
part of the core application integrity. They fall into two main categories
within our application - *notifications* and *updates*, and are best
illustrated by example:

**Notifications**

* HipChat messages
* SMS (via Twilio)
* Push notifications (via Google Cloud Messaging)
* Email

**Updates**

* Base CRM (sales)
* Mailchimp CRM (marketing)
* Elasticsearch (full-text index)

There are some shared aspects of all of these side-effects:

1. They can all be processed asynchronously (queued)
2. They can all be replayed (and are idempotent)
3. They can be executed in any order
4. They are not time critical
5. They do not affect the state of the Django application

As we have continued to build out YunoJuno our use of these side-effects
has become ever more complex, and has in some areas left us with functions
that are 80% side-effects:

.. code:: python

    def foo():
        # do the thing the function is supposed to do
        update_object(obj)
        # spend the rest of the function working out which side-effects to fire
        if settings.notify_account_handler:
            send_notification(obj.account_handler)
        if obj.has_changed_foo():
            udpate_crm(obj)


This results in a codebase is:

* Hard to read
* Hard to test
* Hard to document^

^ Barely a week goes by without someone asking *"what happens when X does Y -
I thought they got email Z?"*

Solution
--------

This project aims to address all three of the issues above by:

* Removing all side-effects code from core functions
* Simplifying mocking / disabling of side-effects in tests
* Simplifying testing of side-effects only
* Automating documentation of side-effects

It does this with a combination of function decorators that can
be used to build up a global registry of side-effects.

The first decorator, ``has_side_effects``, is used to mark a function as one
that has side effects:

.. code:: python

    # mark this function as one that has side-effects. The label
    # can be anything, and is used as a dict key for looking up
    # associated side-effects functions
    @side_effects.decorators.has_side_effects('update_profile')
    def foo(*args, **kwargs):
        pass

**Decorating view functions**

By default, the ``has_side_effects`` decorator will run so long as the inner
function does not raise an exception. View functions, however, are a paticular
case where the function may run, and return a perfectly valid ``HttpResponse``
object, but you do **not** want the side effects to run, as the response object
has a ``status_code`` of 404, 500, etc. In this case, you want to inspect the
inner function return value before deciding whether to fire the side effects
functions. In order to support this, the ``has_side_effects`` decorator has
a kwarg ``run_on_exit`` which takes a function that takes a single parameter,
the return value from the inner function, and must return ``True`` or ``False``
which determines whether to run the side effects.

The ``decorators`` module contains the default argument for this kwarg, a
function called ``http_response_check``. This will return ``False`` if the
inner function return value is an ``HttpResponse`` object with a status
code in the 4xx-5xx range.


The second decorator, ``is_side_effect_of``, is used to bind those functions
that implement the side effects to the origin function:

.. code:: python

    # bind this function to the event 'update_profile'
    @is_side_effect_of('update_profile')
    def send_updates(*args, **kwargs):
        """Update CRM system."""
        pass

    # bind this function also to 'update_profile'
    @is_side_effect_of('update_profile')
    def send_notifications(*args, **kwargs):
        """Notify account managers."""
        pass

In the above example, the updates and notifications have been separated
out from the origin function, which is now easier to understand as it is
only responsible for its own functionality. In this example we have two
side-effects bound to the same origin, however this is an implementation
detail - you could have a single function implementing all the side-effects,
or split them out further into the individual external systems.

Internally, the app maintains a registry of side-effects functions bound to
origin functions using the text labels. The docstrings for all the bound functions can be grouped using these labels, and then be printed out using the
management command ``display_side_effects``:

.. code:: bash

    $ ./manage.py display_side_effects

    This command prints out the first line from the docstrings of all functions
    registered using the @is_side_effect decorator, grouped by label.

    update_profile:

        - Update CRM system.
        - Notify account managers.

    close_account:

        - Send confirmation email to user.
        - Notify customer service.

If you have a lot of side-effects wired up, you can filter the list by the label:

.. code:: bash

    $ ./manage.py display_side_effects --label update_profile

    update_profile:
        - Update CRM system.
        - Notify account managers.

Or by a partial match on the event label:

.. code:: bash

    $ ./manage.py display_side_effects --label-contains profile

    update_profile:
        - Update CRM system.
        - Notify account managers.

If you want to enforce docstrings on side-effect functions, then you can use the
`--check-docstrings` option, which will exit with a non-zero exit code if any
docstrings are missing. This can be used as part of a CI process, failing any
build that does not have all its functions documented. (The exit code is the count
of functions without docstrings).

.. code:: bash

    $ ./manage.py display_side_effects --check-docstrings

    update_profile:
        *** DOCSTRING MISSING: update_crm ***
        - Notify account managers.

    ERROR: InvocationError for command '...' (exited with code 1)

Why not use signals?
--------------------

The above solution probably looks extremely familiar - and it is very closely
related to the built-in Django signals implementation. You could easily
reproduce the output of this project using signals - this project is really
just a formalisation of the way in which a signal-like pattern could be used
to make your code clear and easy to document. The key differences are:

1. Explicit statement that a function has side-effects
2. A simpler binding mechanism (using text labels)
3. (TODO) Async processing of receiver functions

It may well be that this project merges back in to the signals pattern in
due course - at the moment we still experimenting.


Installation
------------

The project is available through PyPI as ``django-side-effects``:

.. code::

    $ pip install django-side-effects

And the main package itself is just ``side_effects``:

.. code:: python

    >>> from side_effects import decorators

Tests
-----

The project has pretty good test coverage (>90%) and the tests themselves run through ``tox``.

.. code::

    $ pip install tox
    $ tox

If you want to run the tests manually, make sure you install the requirements, and Django.

.. code::

    $ pip install django==2.0  # your version goes here
    $ tox

If you are hacking on the project, please keep coverage up.

NB If you implement side-effects in your project, you will most likely want to be able to turn off the side-effects when testing your own code (so that you are not actually sending emails, updating systems), but you also probably want to know that the side-effects events that you are expecting are fired.

The following code snippet shows how to use the `disable_side_effects` context manager, which returns a list of all the side-effects events that are fired. There is a matching function decorator, which will append the events list as an arg to the decorated function, in the same manner that `unittest.mock.patch` does.

.. code:: python

    @has_side_effects('do_foo')
    def foo():
        pass

    def test_foo():

        # to disable side-effects temporarily, use decorator
        with disable_side_effects() as events:
            foo()
            assert events = ['do_foo']
            foo()
            assert events = ['do_foo', 'do_foo']


    # events list is added to the test function as an arg
    @disable_side_effects()
    def test_foo_without_side_effects(events):
        foo()
        assert events = ['do_foo']

In addition to these testing tools there is a universal 'kill-switch' which can be set using the env var `SIDE_EFFECTS_TEST_MODE=True`. This will completely disable all side-effects events. It is a useful tool when you are migrating a project over to the side_effects pattern - as it can highlight where existing tests are relying on side-effects from firing. Use with caution.

Contributing
------------

Standard GH rules apply: clone the repo to your own account, create a branch, make sure you update the tests, and submit a pull request.

Status
------

We are using it at YunoJuno, but 'caveat emptor'. It does what we need it to do right now, and we will extend it as we evolve. If you need or want additional features, get involved :-).
