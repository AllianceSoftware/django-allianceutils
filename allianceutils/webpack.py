import hashlib

from django.conf import settings
from unipath import Path
from webpack_loader.loader import WebpackLoader


class TimestampWebpackLoader(WebpackLoader):
    """
    Extension of WebpackLoader that appends a ?ts=(timestamp) query string based on last modified time of chunk to serve
    Allows static asset web server to send far future expiry headers without worrying about cache invalidation

    Set WEBPACK_LOADER['DEFAULT']['LOADER_CLASS'] in django settings to use this
    """
    def get_chunk_url(self, chunk):
        url = super(TimestampWebpackLoader, self).get_chunk_url(chunk)

        if 'mtime' not in chunk:
            # we save the modification time in the chunk info
            relpath = Path(self.config['BUNDLE_DIR_NAME'], chunk['name'])
            # we don't use chunk['path'], because if the production stats file is built on
            # a different machine then it is likely invalid
            staticpath = Path(settings.STATIC_ROOT, relpath)
            try:
                chunk['mtime'] = staticpath.mtime()
            except (IOError, OSError):
                # If using a dev build (ie webpack dev server) then the static file will not exist
                chunk['mtime'] = None

        if chunk['mtime']:
            url += '{}ts={}'.format('&' if '?' in url else '?', chunk['mtime'])

        return url


class ContentHashWebpackLoader(WebpackLoader):
    """
    Extension of WebpackLoader that appends a ?ts=(timestamp) query string based on last modified time of chunk to serve
    Allows static asset web server to send far future expiry headers without worrying about cache invalidation

    Set WEBPACK_LOADER['DEFAULT']['LOADER_CLASS'] in django settings to use this
    """
    def get_chunk_url(self, chunk):
        url = super(ContentHashWebpackLoader, self).get_chunk_url(chunk)

        if 'hash' not in chunk:
            # we save the hash in the chunk info
            relpath = Path(self.config['BUNDLE_DIR_NAME'], chunk['name'])
            # we don't use chunk['path'], because if the production stats file is built on
            # a different machine then it is likely invalid
            staticpath = Path(settings.STATIC_ROOT, relpath)
            try:
                hash = hashlib.md5()
                with open(staticpath, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        hash.update(chunk)
                chunk['hash'] = hash.hexdigest()[:12]
            except (IOError, OSError):
                # If using a dev build (ie webpack dev server) then the static file will not exist
                chunk['hash'] = None

        if chunk['hash']:
            url += '{}hash={}'.format('&' if '?' in url else '?', chunk['hash'])

        return url
