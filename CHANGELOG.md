# CHANGELOG

* Note: `setup.py` reads the highest version number from this section, so use versioning compatible with setuptools
* 0.7
    * 0.7.dev
        * `CurrentUserMiddleware` now uses thread-local storage
    * 0.7.3
        * Fix `util.get_firstparty_apps` not working with isort >=5
        * Fix `setup.py` `packages` only including the root package 
    * 0.7.2
        * Breaking Changes
            * `add_group_permissions`, `get_users_with_permission` and `get_users_with_permissions` are now removed in preference of CsvPermission
            * ProfileModelBackend is now behaving differently, namely suppressing all calls to .user_permissions and .groups.
    * 0.7.1
        * `render_entry_point` now generates URLs to bundles using the `static` function. This makes it possible to use with `ManifestStaticFileStorage`.
        * `camelize` & `underscorize` will no longer transform `File` objects. This resolves an issue when used with djrad forms containing file fields.
        * fixed MediaStorage not working properly with newer version of boto3
    * 0.7.0
        * Breaking Changes
            * `asynctask` table names have changed 
        * `asynctask` is now separate from allianceutils app 
        * Various test fixes (esp test both mysql and postgres in CI)
        * Added documentation for `staff_member_required`
* 0.6
    * 0.6.1
        * Fix `isort` not being a hard requirement (needed for `get_firstparty_apps`)
        * Doc
            * Added documentation for `get_firstparty_apps`
    * 0.6.0
        * Breaking Changes
            * Removed autodumpdata and its related checks
            * Introduced two new models (AsyncItem and AsyncItemStatus). These two may cause your exisiting checks to fail. Consider migrate checks to use get_firstparty_apps.
        * Added GenericDjangoViewsetWithoutModelPermissions
        * underscore_to_camel, camel_to_underscore no longer break if passed dict with non-string keys (eg. int keys)
        * Added HttpAuthMiddleware to provide basic http auth functionality
        * Adds warning message when webpack's compiling / takes too long to compile
        * `checks.check_git_hooks` now also checks for husky
        * Fix DRF BrowserableAPI causes GenericViewsetPermissions to throw out an error for None action
        * Fix `GenericUserProfileQueryset` values() and values_list() incorrectly reject all args
        * CurrentUserMiddleware now supports the post-django-1.11 MIDDLEWARE
        * Replaces boto used by AllianceStorage with Boto3
        * now supports django 1.11 and 2.2
        * Added `checks.check_explicit_table_names`, ensure `db_table` specified in model Meta
        * Added util.get_firstparty_apps() to be used for excluding 3rd party modules in certain checks
* 0.5
    * 0.5.0
        * Breaking Changes    
            * drop support for python 3.4, 3.5
            * `alliance_bundle` removed
            * `TimestampWebpackLoader`, `ContentHashWebpackLoader` removed
        * django 2.1 support
        * remove `unipath` dependency
        * Added `checks.make_check_autodumpdata`, simplified mechanism to ignore missing autodumpdata warnings
        * Added `checks.check_git_hooks`, ensure .git/hooks directory sym-linked to git-hooks
        * Added `checks.check_admins`, ensure settings.ADMINS has been set for staging/production
        * Added `checks.check_db_constraints`, ensure db_constraints are unique when truncated
        * Add `render_entry_point` tag
        * Fix `QueryCountMiddleware` reporting incorrect query counts when run in multithreaded server 
* 0.4
    * 0.4.2
        * `GenericUserProfileManagerMixin` rewritten; interface has changed, now works correctly
    * 0.4.1
        * Breaking Changes
           * Specify behaviour of numbers in underscore/camel case conversion (was undefined before) 
        * Add `raise_validation_errors`
    * 0.4.0
        * Breaking Changes
           * The interface for `get_autodump_labels` has changed
        * Add `checks.check_autodumpdata` 
* 0.3
    * 0.3.4
        * Add `camel_case`
        * Add `print_logging` management command
        * Fix `GenericUserProfile` raising the wrong model exceptions; removed `GenericUserProfileManager.use_proxy_model` 
        * Mark `script_json` for future removal
    * 0.3.3
        * Add `default_value`
        * Add tests
            * For `alliance_bundle` 
            * For `ContentHashWebpackLoader` & `TimestampWebpackLoader`
    * 0.3.2
        * Fix `check_url_trailing_slash` failing with `admin.site.urls`
    * 0.3.1
        * Fix install failure with setuptools<20.3  
    * 0.3.0
        * Breaking Changes
            * Dropped support for python <3.4
            * Dropped support for django <1.11
        * Add `GenericUserProfile`
        * Add `python_to_django_date_format`
        * Add `check_url_trailing_slash`
        * Add `QueryCountMiddleware`
        * Test against python 3.4, 3.5, 3.6
* 0.2
    * 0.2.0
        * Breaking Changes
            * The interface for `get_autodump_labels` has changed 
        * Add autodumpdata SQL output format
        * Add `mysqlquickdump` options `--model` and `--explicit` 
        * Update to work with webpack_loader 0.5
* 0.1
    * 0.1.6
        * Update `json_orminheritancefix` to work with django 1.11 
    * 0.1.5
        * Fix missing import if using autodumpdata automatically calculated filenames
        * autodumpdata now creates missing fixture directory automatically
    * 0.1.4
        * Fix bad versioning in previous release
    * 0.1.3
        * Add autodumpdata test cases
        * Add autodumpdata `--stdout`, `--output` options
        * Fix autodumpdata failing if `settings.SERIALIZATION_MODULES` not defined
    * 0.1.2
        * Add test cases, documentation
    * 0.1.1
        * Add `StaticStorage`, `MediaStorage`
    * 0.1.0
        * Initial release
