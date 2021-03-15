# CHANGELOG

<!--
IMPORTANT: the build script extracts the most recent version from this file
so make sure you follow the template
-->

<!-- Use the poetry changelog a template for each release:
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

## 1.0.0 2021-03-15

### Fixed

* Fix `method_cache` to not set `name` on parent class which would break classes that had an attribute `name`
* `GenericUserProfile` now forces email to lower case on save to avoid issues with duplicate emails in different case

### Added

* SerializerOptInFieldsMixin to control inclusion of expensive serializer fields.
* Camel case JSON DRF renderers and parsers.

## 1.0.0-rc2 2020-09-14

### Breaking Changes

* See [Legacy Changelog](CHANGELOG-legacy.md)

### Added

* First stable 1.0 release
