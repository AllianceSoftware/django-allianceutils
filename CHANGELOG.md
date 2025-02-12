# CHANGELOG

<!--
IMPORTANT: the build script extracts the most recent version from this file
so make sure you follow the template
-->

<!-- Use the poetry changelog as a template for each release:
## 1.2.3 2020-01-01

### Breaking Changes

* An Item

### Added

* An Item

### Changed

* An Item

### Fixed

* An Item

-->

## 4.1.1 2025-02-13

### Fixed

* Remove dependency on deprecated distutils package

### Added

* Copied `strtobool` from distutils

## 4.1.0 2024-08-06

### Fixed

* Resolve bug in `CurrentUserMiddleware` where if an exception was raised, middleware triggers an additional exception
* Fix types for all django checks to accept `None` for the `app_configs` argument

### Added

* Added `check_duplicated_middleware` system check to ensure no middleware gets included twice in config

## 4.0.1 2024-05-13

### Fixed

* `is_static_expression` now handles expressions with filters correctly

## 4.0.0 2024-03-18

### Breaking Changes
* Dropped support for django 3.2

### Added

* Add support for django 5.0
* Add `CurrentRequestMiddleware`
* Add `tox-poetry-installer` middleware to allow better management of tox dependencies in poetry

* Migrate `common_lib.templatetags.common` from template project to `template.py` with the following functions:
    * `resolve`
    * `token_kwargs`
    * `parse_tag_arguments`
    * `build_html_attrs`
    * `is_static_expression`

* Migrate `common_lib.tests.util` from template project to `tests/util.py` with the following decorators:
    * `suppress_silk`
    * `logging_filter`
    * `warning_filter`

* Migrate `permission` from template project with:
    * `class NoDefaultPermissionsMeta`
    * `class PermissionNotImplementedError`
    * `class AmbiguousGlobalPermissionWarning`
    * `def identify_global_perms`
    * `def reverse_if_probably_allowed`

### Fixed

* CI now properly tests for all Django versions, whereas previously Poetry would install the latest Django version and overwrite the tox-managed dependencies

## 3.0.0 2023-06-08

### Breaking changes
* Dropped support for django 2.2
* Dropped support for python 3.7, 3.6
* Dropped support for django-db-constraints validation (`check_db_constraints()` constraint length & collisions); should use django native constraints instead
* `ProfileModelBackend` has been removed. You should use `ProfileModelBackendMixin` instead, and implement a case
  insensitive username field on your User model.
* `GenericUserProfile` now no longer normalizes `email` (or even assumes an `email` field is present)
  * You should implement email/username normalization in your User model
* `MultipleFieldCharFilter` removed; the `method` argument on a `filter.Field` is simple enough to make this now unnecessary.
  * see [documentation](https://django-filter.readthedocs.io/en/stable/ref/filters.html#method)
* Added type information

### Added

* Add support for django 4.2
* Add support for python 3.10, 3.11
* New `QueryCountMiddleware` methods `set_threshold` and `increase_threshold`
  * `request.QUERY_COUNT_WARNING_THRESHOLD` is still supported but will be removed in future versions

### Fixed

* Resolve bug in `CamelCaseMultiPartJSONParser.parse` where if the `HTTP_X_MULTIPART_JSON` header is not set it tries to parse the stream a second time, which returns no data

## 2.2.0 2022-03-28

### Fixed

* `CheckExplicitTableNames` will now skip unmanaged models to allow for cases where there is no table

## 2.1.0 2021-12-17

### Fixed
* Support new URL pattern adopted by django to resolve [CVE-2021-44420] (https://www.djangoproject.com/weblog/2021/dec/07/security-releases/)
* Add check class for configurable git path, update to handle hooksPath config for newer husky

## 2.0.0 2021-07-22

### Added

* Add support for django 3.2
* `auth/backends` now works without `authtools`
    * `ProfileModelBackend` will not be available if `authtools` is not able to be imported (`authtools` does not currently work with django 3.2)
* ````
* Add `add_autoreload_extra_files()`
* Add ability for checks to ignore apps/models using a regex instead of just a static string


### Fixed
* `GenericUserProfile.normalize_email` can now be overridden on child classes and will work as expected

### Breaking Changes
* Drop support for django 1.11
* Drop support for isort 4

## 1.2.0 2021-06-11

### Added

* `INCLUDE_QUERY_HASH` and `BASE_URL` options added to `WEBPACK_LOADER` config. This allows the content hash query string to
  be disabled and to load assets that are on a different domain (eg. a CDN).

## 1.1.0 2021-03-25

### Fixed

* `camelize` now handles django lazy strings (eg. `gettext_lazy`) as strings rather than as iterables

### Added

* `get_model` added to GenericDjangoViewsetPermissions allowing model to be substituted

## 1.0.0 2021-03-15

### Fixed

* Fix `method_cache` to not set `name` on parent class which would break classes that had an attribute `name`
* `GenericUserProfile` now forces email to lower case on save to avoid issues with duplicate emails in different case

### Added

* SerializerOptInFieldsMixin to control inclusion of expensive serializer fields.
* Camel case JSON DRF renderers and parsers.

## 1.0.0rc2 2020-09-14

### Breaking Changes

* See [Legacy Changelog](CHANGELOG-legacy.md)

### Added

* First stable 1.0 release
