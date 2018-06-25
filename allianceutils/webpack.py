import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from django.conf import settings
from webpack_loader.loader import WebpackLoader


class _CacheBustWebpackLoader(WebpackLoader):
    def get_query_cache_param(self, path: Path) -> (str, str):
        """
        Get the cache-busting query URL params
        returns a tuple of (query param name, query param value)
        """
        raise NotImplementedError()

    def get_chunk_url(self, chunk):
        url = super().get_chunk_url(chunk)

        if '_cache_bust_value' not in chunk:
            url_parts = urlsplit(url)
            if url_parts.scheme or url_parts.netloc:
                # this is a URL, not a file path: don't do anything
                chunk['_cache_bust_value'] = None
            else:
                # we don't use the absolute path (chunk['path']) because if the production stats file is
                # built on a different machine then it is probably invalid; instead we assume it's in
                # STATIC_ROOT/BUNDLE_DIR_NAME/chunkname
                relpath = Path(self.config['BUNDLE_DIR_NAME'], chunk['name'])

                assert settings.STATIC_ROOT is not None

                staticpath = Path(settings.STATIC_ROOT, relpath)

                # TODO: Should we catch FileNotFoundError and ignore instead?
                chunk['_cache_bust_value'] = self.get_query_cache_param(staticpath)

        if chunk['_cache_bust_value']:
            url_parts = urlsplit(url)
            query = '{}{}{}={}'.format(
                url_parts.query,
                '' if url_parts.query == '' else '&',
                chunk['_cache_bust_value'][0],
                chunk['_cache_bust_value'][1]
            )
            url = urlunsplit(url_parts._replace(query=query))

        return url


class TimestampWebpackLoader(_CacheBustWebpackLoader):
    """
    Extension of WebpackLoader that appends a ?ts=(timestamp) query string based on last modified time of chunk to serve
    Allows static asset web server to send far future expiry headers without worrying about cache invalidation

    Set WEBPACK_LOADER['DEFAULT']['LOADER_CLASS'] in django settings to use this
    """

    def get_query_cache_param(self, path):
        return 'ts', path.mtime()


class ContentHashWebpackLoader(_CacheBustWebpackLoader):
    """
    Extension of WebpackLoader that appends a ?hash=(hash) query string based on hash of chunk to serve
    Allows static asset web server to send far future expiry headers without worrying about cache invalidation

    Set WEBPACK_LOADER['DEFAULT']['LOADER_CLASS'] in django settings to use this
    """
    def get_query_cache_param(self, path):
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return 'hash', hasher.hexdigest()[:12]
